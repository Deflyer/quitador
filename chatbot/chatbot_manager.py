"""
Gerenciador de estado e lógica do chatbot de pagamentos
"""
import json
import sys
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

# Adiciona os diretórios ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Sugestao-acao'))

from dda_crew_adapter import DDACrewAdapter
from nlp_intent import IntentClassifier
from conversational_agent import ConversationalAgent


class EstadoChat(Enum):
    """Estados possíveis da conversa"""
    INICIO = "inicio"
    MENU_PRINCIPAL = "menu_principal"
    VISAO_DIA = "visao_dia"
    AGUARDANDO_DATA = "aguardando_data"
    OPCOES_VISAO_DIA = "opcoes_visao_dia"
    CONFIRMACAO_PAGAMENTO = "confirmacao_pagamento"  # Novo estado para confirmar pagamento
    DETALHE_BOLETO = "detalhe_boleto"
    SUGESTAO_ACAO = "sugestao_acao"
    VISAO_INTERVALO = "visao_intervalo"
    AGUARDANDO_INTERVALO = "aguardando_intervalo"
    OPCOES_VISAO_INTERVALO = "opcoes_visao_intervalo"  # Novo estado para perguntas sobre intervalo
    BOLETOS_ATRASADOS = "boletos_atrasados"


class ChatbotManager:
    """Gerencia o fluxo de conversa e estado do chatbot"""
    
    def __init__(self, cnpj: str, saldo_atual: float = 10000.0, nome_usuario: str = "Célia"):
        self.cnpj = cnpj
        self.saldo_atual = saldo_atual
        self.saldo_inicial = saldo_atual
        self.nome_usuario = nome_usuario
        self.adapter = DDACrewAdapter(cnpj)
        self.estado = EstadoChat.INICIO
        self.contexto = {}
        self.historico = []
        self.boletos_pagos = []  # Lista de IDs de boletos já pagos nesta sessão
        self._estrategia_parcial_atual = None  # Estratégia de pagamento parcial atual
        self.intent_classifier = IntentClassifier()  # Classificador de intenções com IA
        self.conversational_agent = ConversationalAgent(cnpj, saldo_atual, nome_usuario)  # Agente conversacional com LLM
    
    def adicionar_ao_historico(self, tipo: str, conteudo: str):
        """Adiciona mensagem ao histórico"""
        self.historico.append({
            "tipo": tipo,  # "user" ou "bot"
            "conteudo": conteudo,
            "timestamp": datetime.now().isoformat()
        })
    
    def processar_mensagem(self, mensagem_usuario: str) -> str:
        """Processa a mensagem do usuário e retorna resposta"""
        self.adicionar_ao_historico("user", mensagem_usuario)
        
        resposta = self._processar_por_estado(mensagem_usuario)
        
        self.adicionar_ao_historico("bot", resposta)
        return resposta
    
    def _processar_por_estado(self, mensagem: str) -> str:
        """Processa mensagem usando IA para entender intenção"""
        
        if self.estado == EstadoChat.INICIO:
            return self._iniciar_conversa()
        
        # Usa IA para classificar a intenção do usuário
        contexto_map = {
            EstadoChat.MENU_PRINCIPAL: 'menu_principal',
            EstadoChat.OPCOES_VISAO_DIA: 'opcoes_visao_dia',
            EstadoChat.CONFIRMACAO_PAGAMENTO: 'confirmacao_pagamento',
            EstadoChat.AGUARDANDO_DATA: 'aguardando_data',
            EstadoChat.AGUARDANDO_INTERVALO: 'aguardando_intervalo',
            EstadoChat.DETALHE_BOLETO: 'detalhe_boleto',
            EstadoChat.OPCOES_VISAO_INTERVALO: 'opcoes_visao_intervalo'
        }
        
        contexto = contexto_map.get(self.estado, 'menu_principal')
        resultado = self.intent_classifier.classificar_intencao(mensagem, contexto)
        
        intencao = resultado['intencao']
        parametros = resultado['parametros']
        
        # Processa baseado na intenção identificada
        if intencao == 'saudacao':
            # Para saudações, responde com boas-vindas e já apresenta visão dos boletos
            boas_vindas = self.conversational_agent.gerar_boas_vindas(self.saldo_atual)
            try:
                visao_boletos = self._gerar_visao_dia()
                return f"{boas_vindas}\n\n{visao_boletos}"
            except Exception as e:
                # Se houver erro, retorna apenas as boas-vindas
                return boas_vindas
        
        elif intencao == 'ver_pagamentos_hoje':
            return self._gerar_visao_dia()
        
        elif intencao == 'ver_pagamentos_data':
            if 'data' in parametros:
                return self._gerar_visao_dia(parametros['data'])
            else:
                self.estado = EstadoChat.AGUARDANDO_DATA
                return "📅 Por favor, me diga a data que deseja consultar (formato: AAAA-MM-DD)\nExemplo: 2025-10-20"
        
        elif intencao == 'ver_intervalo':
            if 'data' in parametros and 'data_fim' in parametros:
                return self._processar_intervalo(f"{parametros['data']} até {parametros['data_fim']}")
            elif 'data' in parametros and 'data_fim' not in parametros:
                # Se só tem data inicial, calcula automaticamente baseado na mensagem original
                return self._calcular_intervalo_automatico(mensagem)
            else:
                # Tenta calcular automaticamente mesmo sem parâmetros
                return self._calcular_intervalo_automatico(mensagem)
        
        elif intencao == 'ver_atrasados':
            return self._mostrar_boletos_atrasados()
        
        elif intencao == 'ver_opcoes_financiamento':
            # Verifica se há boletos no contexto para mostrar opções de financiamento
            boletos_dict = self.contexto.get('boletos_dict', {})
            boletos_vencidos = self.contexto.get('boletos_vencidos', [])
            
            if boletos_dict or boletos_vencidos:
                return self._mostrar_opcoes_financiamento()
            else:
                return "Para ver opções de financiamento, primeiro consulte os pagamentos do dia ou de uma data específica."
        
        elif intencao == 'pagar':
            if self.estado in [EstadoChat.OPCOES_VISAO_DIA, EstadoChat.DETALHE_BOLETO, EstadoChat.BOLETOS_ATRASADOS]:
                # Move para estado de confirmação ao invés de pagar diretamente
                self.estado = EstadoChat.OPCOES_VISAO_DIA  # Garante que está no estado certo
                return self._solicitar_confirmacao_pagamento()
            elif self.estado == EstadoChat.CONFIRMACAO_PAGAMENTO:
                # Usuário confirmou, executa o pagamento
                return self._processar_pagamento()
            else:
                return "Para pagar boletos, primeiro consulte os pagamentos do dia ou de uma data específica."
        
        elif intencao == 'ver_detalhes':
            # Permite ver detalhes sempre que houver boletos no contexto
            boletos_dict = self.contexto.get('boletos_dict', {})
            boletos_vencidos = self.contexto.get('boletos_vencidos', [])
            
            if boletos_dict or boletos_vencidos:
                # Verifica se a mensagem contém um código de boleto específico
                codigo_encontrado = self._extrair_codigo_boleto(mensagem)
                if codigo_encontrado:
                    # Usuário pediu detalhes de um boleto específico
                    return self._processar_detalhe_boleto(codigo_encontrado)
                else:
                    # Mostra lista geral e pede para escolher
                    self.estado = EstadoChat.DETALHE_BOLETO
                    return self._mostrar_lista_detalhada_boletos() + "\n\n💡 Digite o código do boleto que deseja ver em detalhes (ex: Boleto_1, BOL001)."
            else:
                return "Para ver detalhes dos boletos, primeiro consulte os pagamentos do dia ou de uma data específica."
        
        elif intencao == 'ver_valores_destaque':
            if self.estado == EstadoChat.OPCOES_VISAO_INTERVALO:
                return self._mostrar_valores_destaque()
            else:
                return "Para ver valores dos dias em destaque, primeiro consulte um período específico."
        
        elif intencao == 'voltar':
            return self._voltar_menu_principal()
        
        elif intencao == 'ajuda':
            return self._mostrar_ajuda()
        
        # Fallback específico para opções de financiamento
        elif any(palavra in mensagem.lower() for palavra in ['opções', 'financiamento', 'opcoes', 'financiar', 'capital', 'adiantamento']):
            # Verifica se há boletos no contexto para mostrar opções de financiamento
            boletos_dict = self.contexto.get('boletos_dict', {})
            boletos_vencidos = self.contexto.get('boletos_vencidos', [])
            
            if boletos_dict or boletos_vencidos:
                return self._mostrar_opcoes_financiamento()
            else:
                return "Para ver opções de financiamento, primeiro consulte os pagamentos do dia ou de uma data específica."
        
        # Fallback: tenta processar contextos específicos
        elif self.estado == EstadoChat.AGUARDANDO_DATA:
            return self._processar_data(mensagem)
        
        elif self.estado == EstadoChat.AGUARDANDO_INTERVALO:
            return self._processar_intervalo(mensagem)
        
        elif self.estado == EstadoChat.DETALHE_BOLETO:
            # A intenção 'pagar' já foi tratada acima
            # Para outras mensagens, processa como código de boleto
            return self._processar_detalhe_boleto(mensagem)
        
        elif self.estado == EstadoChat.OPCOES_VISAO_INTERVALO:
            # Processa perguntas sobre o intervalo visualizado
            return self._processar_opcoes_visao_intervalo(mensagem)
        
        else:
            return """❓ Desculpe, não entendi seu pedido.

Você pode me pedir coisas como:
• "Mostrar pagamentos de hoje"
• "Ver boletos atrasados"
• "Pagar os boletos"
• "Ver período de 2025-10-19 até 2025-10-30"

Ou use o menu abaixo:

""" + self._menu_principal_texto()
    
    def _iniciar_conversa(self) -> str:
        """Inicia a conversa com LLM"""
        self.estado = EstadoChat.MENU_PRINCIPAL
        return self.conversational_agent.gerar_boas_vindas(self.saldo_atual)
    
    def _processar_menu_principal(self, mensagem: str) -> str:
        """Processa escolha do menu principal"""
        if "1" in mensagem or "hoje" in mensagem:
            return self._gerar_visao_dia()
        
        elif "2" in mensagem or "outra data" in mensagem:
            self.estado = EstadoChat.AGUARDANDO_DATA
            return "📅 Por favor, digite a data no formato AAAA-MM-DD (ex: 2025-10-20):"
        
        elif "3" in mensagem or "período" in mensagem or "intervalo" in mensagem:
            self.estado = EstadoChat.AGUARDANDO_INTERVALO
            return "📅 Digite o intervalo de datas no formato: AAAA-MM-DD até AAAA-MM-DD\n(ex: 2025-10-19 até 2025-10-30)"
        
        elif "4" in mensagem or "atrasados" in mensagem:
            return self._mostrar_boletos_atrasados()
        
        else:
            return "❌ Opção não reconhecida. Por favor, escolha uma opção de 1 a 4."
    
    def _gerar_visao_dia(self, dia: str = None) -> str:
        """Gera visão de pagamento do dia com resposta conversacional da LLM"""
        try:
            if dia is None:
                dia = datetime.now().strftime('%Y-%m-%d')
            
            overview, boletos_dict = self.adapter.obter_visao_dia(dia)
            
            # Filtra boletos já pagos (verifica tanto o código quanto possíveis variações)
            boletos_dict_filtrados = {}
            for codigo, dados in boletos_dict.items():
                # Verifica se o código ou qualquer variação dele está na lista de pagos
                if codigo not in self.boletos_pagos:
                    boletos_dict_filtrados[codigo] = dados
            boletos_dict = boletos_dict_filtrados
            
            # Obtém boletos vencidos (sempre usa data ATUAL, não a data consultada)
            boletos_vencidos = self.adapter.obter_boletos_atrasados()
            boletos_vencidos = [b for b in boletos_vencidos if b['id'] not in self.boletos_pagos]
            
            # RECALCULA o overview após filtrar boletos pagos
            overview['total_boletos_no_dia'] = len(boletos_dict)
            overview['valor_total_no_dia'] = sum(b['valor'] for b in boletos_dict.values())
            overview['total_boletos_vencidos'] = len(boletos_vencidos)
            overview['valor_total_vencidos'] = sum(b['valor'] for b in boletos_vencidos)
            
            # Armazena no contexto para uso posterior
            self.contexto['overview'] = overview
            self.contexto['boletos_dict'] = boletos_dict
            self.contexto['boletos_vencidos'] = boletos_vencidos
            self.contexto['data_atual'] = dia
            
            self.estado = EstadoChat.OPCOES_VISAO_DIA
            
            # EXECUTA A ANÁLISE FINANCEIRA (passa lista de boletos pagos)
            analise_ia = ""
            try:
                overview_ia, boletos_crewai, temp_path = self.adapter.preparar_para_sugestao_acao(dia, boletos_pagos=self.boletos_pagos)
                from crew_integration import executar_analise_financeira
                
                analise_ia = executar_analise_financeira(
                    saldo_atual=self.saldo_atual,
                    boletos_file_path=temp_path
                )
                
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                analise_ia = f"Análise financeira indisponível no momento."
            
            # Armazena análise no contexto
            self.contexto['analise_ia'] = analise_ia
            
            # USA A LLM PARA GERAR RESPOSTA CONVERSACIONAL
            dados = {
                'overview': overview,
                'boletos_dict': boletos_dict,
                'boletos_vencidos': boletos_vencidos,
                'analise_ia': analise_ia
            }
            
            resposta = self.conversational_agent.gerar_resposta_visao_dia(dados, self.saldo_atual, data_consultada=dia)
            
            # ADICIONA SUGESTÃO AUTOMÁTICA DO QUITADOR
            total_boletos = overview.get('total_boletos_no_dia', 0) + overview.get('total_boletos_vencidos', 0)
            total_valor = overview.get('valor_total_no_dia', 0) + overview.get('valor_total_vencidos', 0)
            
            if total_boletos > 0:
                if self.saldo_atual >= total_valor:
                    # Saldo suficiente - sugere pagamento direto
                    sugestao = f"\n\nSUGESTÃO DO QUITADOR:\nComo seu saldo é suficiente, recomendo pagar todos os boletos agora para evitar juros. Deseja executar o pagamento?"
                else:
                    # Saldo insuficiente - calcula e apresenta a melhor opção diretamente
                    deficit = total_valor - self.saldo_atual
                    
                    # Importa função de cálculo
                    import sys
                    sys.path.append('/home/blomes/projects/Pagamento - BTG/Sugestao-acao')
                    from financial_tools_simple import calcular_melhor_financiamento
                    
                    # Calcula opções
                    custo_giro = deficit * 0.08  # 8%
                    custo_adiantamento = deficit * 0.15  # 15%
                    
                    # Calcula estratégia de pagamento parcial
                    boletos_dict = self.contexto.get('boletos_dict', {})
                    boletos_vencidos = self.contexto.get('boletos_vencidos', [])
                    
                    # Combina todos os boletos com juros
                    todos_boletos = []
                    for codigo, dados in boletos_dict.items():
                        todos_boletos.append({
                            'id': codigo,
                            'valor': dados['valor'],
                            'juros_diario': 0.01,  # 1% ao dia para boletos do dia
                            'beneficiario': dados.get('beneficiario', 'Não informado'),
                            'tipo': 'do_dia'
                        })
                    
                    for bol in boletos_vencidos:
                        todos_boletos.append({
                            'id': bol['id'],
                            'valor': bol['valor'],
                            'juros_diario': 0.01,  # 1% ao dia para boletos vencidos
                            'beneficiario': bol.get('beneficiario', 'Não informado'),
                            'tipo': 'vencido'
                        })
                    
                    # Calcula estratégia de pagamento parcial
                    estrategia_parcial = self._calcular_pagamento_parcial(todos_boletos, self.saldo_atual)
                    
                    # Determina melhor opção - SEMPRE considera pagamento parcial se custo for menor
                    custo_pagamento_parcial = estrategia_parcial['custo_juros']
                    
                    if custo_pagamento_parcial < custo_giro and custo_pagamento_parcial < custo_adiantamento:
                        melhor_opcao = ('PAGAMENTO PARCIAL', custo_pagamento_parcial)
                    elif custo_giro < custo_adiantamento:
                        melhor_opcao = ('CAPITAL DE GIRO', custo_giro)
                    else:
                        melhor_opcao = ('ADIANTAMENTO DE RECEBÍVEIS', custo_adiantamento)
                    
                    # Armazena estratégia parcial se for a melhor opção
                    if melhor_opcao[0] == 'PAGAMENTO PARCIAL':
                        self._estrategia_parcial_atual = estrategia_parcial
                    else:
                        self._estrategia_parcial_atual = None
                    
                    # Gera sugestão específica baseada na melhor opção
                    if melhor_opcao[0] == 'CAPITAL DE GIRO':
                        sugestao = f"\n\nSUGESTÃO DO QUITADOR:\nRecomendo usar Capital de Giro a 8% para cobrir o déficit de R$ {deficit:,.2f}. Custo total: R$ {custo_giro:,.2f}. Deseja executar esta estratégia?"
                    elif melhor_opcao[0] == 'ADIANTAMENTO DE RECEBÍVEIS':
                        sugestao = f"\n\nSUGESTÃO DO QUITADOR:\nRecomendo Adiantamento de Recebíveis a 15% para cobrir o déficit de R$ {deficit:,.2f}. Custo total: R$ {custo_adiantamento:,.2f}. Deseja executar esta estratégia?"
                    else:  # PAGAMENTO PARCIAL
                        # SEMPRE armazena estratégia parcial quando recomendada
                        self._estrategia_parcial_atual = estrategia_parcial
                        sugestao = f"\n\nSUGESTÃO DO QUITADOR:\nRecomendo Pagamento Parcial Inteligente: pagar R$ {estrategia_parcial['valor_pagar_agora']:,.2f} agora e deixar R$ {estrategia_parcial['valor_deixar_depois']:,.2f} para amanhã. Custo de juros: apenas R$ {estrategia_parcial['custo_juros']:,.2f}. Deseja executar esta estratégia?"
                    
                    sugestao += f"\n\nSe quiser ver todas as opções detalhadas, digite 'ver opções de financiamento'."
                
                resposta += sugestao
            
            return resposta
            
        except Exception as e:
            self.estado = EstadoChat.MENU_PRINCIPAL
            return self.conversational_agent.gerar_resposta_generica(
                "erro_ao_obter_visao",
                {"erro": str(e)}
            )
    
    def _processar_data(self, mensagem: str) -> str:
        """Processa data fornecida pelo usuário"""
        try:
            # Tenta parsear a data
            datetime.strptime(mensagem.strip(), '%Y-%m-%d')
            return self._gerar_visao_dia(mensagem.strip())
        except ValueError:
            return "❌ Data inválida. Por favor, use o formato AAAA-MM-DD (ex: 2025-10-20):"
    
    def _processar_opcoes_visao_dia(self, mensagem: str) -> str:
        """Processa opções após visualizar o dia"""
        # Usa o classificador de intenções para entender melhor o que o usuário quer
        resultado = self.intent_classifier.classificar_intencao(mensagem, 'opcoes_visao_dia')
        intencao = resultado['intencao']
        
        if intencao == 'pagar':
            return self._processar_pagamento()
        
        elif intencao == 'ver_detalhes':
            self.estado = EstadoChat.DETALHE_BOLETO
            boletos = list(self.contexto.get('boletos_dict', {}).keys())
            if boletos:
                return f"🔍 Digite o código do boleto que deseja ver detalhes:\n\nBoletos disponíveis: {', '.join(boletos)}"
            else:
                return "❌ Nenhum boleto disponível para visualizar detalhes."
        
        elif intencao == 'ver_opcoes_financiamento':
            return self._mostrar_opcoes_financiamento()
        
        elif intencao == 'voltar':
            return self._voltar_menu_principal()
        
        else:
            # Fallback para padrões antigos
            if "1" in mensagem or "seguir" in mensagem or "executar" in mensagem or "pagar" in mensagem:
                return self._processar_pagamento()
            
            elif "2" in mensagem or "detalhe" in mensagem or "boleto" in mensagem:
                self.estado = EstadoChat.DETALHE_BOLETO
                boletos = list(self.contexto.get('boletos_dict', {}).keys())
                if boletos:
                    return f"🔍 Digite o código do boleto que deseja ver detalhes:\n\nBoletos disponíveis: {', '.join(boletos)}"
                else:
                    return "❌ Nenhum boleto disponível para visualizar detalhes."
            
            elif "3" in mensagem or "menu" in mensagem or "voltar" in mensagem or "alternativa" in mensagem:
                return self._voltar_menu_principal()
            
            # Fallback específico para opções de financiamento
            elif any(palavra in mensagem.lower() for palavra in ['opções', 'financiamento', 'opcoes', 'financiar', 'capital', 'adiantamento']):
                return self._mostrar_opcoes_financiamento()
            
            else:
                return "❌ Opção não reconhecida. Por favor, escolha uma opção de 1 a 3."
    
    def _solicitar_confirmacao_pagamento(self) -> str:
        """Solicita confirmação explícita antes de executar pagamento"""
        overview = self.contexto.get('overview', {})
        boletos_dict = self.contexto.get('boletos_dict', {})
        boletos_vencidos = self.contexto.get('boletos_vencidos', [])
        
        # Se não há boletos para pagar, informa o usuário
        if not boletos_dict and not boletos_vencidos:
            self.estado = EstadoChat.MENU_PRINCIPAL
            return "✅ Ótima notícia! Não há boletos pendentes para pagar. Todos os boletos estão em dia!"
        
        valor_dia = overview.get('valor_total_no_dia', 0)
        valor_vencidos = overview.get('valor_total_vencidos', 0)
        valor_total = valor_dia + valor_vencidos
        
        # VERIFICA SALDO INSUFICIENTE ANTES DE CONFIRMAR
        if self.saldo_atual < valor_total:
            # Define estado para confirmação de pagamento
            self.estado = EstadoChat.CONFIRMACAO_PAGAMENTO
            return self._gerar_estrategias_financiamento(valor_total, boletos_dict, boletos_vencidos)
        
        # Lista os beneficiários
        lista_beneficiarios = []
        for dados in boletos_dict.values():
            beneficiario = dados.get('beneficiario', 'Não informado')
            lista_beneficiarios.append(f"  • {beneficiario}: R$ {dados['valor']:,.2f}")
        
        for bol in boletos_vencidos:
            beneficiario = bol.get('beneficiario', 'Não informado')
            lista_beneficiarios.append(f"  • {beneficiario}: R$ {bol['valor']:,.2f} (vencido)")
        
        confirmacao = f"""
📋 CONFIRMAÇÃO DE PAGAMENTO

Boletos do dia: {len(boletos_dict)} (R$ {valor_dia:,.2f})
Boletos vencidos: {len(boletos_vencidos)} (R$ {valor_vencidos:,.2f})

Beneficiários:
{chr(10).join(lista_beneficiarios)}

💰 VALOR TOTAL A PAGAR: R$ {valor_total:,.2f}
💳 SALDO ATUAL: R$ {self.saldo_atual:,.2f}
💵 SALDO APÓS PAGAMENTO: R$ {self.saldo_atual - valor_total:,.2f}

✅ Confirma a execução do pagamento? (Digite 'sim' para confirmar ou 'não' para cancelar)
"""
        
        self.estado = EstadoChat.CONFIRMACAO_PAGAMENTO
        return confirmacao.strip()
    
    def _processar_pagamento(self) -> str:
        """Processa o pagamento de boletos com resposta conversacional"""
        overview = self.contexto.get('overview', {})
        valor_total = overview.get('valor_total_no_dia', 0) + overview.get('valor_total_vencidos', 0)
        saldo_anterior = self.saldo_atual
        
        if self.saldo_atual >= valor_total:
            # SALDO SUFICIENTE - Pagamento direto
            self.saldo_atual -= valor_total
            
            # Registra os boletos como pagos
            boletos_dict = self.contexto.get('boletos_dict', {})
            dia = self.contexto.get('data_atual')
            
            # Adiciona boletos do dia aos pagos
            for codigo in boletos_dict.keys():
                if codigo not in self.boletos_pagos:
                    self.boletos_pagos.append(codigo)
            
            # Adiciona boletos vencidos aos pagos (usa data atual, não a consultada)
            try:
                boletos_vencidos = self.adapter.obter_boletos_atrasados()
                for boleto in boletos_vencidos:
                    boleto_id = boleto['id']
                    if boleto_id not in self.boletos_pagos:
                        self.boletos_pagos.append(boleto_id)
            except:
                pass
            
            # USA A LLM PARA GERAR RESPOSTA CONVERSACIONAL
            resposta = self.conversational_agent.gerar_resposta_pagamento(
                valor_total, saldo_anterior, self.saldo_atual, len(self.boletos_pagos)
            )
        else:
            # SALDO INSUFICIENTE - Verifica se deve executar pagamento parcial
            # Verifica se a estratégia recomendada foi pagamento parcial
            if hasattr(self, '_estrategia_parcial_atual') and self._estrategia_parcial_atual:
                return self._executar_pagamento_parcial()
            
            deficit = valor_total - self.saldo_atual
            
            # Calcula custo do financiamento usando a análise da IA
            try:
                dia = self.contexto.get('data_atual', datetime.now().strftime('%Y-%m-%d'))
                overview_ia, boletos_crewai, temp_path = self.adapter.preparar_para_sugestao_acao(dia, boletos_pagos=self.boletos_pagos)
                from crew_integration import executar_analise_financeira
                
                analise_ia = executar_analise_financeira(
                    saldo_atual=self.saldo_atual,
                    boletos_file_path=temp_path
                )
                
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Extrai custo do financiamento da análise (simulação)
                # Em uma implementação real, isso viria da análise da IA
                import sys
                sys.path.append('/home/blomes/projects/Pagamento - BTG/Sugestao-acao')
                from financial_tools_simple import calcular_melhor_financiamento
                custo_financiamento, metodo, total_com_juros = calcular_melhor_financiamento(deficit)
                
                # Executa o financiamento
                self.saldo_atual += deficit  # Adiciona o valor financiado
                self.saldo_atual -= valor_total  # Paga os boletos
                
                # Registra os boletos como pagos
                boletos_dict = self.contexto.get('boletos_dict', {})
                for codigo in boletos_dict.keys():
                    if codigo not in self.boletos_pagos:
                        self.boletos_pagos.append(codigo)
                
                try:
                    boletos_vencidos = self.adapter.obter_boletos_atrasados()
                    for boleto in boletos_vencidos:
                        boleto_id = boleto['id']
                        if boleto_id not in self.boletos_pagos:
                            self.boletos_pagos.append(boleto_id)
                except:
                    pass
                
                # Gera resposta conversacional sobre financiamento executado
                resposta = f"""✅ Pagamento realizado pelo Quitador com financiamento!

💳 Valor pago: R$ {valor_total:,.2f}
🏦 Financiamento: {metodo} (R$ {deficit:,.2f})
💸 Custo do financiamento: R$ {custo_financiamento:,.2f}
💰 Saldo atual: R$ {self.saldo_atual:,.2f}

Todos os boletos foram quitados com sucesso! Posso ajudar com mais alguma coisa?"""
                
            except Exception as e:
                resposta = f"❌ Erro ao executar financiamento: {str(e)}"
        
        self.estado = EstadoChat.MENU_PRINCIPAL
        return resposta
    
    def _mostrar_opcoes_financiamento(self) -> str:
        """Mostra todas as opções de financiamento disponíveis"""
        try:
            overview = self.contexto.get('overview', {})
            valor_total = overview.get('valor_total_no_dia', 0) + overview.get('valor_total_vencidos', 0)
            deficit = valor_total - self.saldo_atual
            
            if deficit <= 0:
                return "✅ Seu saldo é suficiente para pagar todos os boletos sem necessidade de financiamento!"
            
            # Importa função de cálculo
            import sys
            sys.path.append('/home/blomes/projects/Pagamento - BTG/Sugestao-acao')
            from financial_tools_simple import calcular_melhor_financiamento, RECEBIVEIS_FUTUROS
            
            # Calcula opções
            custo_giro = deficit * 0.08  # 8%
            custo_adiantamento = deficit * 0.15  # 15%
            
            # Calcula recebíveis disponíveis
            total_recebiveis = sum(r["valor"] for r in RECEBIVEIS_FUTUROS)
            
            # NOVA OPÇÃO 3: Pagamento parcial inteligente
            boletos_dict = self.contexto.get('boletos_dict', {})
            boletos_vencidos = self.contexto.get('boletos_vencidos', [])
            
            # Combina todos os boletos com juros
            todos_boletos = []
            for codigo, dados in boletos_dict.items():
                todos_boletos.append({
                    'id': codigo,
                    'valor': dados['valor'],
                    'juros_diario': 0.01,  # 1% ao dia para boletos do dia
                    'beneficiario': dados.get('beneficiario', 'Não informado'),
                    'tipo': 'do_dia'
                })
            
            for bol in boletos_vencidos:
                todos_boletos.append({
                    'id': bol['id'],
                    'valor': bol['valor'],
                    'juros_diario': 0.01,  # 1% ao dia para boletos vencidos
                    'beneficiario': bol.get('beneficiario', 'Não informado'),
                    'tipo': 'vencido'
                })
            
            # Calcula estratégia de pagamento parcial
            estrategia_parcial = self._calcular_pagamento_parcial(todos_boletos, self.saldo_atual)
            
            # Armazena estratégia parcial para uso posterior
            self._estrategia_parcial_atual = estrategia_parcial
            
            resposta = f"""ANÁLISE COMPARATIVA DE FINANCIAMENTO

Situação Atual:
• Valor total a pagar: R$ {valor_total:,.2f}
• Saldo disponível: R$ {self.saldo_atual:,.2f}
• Déficit a cobrir: R$ {deficit:,.2f}

OPÇÃO 1: CAPITAL DE GIRO
• Taxa: 8% ao mês
• Custo do financiamento: R$ {custo_giro:,.2f}
• Total a pagar: R$ {deficit + custo_giro:,.2f}
• Processo: Aprovação rápida (até 2h)
• Garantias: Sem necessidade de garantias específicas

OPÇÃO 2: ADIANTAMENTO DE RECEBÍVEIS
• Taxa: 15% ao mês
• Custo do financiamento: R$ {custo_adiantamento:,.2f}
• Total a pagar: R$ {deficit + custo_adiantamento:,.2f}
• Recebíveis disponíveis: R$ {total_recebiveis:,.2f}
• Processo: Análise de recebíveis (até 24h)
• Garantias: Recebíveis futuros como garantia

OPÇÃO 3: PAGAMENTO PARCIAL INTELIGENTE
• Pagar agora: R$ {estrategia_parcial['valor_pagar_agora']:,.2f}
• Deixar para depois: R$ {estrategia_parcial['valor_deixar_depois']:,.2f}
• Custo de juros (1 dia): R$ {estrategia_parcial['custo_juros']:,.2f}
• Total economizado: R$ {estrategia_parcial['economia']:,.2f}
• Processo: Imediato (sem aprovação)
• Garantias: Recebíveis futuros cobrem déficit

RECEBÍVEIS FUTUROS DISPONÍVEIS:
"""
            
            for rec in RECEBIVEIS_FUTUROS:
                resposta += f"• {rec['data']}: R$ {rec['valor']:,.2f} ({rec['origem']})\n"
            
            # Adiciona detalhes dos boletos por estratégia
            resposta += f"""

DETALHES POR ESTRATÉGIA:

PAGAMENTO PARCIAL - Boletos que seriam pagos agora:
"""
            for boleto in estrategia_parcial['boletos_pagar_agora']:
                resposta += f"• {boleto['beneficiario']}: R$ {boleto['valor']:,.2f}\n"
            
            resposta += f"\nBoletos que ficariam para depois:\n"
            for boleto in estrategia_parcial['boletos_deixar_depois']:
                resposta += f"• {boleto['beneficiario']}: R$ {boleto['valor']:,.2f}\n"
            
            # Determina melhor opção considerando todas as três
            opcoes = [
                ('CAPITAL DE GIRO', custo_giro),
                ('ADIANTAMENTO DE RECEBÍVEIS', custo_adiantamento),
                ('PAGAMENTO PARCIAL', estrategia_parcial['custo_juros'])
            ]
            
            melhor_opcao = min(opcoes, key=lambda x: x[1])
            
            # Se pagamento parcial for a melhor opção, marca para execução
            if melhor_opcao[0] == 'PAGAMENTO PARCIAL':
                self._estrategia_parcial_atual = estrategia_parcial
            else:
                self._estrategia_parcial_atual = None
            
            resposta += f"""

RECOMENDAÇÃO DO QUITADOR: {melhor_opcao[0]}
• Menor custo total: R$ {melhor_opcao[1]:,.2f}
• Mais vantajoso financeiramente

Deseja executar esta estratégia recomendada pelo Quitador?"""
            
            # Move para estado de confirmação
            self.estado = EstadoChat.CONFIRMACAO_PAGAMENTO
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao calcular opções de financiamento: {str(e)}"
    
    def _mostrar_valores_destaque(self) -> str:
        """Mostra valores específicos dos dias em destaque do intervalo"""
        try:
            dashboard = self.contexto.get('dashboard_intervalo', {})
            data_inicio = self.contexto.get('data_inicio', '')
            data_fim = self.contexto.get('data_fim', '')
            
            if not dashboard:
                return "❌ Não há dados de intervalo disponíveis. Consulte um período primeiro."
            
            resposta = f"""VALORES DOS DIAS EM DESTAQUE

Período: {data_inicio} até {data_fim}

DIAS COM MAIORES VALORES:
"""
            
            # Dias com maiores valores
            dias_valor = dashboard.get('dias_valor', {})
            if dias_valor:
                for i, (dia, valor) in enumerate(list(dias_valor.items())[:3], 1):
                    resposta += f"{i}º {dia}: R$ {valor:,.2f}\n"
            else:
                resposta += "• Nenhum dia com valores específicos encontrado\n"
            
            resposta += f"""
DIAS COM MAIS BOLETOS:
"""
            
            # Dias com mais boletos
            dias_boletos = dashboard.get('dias_boletos', {})
            if dias_boletos:
                for i, (dia, qtd) in enumerate(list(dias_boletos.items())[:3], 1):
                    resposta += f"{i}º {dia}: {qtd} boletos\n"
            else:
                resposta += "• Nenhum dia com boletos específicos encontrado\n"
            
            resposta += f"""
VISÃO DE URGÊNCIA (Primeiros dias):
"""
            
            # Visão urgente (FILTRA boletos já pagos)
            visao_urgente = dashboard.get('visao_urgente', {})
            if visao_urgente:
                for dia, boletos in list(visao_urgente.items())[:3]:
                    # Filtra boletos não pagos
                    boletos_nao_pagos = [b for b in boletos if b['id'] not in self.boletos_pagos]
                    if boletos_nao_pagos:  # Só mostra se há boletos não pagos
                        valor_dia = sum(b['valor'] for b in boletos_nao_pagos)
                        resposta += f"• {dia}: {len(boletos_nao_pagos)} boletos - R$ {valor_dia:,.2f}\n"
            else:
                resposta += "• Nenhum boleto urgente encontrado\n"
            
            resposta += f"""
RESUMO:
• Total de dias analisados: {len(dias_valor) + len(dias_boletos)}
• Maior valor em um dia: R$ {max(dias_valor.values()) if dias_valor else 0:,.2f}
• Dia com mais boletos: {max(dias_boletos.items(), key=lambda x: x[1])[0] if dias_boletos else 'N/A'}

Posso ajudar com mais alguma coisa sobre este período?"""
            
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao mostrar valores dos dias em destaque: {str(e)}"
    
    def _mostrar_detalhes_boletos_intervalo(self) -> str:
        """Mostra detalhes dos boletos do período consultado"""
        try:
            dashboard = self.contexto.get('dashboard_intervalo', {})
            data_inicio = self.contexto.get('data_inicio', '')
            data_fim = self.contexto.get('data_fim', '')
            
            if not dashboard:
                return "❌ Não há dados de intervalo disponíveis. Consulte um período primeiro."
            
            resposta = f"""DETALHES DOS BOLETOS DO PERÍODO

Período: {data_inicio} até {data_fim}

BOLETOS POR DIA (Visão Urgente):
"""
            
            # Visão urgente - mostra boletos por dia (FILTRA boletos já pagos)
            visao_urgente = dashboard.get('visao_urgente', {})
            boletos_nao_pagos_por_dia = {}
            total_boletos_nao_pagos = 0
            
            if visao_urgente:
                for dia, boletos in visao_urgente.items():
                    # Filtra boletos não pagos
                    boletos_nao_pagos = [b for b in boletos if b['id'] not in self.boletos_pagos]
                    if boletos_nao_pagos:
                        boletos_nao_pagos_por_dia[dia] = boletos_nao_pagos
                        total_boletos_nao_pagos += len(boletos_nao_pagos)
            
            if boletos_nao_pagos_por_dia:
                for dia, boletos in boletos_nao_pagos_por_dia.items():
                    resposta += f"\n{dia}:\n"
                    for boleto in boletos:
                        beneficiario = boleto.get('beneficiario', 'Não informado')
                        resposta += f"• {boleto['id']}: {beneficiario} - R$ {boleto['valor']:,.2f}\n"
            else:
                resposta += "• Todos os boletos deste período já foram pagos! ✅\n"
            
            # Dias com maiores valores
            dias_valor = dashboard.get('dias_valor', {})
            if dias_valor:
                resposta += f"\nDIAS COM MAIORES VALORES:\n"
                for dia, valor in list(dias_valor.items())[:3]:
                    resposta += f"• {dia}: R$ {valor:,.2f}\n"
            
            # Dias com mais boletos
            dias_boletos = dashboard.get('dias_boletos', {})
            if dias_boletos:
                resposta += f"\nDIAS COM MAIS BOLETOS:\n"
                for dia, qtd in list(dias_boletos.items())[:3]:
                    resposta += f"• {dia}: {qtd} boletos\n"
            
            resposta += f"""
RESUMO DO PERÍODO:
• Total de dias com boletos não pagos: {len(boletos_nao_pagos_por_dia)}
• Total de boletos não pagos no período: {total_boletos_nao_pagos}
• Maior valor em um dia: R$ {max(dias_valor.values()) if dias_valor else 0:,.2f}

Posso ajudar com mais alguma coisa sobre este período?"""
            
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao mostrar detalhes dos boletos do período: {str(e)}"
    
    def _calcular_intervalo_automatico(self, mensagem: str) -> str:
        """Calcula intervalo automaticamente baseado na mensagem do usuário"""
        try:
            import re
            from datetime import datetime, timedelta
            
            # Extrai número de dias da mensagem
            mensagem_lower = mensagem.lower()
            
            # Padrões para detectar "próximos X dias/semanas/meses"
            padroes = [
                r'próximos?\s+(\d+)\s+dias?',
                r'próximas?\s+(\d+)\s+semanas?',
                r'próximos?\s+(\d+)\s+meses?',
                r'(\d+)\s+dias?\s+próximos?',
                r'(\d+)\s+semanas?\s+próximas?',
                r'(\d+)\s+meses?\s+próximos?'
            ]
            
            numero = None
            tipo_periodo = 'dias'
            
            for padrao in padroes:
                match = re.search(padrao, mensagem_lower)
                if match:
                    numero = int(match.group(1))
                    if 'semanas' in padrao:
                        tipo_periodo = 'semanas'
                    elif 'meses' in padrao:
                        tipo_periodo = 'meses'
                    break
            
            if numero is None:
                # Fallback: procura qualquer número na mensagem
                numeros = re.findall(r'\d+', mensagem)
                if numeros:
                    numero = int(numeros[0])
                else:
                    return "❌ Não consegui identificar quantos dias você quer consultar. Tente: 'próximos 20 dias'"
            
            # Calcula datas
            hoje = datetime.now().date()
            
            if tipo_periodo == 'dias':
                data_fim = hoje + timedelta(days=numero)
            elif tipo_periodo == 'semanas':
                data_fim = hoje + timedelta(weeks=numero)
            elif tipo_periodo == 'meses':
                # Aproximação: 1 mês = 30 dias
                data_fim = hoje + timedelta(days=numero * 30)
            
            # Formata as datas
            data_inicio_str = hoje.strftime('%Y-%m-%d')
            data_fim_str = data_fim.strftime('%Y-%m-%d')
            
            # Processa o intervalo calculado
            return self._processar_intervalo(f"{data_inicio_str} até {data_fim_str}")
            
        except Exception as e:
            return f"❌ Erro ao calcular intervalo automático: {str(e)}"
    
    def _processar_opcoes_visao_intervalo(self, mensagem: str) -> str:
        """Processa opções após visualizar o intervalo"""
        # Usa o classificador de intenções para entender melhor o que o usuário quer
        resultado = self.intent_classifier.classificar_intencao(mensagem, 'opcoes_visao_intervalo')
        intencao = resultado['intencao']
        
        if intencao == 'ver_valores_destaque':
            return self._mostrar_valores_destaque()
        
        elif intencao == 'ver_detalhes':
            return self._mostrar_detalhes_boletos_intervalo()
        
        elif intencao == 'voltar':
            return self._voltar_menu_principal()
        
        else:
            return "Posso ajudar com valores dos dias em destaque ou outras informações sobre o período. Como posso te auxiliar?"
    
    def _calcular_pagamento_parcial(self, todos_boletos: list, saldo_disponivel: float) -> dict:
        """Calcula estratégia de pagamento parcial inteligente"""
        try:
            # Ordena boletos por custo-benefício (maior valor com menor juros primeiro)
            boletos_ordenados = sorted(todos_boletos, key=lambda x: x['valor'] * x['juros_diario'], reverse=True)
            
            # Simula pagamento com saldo disponível
            boletos_pagar_agora = []
            boletos_deixar_depois = []
            saldo_restante = saldo_disponivel
            
            for boleto in boletos_ordenados:
                if saldo_restante >= boleto['valor']:
                    boletos_pagar_agora.append(boleto)
                    saldo_restante -= boleto['valor']
                else:
                    boletos_deixar_depois.append(boleto)
            
            # Calcula custos
            valor_pagar_agora = sum(b['valor'] for b in boletos_pagar_agora)
            valor_deixar_depois = sum(b['valor'] for b in boletos_deixar_depois)
            
            # Custo de juros por 1 dia (simulando que recebíveis caem amanhã)
            custo_juros = sum(b['valor'] * b['juros_diario'] for b in boletos_deixar_depois)
            
            # Calcula economia comparada ao financiamento total
            deficit_total = valor_pagar_agora + valor_deixar_depois - saldo_disponivel
            custo_financiamento_total = deficit_total * 0.08  # Capital de giro
            economia = custo_financiamento_total - custo_juros
            
            return {
                'boletos_pagar_agora': boletos_pagar_agora,
                'boletos_deixar_depois': boletos_deixar_depois,
                'valor_pagar_agora': valor_pagar_agora,
                'valor_deixar_depois': valor_deixar_depois,
                'custo_juros': custo_juros,
                'economia': economia,
                'saldo_restante': saldo_restante
            }
            
        except Exception as e:
            return {
                'boletos_pagar_agora': [],
                'boletos_deixar_depois': todos_boletos,
                'valor_pagar_agora': 0,
                'valor_deixar_depois': sum(b['valor'] for b in todos_boletos),
                'custo_juros': 0,
                'economia': 0,
                'saldo_restante': saldo_disponivel
            }
    
    def _executar_pagamento_parcial(self) -> str:
        """Executa pagamento parcial baseado na estratégia calculada"""
        try:
            if not hasattr(self, '_estrategia_parcial_atual') or not self._estrategia_parcial_atual:
                return "❌ Erro: Estratégia de pagamento parcial não encontrada."
            
            estrategia = self._estrategia_parcial_atual
            saldo_anterior = self.saldo_atual
            
            # Executa pagamento apenas dos boletos selecionados
            self.saldo_atual -= estrategia['valor_pagar_agora']
            
            # Registra apenas os boletos pagos como pagos
            for boleto in estrategia['boletos_pagar_agora']:
                if boleto['id'] not in self.boletos_pagos:
                    self.boletos_pagos.append(boleto['id'])
            
            # Lista boletos pagos e deixados para depois
            boletos_pagos_texto = ""
            for boleto in estrategia['boletos_pagar_agora']:
                boletos_pagos_texto += f"• {boleto['beneficiario']}: R$ {boleto['valor']:,.2f}\n"
            
            boletos_deixados_texto = ""
            for boleto in estrategia['boletos_deixar_depois']:
                boletos_deixados_texto += f"• {boleto['beneficiario']}: R$ {boleto['valor']:,.2f}\n"
            
            resposta = f"""PAGAMENTO PARCIAL EXECUTADO COM SUCESSO!

Boletos Pagos Agora:
{boletos_pagos_texto}
Valor pago: R$ {estrategia['valor_pagar_agora']:,.2f}

Boletos Deixados para Amanhã:
{boletos_deixados_texto}
Custo de juros (1 dia): R$ {estrategia['custo_juros']:,.2f}

Resumo:
• Saldo anterior: R$ {saldo_anterior:,.2f}
• Saldo atual: R$ {self.saldo_atual:,.2f}
• Economia total: R$ {estrategia['economia']:,.2f}

Estratégia inteligente executada! Os recebíveis futuros cobrirão os boletos restantes amanhã.

Posso ajudar com mais alguma coisa?"""
            
            # Limpa estratégia parcial
            self._estrategia_parcial_atual = None
            self.estado = EstadoChat.MENU_PRINCIPAL
            
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao executar pagamento parcial: {str(e)}"
    
    def _gerar_estrategias_financiamento(self, valor_total: float, boletos_dict: dict, boletos_vencidos: list) -> str:
        """Gera estratégias de financiamento quando saldo é insuficiente"""
        try:
            deficit = valor_total - self.saldo_atual
            
            # Calcula estratégias de financiamento usando a mesma lógica da visão do dia
            custo_giro = deficit * 0.08  # 8%
            custo_adiantamento = deficit * 0.15  # 15%
            
            # Calcula estratégia de pagamento parcial
            todos_boletos = []
            for codigo, dados in boletos_dict.items():
                todos_boletos.append({
                    'id': codigo,
                    'valor': dados['valor'],
                    'juros_diario': 0.01,  # 1% ao dia para boletos do dia
                    'beneficiario': dados.get('beneficiario', 'Não informado'),
                    'tipo': 'do_dia'
                })
            
            for bol in boletos_vencidos:
                todos_boletos.append({
                    'id': bol['id'],
                    'valor': bol['valor'],
                    'juros_diario': 0.01,  # 1% ao dia para boletos vencidos
                    'beneficiario': bol.get('beneficiario', 'Não informado'),
                    'tipo': 'vencido'
                })
            
            # Calcula estratégia de pagamento parcial
            estrategia_parcial = self._calcular_pagamento_parcial(todos_boletos, self.saldo_atual)
            
            # Determina melhor opção - SEMPRE considera pagamento parcial se custo for menor
            custo_pagamento_parcial = estrategia_parcial['custo_juros']
            
            if custo_pagamento_parcial < custo_giro and custo_pagamento_parcial < custo_adiantamento:
                melhor_opcao = ('PAGAMENTO PARCIAL', custo_pagamento_parcial)
            elif custo_giro < custo_adiantamento:
                melhor_opcao = ('CAPITAL DE GIRO', custo_giro)
            else:
                melhor_opcao = ('ADIANTAMENTO DE RECEBÍVEIS', custo_adiantamento)
            
            # Armazena estratégia parcial se for a melhor opção
            if melhor_opcao[0] == 'PAGAMENTO PARCIAL':
                self._estrategia_parcial_atual = estrategia_parcial
            else:
                self._estrategia_parcial_atual = None
            
            # Executa análise financeira para obter estratégias
            analise_ia = ""
            try:
                dia = self.contexto.get('data_atual', datetime.now().strftime('%Y-%m-%d'))
                overview_ia, boletos_crewai, temp_path = self.adapter.preparar_para_sugestao_acao(dia, boletos_pagos=self.boletos_pagos)
                from crew_integration import executar_analise_financeira
                
                analise_ia = executar_analise_financeira(
                    saldo_atual=self.saldo_atual,
                    boletos_file_path=temp_path
                )
                
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                analise_ia = f"Análise financeira indisponível: {str(e)}"
            
            # Lista os beneficiários para contexto
            lista_beneficiarios = []
            for dados in boletos_dict.values():
                beneficiario = dados.get('beneficiario', 'Não informado')
                lista_beneficiarios.append(f"  • {beneficiario}: R$ {dados['valor']:,.2f}")
            
            for bol in boletos_vencidos:
                beneficiario = bol.get('beneficiario', 'Não informado')
                lista_beneficiarios.append(f"  • {beneficiario}: R$ {bol['valor']:,.2f} (vencido)")
            
            # Usa LLM para gerar resposta conversacional sobre estratégias
            prompt = f"""Você é um assistente financeiro do BTG. O usuário tem saldo insuficiente para pagar todos os boletos.

SITUAÇÃO:
- Valor total a pagar: R$ {valor_total:,.2f}
- Saldo disponível: R$ {self.saldo_atual:,.2f}
- Déficit: R$ {deficit:,.2f}

BOLETOS A PAGAR:
{chr(10).join(lista_beneficiarios)}

ESTRATÉGIA RECOMENDADA: {melhor_opcao[0]}
- Custo total: R$ {melhor_opcao[1]:,.2f}

ANÁLISE FINANCEIRA DA IA:
{analise_ia}

Gere uma resposta CONVERSACIONAL (4-5 linhas) que:
1. Explique que o saldo é insuficiente
2. Apresente a estratégia recomendada ({melhor_opcao[0]}) com seu custo
3. Mencione os benefícios da estratégia escolhida
4. Pergunte se deseja executar a estratégia recomendada

Seja NATURAL, DIRETO e CONVINCENTE. NÃO use muitos emojis."""

            resposta = self.conversational_agent._chamar_llm(prompt, max_tokens=400)
            
            # Move para estado de confirmação de financiamento
            self.estado = EstadoChat.CONFIRMACAO_PAGAMENTO
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao gerar estratégias de financiamento: {str(e)}"
    
    def _extrair_codigo_boleto(self, mensagem: str) -> str:
        """Extrai código de boleto da mensagem (ex: Boleto_1, BOL001)"""
        import re
        msg_upper = mensagem.upper()
        
        # Padrões: Boleto_X, BOLX, BOL_X, BOLXXX
        padroes = [
            r'BOLETO[_\s]*(\d+)',  # Boleto_1, Boleto 1
            r'BOL[_\s]*(\d+)',      # BOL_001, BOL 001
            r'\bBOL(\d{3,})\b'      # BOL001
        ]
        
        for padrao in padroes:
            match = re.search(padrao, msg_upper)
            if match:
                # Verifica nos boletos do dia
                for codigo in self.contexto.get('boletos_dict', {}).keys():
                    if match.group(0) in codigo.upper() or match.group(1) in codigo:
                        return codigo
                
                # Verifica nos boletos vencidos
                for bol in self.contexto.get('boletos_vencidos', []):
                    if match.group(0) in bol['id'].upper() or match.group(1) in bol['id']:
                        return bol['id']
        
        return None
    
    def _mostrar_lista_detalhada_boletos(self) -> str:
        """Mostra lista detalhada de TODOS os boletos (do dia + vencidos) FILTRANDO boletos já pagos"""
        try:
            boletos_dict = self.contexto.get('boletos_dict', {})
            boletos_vencidos = self.contexto.get('boletos_vencidos', [])
            
            # FILTRA boletos já pagos
            boletos_dict_nao_pagos = {k: v for k, v in boletos_dict.items() if k not in self.boletos_pagos}
            boletos_vencidos_nao_pagos = [b for b in boletos_vencidos if b['id'] not in self.boletos_pagos]
            
            # Monta lista completa apenas com boletos não pagos
            lista_completa = ""
            
            if boletos_dict_nao_pagos:
                lista_completa += "BOLETOS VENCENDO HOJE:\n"
                for codigo, dados in boletos_dict_nao_pagos.items():
                    beneficiario = dados.get('beneficiario', 'Não informado')
                    lista_completa += f"- {codigo}: {beneficiario} - R$ {dados['valor']:,.2f}\n"
            
            if boletos_vencidos_nao_pagos:
                lista_completa += "\nBOLETOS VENCIDOS:\n"
                for bol in boletos_vencidos_nao_pagos:
                    beneficiario = bol.get('beneficiario', 'Não informado')
                    lista_completa += f"- {bol['id']}: {beneficiario} - R$ {bol['valor']:,.2f} (venceu em {bol.get('data_vencimento', 'N/A')})\n"
            
            # Se não há boletos não pagos, informa
            if not boletos_dict_nao_pagos and not boletos_vencidos_nao_pagos:
                return "✅ Ótima notícia! Todos os boletos já foram pagos. Não há pendências!"
            
            total_geral = (sum(b['valor'] for b in boletos_dict_nao_pagos.values()) + 
                          sum(b['valor'] for b in boletos_vencidos_nao_pagos))
            
            prompt = f"""Você é um assistente financeiro. O usuário pediu mais informações sobre os boletos.

LISTA COMPLETA DE BOLETOS A PAGAR (apenas não pagos):
{lista_completa}

TOTAL GERAL: R$ {total_geral:,.2f}
SALDO DISPONÍVEL: R$ {self.saldo_atual:,.2f}

Gere uma resposta CONVERSACIONAL (3-4 linhas) que:
1. Apresente a lista de forma organizada e clara
2. Destaque os principais (maiores valores ou mais urgentes)
3. Mencione que pode mostrar detalhes de qualquer boleto ou pagar todos

Seja NATURAL e PRESTATIVO."""

            resposta = self.conversational_agent._chamar_llm(prompt, max_tokens=400)
            return resposta
            
        except Exception as e:
            return self.conversational_agent.gerar_resposta_generica(
                "erro_ao_listar_boletos",
                {"erro": str(e)}
            )
    
    def _processar_detalhe_boleto(self, mensagem: str) -> str:
        """Mostra detalhes de um boleto específico com resposta conversacional"""
        try:
            # Tenta extrair código se ainda não foi extraído
            codigo_boleto = self._extrair_codigo_boleto(mensagem)
            if not codigo_boleto:
                # Tenta busca direta case-insensitive
                codigo_boleto = mensagem.strip()
            
            boletos_dict = self.contexto.get('boletos_dict', {})
            boletos_vencidos = self.contexto.get('boletos_vencidos', [])
            
            # Busca nos boletos do dia (case-insensitive)
            for codigo, dados in boletos_dict.items():
                if codigo.upper() == codigo_boleto.upper():
                    beneficiario = dados.get('beneficiario', 'Não informado')
                    valor_total = dados['valor'] + dados['juros']
                    
                    prompt = f"""Você é um assistente financeiro. O usuário pediu detalhes de um boleto.

DETALHES DO BOLETO:
- Código: {codigo}
- Beneficiário: {beneficiario}
- Valor principal: R$ {dados['valor']:,.2f}
- Juros acumulados: R$ {dados['juros']:,.2f}
- Valor total: R$ {valor_total:,.2f}
- Vencimento: {dados['data_vencimento']}

Gere uma resposta CONVERSACIONAL (2-3 linhas) apresentando esses detalhes de forma natural e amigável.
Pergunte se deseja pagar este boleto ou pagar todos os boletos.

Seja NATURAL e DIRETO."""

                    resposta = self.conversational_agent._chamar_llm(prompt, max_tokens=200)
                    self.estado = EstadoChat.DETALHE_BOLETO
                    return resposta
            
            # Busca nos boletos vencidos
            for bol in boletos_vencidos:
                if bol['id'].upper() == codigo_boleto.upper():
                    beneficiario = bol.get('beneficiario', 'Não informado')
                    
                    prompt = f"""Você é um assistente financeiro. O usuário pediu detalhes de um boleto vencido.

DETALHES DO BOLETO VENCIDO:
- Código: {bol['id']}
- Beneficiário: {beneficiario}
- Valor: R$ {bol['valor']:,.2f}
- Vencimento: {bol.get('data_vencimento', 'N/A')}
- Status: VENCIDO

Gere uma resposta CONVERSACIONAL (2-3 linhas) apresentando esses detalhes, alertando que está vencido.
Pergunte se deseja pagar este boleto ou pagar todos os boletos.

Seja NATURAL e DIRETO."""

                    resposta = self.conversational_agent._chamar_llm(prompt, max_tokens=200)
                    self.estado = EstadoChat.DETALHE_BOLETO
                    return resposta
            
            # Não encontrou
            self.estado = EstadoChat.DETALHE_BOLETO
            return f"Não encontrei o boleto '{codigo_boleto}'. Quer ver a lista completa de boletos disponíveis?"
            
        except Exception as e:
            return self.conversational_agent.gerar_resposta_generica(
                "erro_ao_buscar_detalhes",
                {"erro": str(e)}
            )
    
    def _obter_sugestao_ia(self) -> str:
        """Obtém sugestão de ação usando CrewAI"""
        try:
            resposta = "🤖 CONSULTANDO INTELIGÊNCIA ARTIFICIAL...\n\n"
            
            # Prepara dados para o CrewAI
            overview, boletos_crewai, temp_path = self.adapter.preparar_para_sugestao_acao(
                self.contexto.get('data_atual')
            )
            
            # Importa e executa o CrewAI
            from crew_integration import executar_analise_financeira
            
            resultado_ia = executar_analise_financeira(
                saldo_atual=self.saldo_atual,
                boletos_file_path=temp_path
            )
            
            resposta += f"📊 ANÁLISE DA IA:\n\n{resultado_ia}\n\n"
            
            # Remove arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            self.estado = EstadoChat.MENU_PRINCIPAL
            resposta += self._menu_principal_texto()
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao obter sugestão da IA: {str(e)}\n\nVoltando ao menu..."
    
    def _processar_intervalo(self, mensagem: str) -> str:
        """Processa consulta de intervalo de datas com resposta conversacional"""
        try:
            # Tenta extrair datas (formato: "2025-10-19 até 2025-10-30")
            partes = mensagem.replace("até", " ").replace("ate", " ").split()
            datas = [p for p in partes if len(p) == 10 and p.count('-') == 2]
            
            if len(datas) < 2:
                return "Por favor, me diga o intervalo de datas que deseja consultar."
            
            data_inicio = datas[0]
            data_fim = datas[1]
            
            # Valida datas
            datetime.strptime(data_inicio, '%Y-%m-%d')
            datetime.strptime(data_fim, '%Y-%m-%d')
            
            dashboard = self.adapter.obter_dash_intervalo(data_inicio, data_fim)
            
            # FILTRA boletos atrasados que já foram pagos nesta sessão
            atrasados_total = self.adapter.obter_boletos_atrasados()
            atrasados_nao_pagos = [b for b in atrasados_total if b['id'] not in self.boletos_pagos]
            
            # Atualiza o dashboard com os valores corretos (sem boletos pagos)
            dashboard['contas_atrasadas'] = {
                'quantidade': len(atrasados_nao_pagos),
                'valor_total': sum(b['valor'] for b in atrasados_nao_pagos)
            }
            
            # Filtra boletos pagos da visão urgente
            if 'visao_urgente' in dashboard:
                for dia, boletos in dashboard['visao_urgente'].items():
                    dashboard['visao_urgente'][dia] = [
                        b for b in boletos if b['id'] not in self.boletos_pagos
                    ]
            
            # USA A LLM PARA GERAR RESPOSTA CONVERSACIONAL
            resposta = self.conversational_agent.gerar_resposta_intervalo(
                dashboard, data_inicio, data_fim, self.saldo_atual
            )
            
            # Armazena dados do intervalo no contexto para perguntas posteriores
            self.contexto['dashboard_intervalo'] = dashboard
            self.contexto['data_inicio'] = data_inicio
            self.contexto['data_fim'] = data_fim
            
            self.estado = EstadoChat.OPCOES_VISAO_INTERVALO
            return resposta
            
        except Exception as e:
            return self.conversational_agent.gerar_resposta_generica(
                "erro_ao_processar_intervalo",
                {"erro": str(e)}
            )
    
    def _mostrar_boletos_atrasados(self) -> str:
        """Mostra lista de boletos atrasados com resposta conversacional"""
        try:
            atrasados = self.adapter.obter_boletos_atrasados()
            
            # Filtra boletos já pagos
            atrasados = [b for b in atrasados if b['id'] not in self.boletos_pagos]
            
            total_atrasado = sum(b['valor'] for b in atrasados) if atrasados else 0
            
            # USA A LLM PARA GERAR RESPOSTA CONVERSACIONAL
            resposta = self.conversational_agent.gerar_resposta_boletos_atrasados(
                atrasados, total_atrasado
            )
            
            self.estado = EstadoChat.MENU_PRINCIPAL
            return resposta
            
        except Exception as e:
            return self.conversational_agent.gerar_resposta_generica(
                "erro_ao_buscar_atrasados",
                {"erro": str(e)}
            )
    
    def _voltar_menu_principal(self) -> str:
        """Volta ao menu principal"""
        self.estado = EstadoChat.MENU_PRINCIPAL
        return self._menu_principal_texto()
    
    def _mostrar_ajuda(self) -> str:
        """Mostra ajuda ao usuário"""
        return f"""AJUDA - Assistente de Pagamentos BTG

Você pode conversar comigo naturalmente! Exemplos:

Ver boletos:
• "Mostrar meus boletos de hoje"
• "Ver pagamentos de amanhã"
• "Consultar boletos de 2025-10-20"
• "Quero ver boletos atrasados"

Consultar período:
• "Ver período de 19/10 até 30/10"
• "Mostrar intervalo entre 2025-10-19 e 2025-10-30"

Pagar boletos:
• "Pagar os boletos"
• "Quero executar o pagamento"
• "Seguir a recomendação da IA"

Ver detalhes:
• "Mostrar detalhes do boleto"
• "Ver informações do boleto X"

Navegação:
• "Voltar ao menu"
• "Menu principal"
• "Ajuda"

Seu saldo atual: R$ {self.saldo_atual:,.2f}
Boletos pagos nesta sessão: {len(self.boletos_pagos)}

{self._menu_principal_texto()}"""
    
    def _menu_principal_texto(self) -> str:
        """Retorna o texto do menu principal - NÃO É MAIS USADO (mantido por compatibilidade)"""
        return ""  # Não mostra mais menu fixo - apenas conversação natural


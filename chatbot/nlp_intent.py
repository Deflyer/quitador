"""
Módulo de Processamento de Linguagem Natural para entender intenções do usuário
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Tenta usar OpenAI para entendimento de intenção
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False


class IntentClassifier:
    """Classifica a intenção do usuário usando IA ou pattern matching"""
    
    INTENCOES = {
        'saudacao': [
            'oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'hey', 'hi',
            'hello', 'e aí', 'eai', 'salve', 'fala', 'tudo bem', 'td bem',
            'como vai', 'como está', 'tudo certo', 'beleza', 'eae', 'oie',
            'bom dia', 'boa tarde', 'boa noite', 'bom dia!', 'boa tarde!', 'boa noite!'
        ],
        'ver_pagamentos_hoje': [
            'pagamentos de hoje', 'boletos hoje', 'ver hoje', 'pagamento hoje',
            'o que vence hoje', 'contas de hoje', 'mostrar hoje'
        ],
        'ver_pagamentos_data': [
            'pagamentos de', 'boletos de', 'ver data', 'outra data',
            'data específica', 'consultar data'
        ],
        'ver_intervalo': [
            'período', 'intervalo', 'range', 'entre', 'do dia até',
            'visão período', 'dashboard período', 'próximos', 'próximas',
            'dias', 'semanas', 'meses', 'visualizar boletos dos próximos'
        ],
        'ver_atrasados': [
            'atrasados', 'vencidos', 'em atraso', 'contas atrasadas',
            'boletos vencidos', 'pendentes'
        ],
        'pagar': [
            'pagar', 'quitar', 'executar pagamento', 'fazer pagamento',
            'seguir recomendação', 'confirmar', 'sim', 'ok', 'pagar boletos',
            'pagar todos', 'efetuar pagamento', 'realizar pagamento', 'aceito',
            'aceito essa proposta', 'executar proposta', 'executar estratégia',
            'pagar assim', 'confirmo', 'aceito proposta', 'aceito estratégia',
            'quero executar', 'executar', 'prosseguir', 'continuar',
            'gostaria de seguir sua sugestão', 'seguir sua sugestão', 'seguir sugestão',
            'aceito sua sugestão', 'aceito a sugestão', 'concordo com a sugestão',
            'vamos com sua sugestão', 'vamos com a sugestão', 'fazer sua sugestão',
            'fazer a sugestão', 'aplicar sua sugestão', 'aplicar a sugestão',
            'implementar sua sugestão', 'implementar a sugestão', 'seguir recomendação',
            'aceito recomendação', 'concordo com recomendação', 'vamos com recomendação',
            'fazer recomendação', 'aplicar recomendação', 'implementar recomendação',
            'quero seguir', 'vou seguir', 'pode seguir', 'pode executar',
            'pode aplicar', 'pode implementar', 'pode fazer'
        ],
        'ver_detalhes': [
            'detalhes', 'informações', 'ver mais', 'detalhe do boleto',
            'mostrar boleto', 'info do boleto', 'saber mais', 'mais informações',
            'quais boletos', 'lista de boletos', 'quero saber mais', 'mostrar mais',
            'mais detalhes sobre esses boletos', 'detalhes sobre esses boletos',
            'me forneça mais detalhe sobre esses boletos', 'forneça mais detalhes'
        ],
        'ver_opcoes_financiamento': [
            'outras opções', 'opções de financiamento', 'visão das opções',
            'quanto ficaria', 'comparar opções', 'ver alternativas',
            'opções disponíveis', 'comparação', 'todas as opções', 'tem outra opção',
            'outra opção', 'mais opções', 'outras alternativas', 'mais detalhes dessa negociação',
            'detalhes da negociação', 'negociação', 'opções de negociação',
            'como funciona', 'explicar opções', 'ver como funciona',
            'me de opções de financiamento', 'me dê opções de financiamento',
            'quero opções de financiamento', 'preciso de opções de financiamento',
            'mostre opções de financiamento', 'opções de financiamento por favor'
        ],
        'ver_valores_destaque': [
            'qual valor desses dias destaque', 'valores dos dias destaque',
            'quanto custa esses dias', 'valores específicos', 'detalhes dos valores',
            'quanto é cada dia', 'valores por dia', 'custos dos dias',
            'mostrar valores', 'ver valores', 'quais os valores'
        ],
        'voltar': [
            'voltar', 'menu', 'cancelar', 'não', 'sair', 'retornar'
        ],
        'ajuda': [
            'ajuda', 'help', 'o que posso fazer', 'comandos',
            'como funciona', 'não entendi'
        ]
    }
    
    def __init__(self):
        self.use_openai = OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY')
    
    def classificar_intencao(self, mensagem: str, contexto: str = None) -> dict:
        """
        Classifica a intenção do usuário
        
        Args:
            mensagem: Mensagem do usuário
            contexto: Contexto atual da conversa (opcional)
        
        Returns:
            dict com 'intencao', 'confianca' e 'parametros'
        """
        mensagem_lower = mensagem.lower().strip()
        
        # Se for apenas um número, mapeia para contexto
        if mensagem_lower.isdigit():
            return self._processar_numero(mensagem_lower, contexto)
        
        # Tenta usar OpenAI se disponível
        if self.use_openai:
            try:
                return self._classificar_com_openai(mensagem, contexto)
            except:
                pass  # Fallback para pattern matching
        
        # Fallback: Pattern matching simples
        return self._classificar_com_patterns(mensagem_lower, contexto)
    
    def _processar_numero(self, numero: str, contexto: str) -> dict:
        """Processa entrada numérica baseada no contexto"""
        mapeamento = {
            'menu_principal': {
                '1': 'ver_pagamentos_hoje',
                '2': 'ver_pagamentos_data',
                '3': 'ver_intervalo',
                '4': 'ver_atrasados'
            },
            'opcoes_visao_dia': {
                '1': 'pagar',
                '2': 'ver_detalhes',
                '3': 'voltar'
            }
        }
        
        intencao = mapeamento.get(contexto, {}).get(numero, 'desconhecida')
        
        return {
            'intencao': intencao,
            'confianca': 1.0 if intencao != 'desconhecida' else 0.0,
            'parametros': {}
        }
    
    def _classificar_com_patterns(self, mensagem: str, contexto: str) -> dict:
        """Classificação usando pattern matching"""
        melhor_intencao = 'desconhecida'
        melhor_score = 0
        
        # PRIMEIRO: Verifica se é uma saudação (tem prioridade máxima)
        saudações = self.INTENCOES['saudacao']
        if any(saudacao in mensagem for saudacao in saudações):
            return {
                'intencao': 'saudacao',
                'confianca': 1.0,
                'parametros': {}
            }
        
        # Contexto especial: se está em opcoes_visao_dia e usuário quer pagar, move para confirmação
        if contexto == 'opcoes_visao_dia':
            # Primeiro verifica se é pedido de opções de financiamento
            pedidos_financiamento = ['mais detalhes dessa negociação', 'detalhes da negociação', 
                                   'negociação', 'opções de negociação', 'outras opções', 
                                   'opções de financiamento', 'como funciona', 'explicar opções']
            if any(fin in mensagem for fin in pedidos_financiamento):
                return {
                    'intencao': 'ver_opcoes_financiamento',
                    'confianca': 1.0,
                    'parametros': {}
                }
            
            # Depois verifica se NÃO é um pedido de informação sobre boletos
            pedidos_info = ['saber mais', 'mais informações', 'informações', 'detalhes', 
                           'mostrar', 'listar', 'ver boletos', 'quais boletos']
            if any(info in mensagem for info in pedidos_info):
                return {
                    'intencao': 'ver_detalhes',
                    'confianca': 1.0,
                    'parametros': {}
                }
            
            # Só depois verifica confirmações de pagamento
            confirmacoes = ['sim', 'yes', 'confirmo', 'confirmar', 'pode pagar', 
                           'executar pagamento', 'pagar agora', 'efetuar pagamento']
            if any(conf in mensagem for conf in confirmacoes):
                return {
                    'intencao': 'pagar',
                    'confianca': 1.0,
                    'parametros': {}
                }
        
        # Contexto especial: se está em confirmacao_pagamento aguardando sim/não
        if contexto == 'confirmacao_pagamento':
            confirmacoes_sim = ['sim', 'confirmo', 'ok', 'pode', 'pagar', 'executar', 'confirmar',
                              'aceito', 'aceito essa proposta', 'executar proposta', 'executar estratégia',
                              'pagar assim', 'aceito proposta', 'aceito estratégia', 'quero executar',
                              'prosseguir', 'continuar', 'sim,', 'aceito,', 'executar,']
            confirmacoes_nao = ['não', 'nao', 'cancelar', 'voltar', 'negativo']
            
            if any(conf in mensagem for conf in confirmacoes_sim):
                return {
                    'intencao': 'pagar',
                    'confianca': 1.0,
                    'parametros': {}
                }
            elif any(conf in mensagem for conf in confirmacoes_nao):
                return {
                    'intencao': 'voltar',
                    'confianca': 1.0,
                    'parametros': {}
                }
        
        for intencao, keywords in self.INTENCOES.items():
            score = sum(1 for kw in keywords if kw in mensagem)
            if score > melhor_score:
                melhor_score = score
                melhor_intencao = intencao
        
        # Extrai parâmetros básicos
        parametros = {}
        
        import re
        
        # Detecta "próximos X dias" ou "próximas X semanas"
        proximos_match = re.search(r'pr[oó]xim[oa]s?\s+(\d+)\s+(dia|semana|mes)', mensagem)
        if proximos_match:
            quantidade = int(proximos_match.group(1))
            unidade = proximos_match.group(2)
            
            hoje = datetime.now()
            parametros['data'] = hoje.strftime('%Y-%m-%d')
            
            if unidade == 'dia':
                data_fim = hoje + timedelta(days=quantidade)
            elif unidade == 'semana':
                data_fim = hoje + timedelta(weeks=quantidade)
            else:  # mes
                data_fim = hoje + timedelta(days=quantidade * 30)
            
            parametros['data_fim'] = data_fim.strftime('%Y-%m-%d')
            melhor_intencao = 'ver_intervalo'
            melhor_score = 10  # Alta confiança
        
        # Detecta datas no formato AAAA-MM-DD
        datas = re.findall(r'\d{4}-\d{2}-\d{2}', mensagem)
        if datas:
            parametros['data'] = datas[0]
            if len(datas) > 1:
                parametros['data_fim'] = datas[1]
        
        confianca = min(melhor_score / 2, 1.0)  # Normaliza
        
        return {
            'intencao': melhor_intencao,
            'confianca': confianca,
            'parametros': parametros
        }
    
    def _classificar_com_openai(self, mensagem: str, contexto: str) -> dict:
        """Usa OpenAI para classificar intenção com alta precisão"""
        
        contexto_info = ""
        if contexto == 'opcoes_visao_dia':
            contexto_info = """IMPORTANTE: Usuário acabou de ver a análise de boletos.
- Se ele CONFIRMAR explicitamente o pagamento ('sim, pagar agora', 'executar pagamento', 'confirmo', 'gostaria de seguir sua sugestão', 'aceito sua sugestão', 'vamos com sua sugestão'), a intenção é 'pagar'
- Se ele pedir MAIS INFORMAÇÕES sobre boletos ('quero saber mais', 'me mostre os boletos', 'detalhes'), a intenção é 'ver_detalhes'
- Se ele pedir OPÇÕES DE FINANCIAMENTO ('mais detalhes dessa negociação', 'opções de negociação', 'outras opções', 'me de opções de financiamento', 'me dê opções de financiamento'), a intenção é 'ver_opcoes_financiamento'
- NÃO confunda pedido de informações com confirmação de pagamento!"""
        elif contexto == 'confirmacao_pagamento':
            contexto_info = """IMPORTANTE: Usuário está na tela de confirmação de pagamento/financiamento.
- Se confirmar ('sim', 'aceito', 'executar', 'confirmo', 'pagar assim', 'executar proposta', 'gostaria de seguir sua sugestão', 'aceito sua sugestão', 'vamos com sua sugestão'), a intenção é 'pagar'
- Se cancelar ('não', 'cancelar'), a intenção é 'voltar'
- Palavras-chave de confirmação: sim, aceito, executar, confirmo, pagar, proposta, estratégia, sugestão, seguir, aplicar, implementar"""
        elif contexto == 'opcoes_visao_intervalo':
            contexto_info = """IMPORTANTE: Usuário acabou de ver a análise de um período/intervalo.
- Se pedir valores específicos ('qual valor desses dias destaque', 'valores dos dias destaque'), a intenção é 'ver_valores_destaque'
- Se pedir detalhes de boletos ('detalhes', 'ver mais', 'mais detalhes sobre esses boletos'), a intenção é 'ver_detalhes'
- Se quiser voltar ('voltar', 'menu'), a intenção é 'voltar'"""
        
        prompt = f"""Você é um assistente que classifica intenções em um chatbot de pagamento de boletos.

Contexto atual: {contexto or 'menu_principal'}
{contexto_info}

Mensagem do usuário: "{mensagem}"

Classifique a intenção em uma das seguintes categorias:
- saudacao: usuário está cumprimentando (oi, olá, bom dia, boa tarde, boa noite, hey, hi, hello, e aí, tudo bem, como vai)
- ver_pagamentos_hoje: usuário quer ver boletos que vencem hoje
- ver_pagamentos_data: usuário quer ver boletos de uma data específica
- ver_intervalo: usuário quer ver visão de um período/intervalo (detecte "próximos X dias/semanas/meses", "visualizar boletos dos próximos X dias")
- ver_atrasados: usuário quer ver boletos atrasados/vencidos
- pagar: usuário quer executar pagamento, confirmar, dizer sim após ver análise, seguir sugestão/recomendação ("gostaria de seguir sua sugestão", "aceito sua sugestão", "vamos com sua sugestão", "fazer sua sugestão", "aplicar sua sugestão", "implementar sua sugestão", "quero seguir", "vou seguir", "pode executar")
- ver_detalhes: usuário quer ver detalhes, mais informações, lista de boletos, "saber mais sobre boletos"
- ver_opcoes_financiamento: usuário quer ver outras opções de financiamento, comparar alternativas, "quanto ficaria nas outras opções", "mais detalhes dessa negociação", "opções de negociação", "me de opções de financiamento", "me dê opções de financiamento", "quero opções de financiamento"
- ver_valores_destaque: usuário quer ver valores específicos dos dias em destaque, "qual valor desses dias destaque", "valores dos dias destaque"
- voltar: usuário quer voltar ao menu ou cancelar
- ajuda: usuário pede ajuda ou não entende
- desconhecida: não consegue identificar

IMPORTANTE para ver_intervalo:
- Se mencionar "próximos X dias", calcule data_inicio=hoje e data_fim=hoje+X dias
- Se mencionar "próximas X semanas", calcule data_inicio=hoje e data_fim=hoje+X*7 dias
- Se mencionar "próximos X meses", calcule data_inicio=hoje e data_fim=hoje+X*30 dias
- Se mencionar "visualizar boletos dos próximos X dias", também é ver_intervalo
- Formato de datas: YYYY-MM-DD
- SEMPRE calcule automaticamente quando detectar "próximos/próximas X dias/semanas/meses"

Data de hoje: {datetime.now().strftime('%Y-%m-%d')}

Responda APENAS com um JSON no formato:
{{"intencao": "nome_da_intencao", "confianca": 0.9, "parametros": {{"data": "YYYY-MM-DD", "data_fim": "YYYY-MM-DD"}}}}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um classificador de intenções. Responda sempre com JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        resposta = response.choices[0].message.content.strip()
        
        # Parse do JSON
        import json
        try:
            # Remove markdown se houver
            if '```json' in resposta:
                resposta = resposta.split('```json')[1].split('```')[0]
            elif '```' in resposta:
                resposta = resposta.split('```')[1].split('```')[0]
            
            resultado = json.loads(resposta)
            return resultado
        except:
            # Fallback
            return {'intencao': 'desconhecida', 'confianca': 0.0, 'parametros': {}}


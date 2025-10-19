"""
Agente Conversacional com LLM para respostas naturais e fluidas
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False


class ConversationalAgent:
    """Agente que gera respostas conversacionais usando LLM - Impersona o Quitador"""
    
    def __init__(self, cnpj: str, saldo_inicial: float, nome_usuario: str = "Célia"):
        self.cnpj = cnpj
        self.saldo_inicial = saldo_inicial
        self.nome_usuario = nome_usuario
        self.historico_conversa = []
        self.use_llm = OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY')
        self.nome_agente = "Quitador"
    
    def gerar_boas_vindas(self, saldo_atual: float) -> str:
        """Gera mensagem de boas-vindas conversacional"""
        if not self.use_llm:
            return self._fallback_boas_vindas(saldo_atual)
        
        prompt = f"""Você é o QUITADOR, um assistente financeiro especializado do BTG para gestão de pagamentos de boletos.

Empresa: {self.cnpj}
Usuário: {self.nome_usuario}
Saldo disponível: R$ {saldo_atual:,.2f}

Gere uma mensagem de boas-vindas CURTA e NATURAL (máximo 3 linhas) onde você se apresenta como o Quitador e explica que pode ajudar com:
- Consultar boletos e pagamentos
- Ver análises financeiras
- Executar pagamentos

Seja amigável, direto e sempre mencione que você é o Quitador. Use o nome {self.nome_usuario} quando apropriado. NÃO use emojis em excesso. Termine perguntando como pode ajudar."""

        return self._chamar_llm(prompt, max_tokens=150)
    
    def gerar_resposta_visao_dia(self, dados: dict, saldo_atual: float, data_consultada: str = None) -> str:
        """Gera resposta conversacional sobre a visão do dia"""
        if not self.use_llm:
            return self._fallback_visao_dia(dados, saldo_atual)
        
        # Prepara dados para a LLM
        overview = dados.get('overview', {})
        boletos_dict = dados.get('boletos_dict', {})
        boletos_vencidos = dados.get('boletos_vencidos', [])
        analise_ia = dados.get('analise_ia', '')
        
        # Verifica se é hoje ou uma data futura/passada
        from datetime import datetime
        hoje = datetime.now().strftime('%Y-%m-%d')
        eh_hoje = (data_consultada is None or data_consultada == hoje)
        
        total_boletos = overview.get('total_boletos_no_dia', 0) + overview.get('total_boletos_vencidos', 0)
        total_valor = overview.get('valor_total_no_dia', 0) + overview.get('valor_total_vencidos', 0)
        tem_saldo = saldo_atual >= total_valor
        
        # Lista de boletos com beneficiários
        lista_boletos_texto = ""
        data_texto = "HOJE" if eh_hoje else f"em {data_consultada}"
        
        if boletos_dict:
            lista_boletos_texto = f"\nBOLETOS VENCENDO {data_texto}:\n"
            for codigo, dados_bol in list(boletos_dict.items())[:5]:
                beneficiario = dados_bol.get('beneficiario', 'Não informado')
                lista_boletos_texto += f"- {beneficiario}: R$ {dados_bol['valor']:,.2f}\n"
        
        if boletos_vencidos:
            lista_boletos_texto += f"\nBOLETOS VENCIDOS (até HOJE - {hoje}):\n"
            for bol in boletos_vencidos[:5]:
                beneficiario = bol.get('beneficiario', 'Não informado')
                lista_boletos_texto += f"- {beneficiario}: R$ {bol['valor']:,.2f} (venceu em {bol.get('data_vencimento', 'N/A')})\n"
        
        contexto_data = "hoje" if eh_hoje else f"para a data {data_consultada}"
        prompt = f"""Você é o QUITADOR, um assistente financeiro especializado do BTG. O usuário {self.nome_usuario} pediu para ver boletos {contexto_data}.

SITUAÇÃO ATUAL:
- Usuário: {self.nome_usuario}
- Data consultada: {data_consultada if not eh_hoje else "HOJE"}
- Boletos vencendo na data: {overview.get('total_boletos_no_dia', 0)} (R$ {overview.get('valor_total_no_dia', 0):,.2f})
- Boletos vencidos (até hoje {hoje}): {overview.get('total_boletos_vencidos', 0)} (R$ {overview.get('valor_total_vencidos', 0):,.2f})
- Total a pagar: R$ {total_valor:,.2f}
- Saldo disponível: R$ {saldo_atual:,.2f}

BOLETOS (com beneficiários):
{lista_boletos_texto}

ANÁLISE FINANCEIRA:
{analise_ia}

Gere uma resposta CONVERSACIONAL e NATURAL seguindo esta estrutura:

1. Se for HOJE ({eh_hoje}):
   - "Olá {self.nome_usuario}! Hoje você tem X boleto(s) vencendo..."
   
2. Se for OUTRA DATA:
   - "Olá {self.nome_usuario}! No dia {data_consultada} você terá X boleto(s) vencendo..."
   - "Além disso, até hoje você tem X boletos vencidos..."

3. SEMPRE mencione:
   - Valores monetários específicos
   - Principais beneficiários
   - Saldo disponível
   
4. Se saldo for INSUFICIENTE:
   - Mencione que o Quitador tem opções de financiamento disponíveis
   - Sugira ver "outras opções" ou "opções de financiamento"
   
5. Pergunte se deseja ver mais detalhes, análise de pagamento ou opções de financiamento

IMPORTANTE: 
- Seja NATURAL e CONVERSACIONAL (como se fosse uma conversa real)
- Use o nome {self.nome_usuario} quando apropriado
- Mencione que você é o Quitador quando apropriado
- Use linguagem amigável e direta
- NÃO use muitos emojis
- Seja específico com valores e beneficiários
- Termine perguntando como pode ajudar
- Boletos VENCIDOS são sempre até HOJE ({hoje}), não até a data consultada
- Se consulta data futura, deixe claro: "vencendo NAQUELE DIA" vs "vencidos ATÉ HOJE"

Seja DIRETO e CONVERSACIONAL. NÃO use muitos emojis."""

        return self._chamar_llm(prompt, max_tokens=400)
    
    def gerar_resposta_pagamento(self, valor_pago: float, saldo_anterior: float, 
                                 saldo_novo: float, qtd_boletos: int) -> str:
        """Gera resposta após pagamento"""
        if not self.use_llm:
            return self._fallback_pagamento(valor_pago, saldo_novo, qtd_boletos)
        
        prompt = f"""Você é o QUITADOR, um assistente financeiro especializado. O pagamento foi realizado com sucesso.

DETALHES:
- Valor pago: R$ {valor_pago:,.2f}
- Saldo anterior: R$ {saldo_anterior:,.2f}
- Saldo atual: R$ {saldo_novo:,.2f}
- Boletos pagos: {qtd_boletos}

Gere uma resposta CURTA (2-3 linhas) confirmando o pagamento de forma natural e amigável.
Mencione que você (Quitador) realizou o pagamento, o saldo novo e pergunte se precisa de mais alguma coisa.

Seja BREVE e NATURAL."""

        return self._chamar_llm(prompt, max_tokens=150)
    
    def gerar_resposta_saldo_insuficiente(self, valor_necessario: float, 
                                          saldo_atual: float, deficit: float) -> str:
        """Gera resposta quando saldo é insuficiente"""
        if not self.use_llm:
            return self._fallback_saldo_insuficiente(valor_necessario, saldo_atual, deficit)
        
        prompt = f"""Você é o QUITADOR, um assistente financeiro especializado. O usuário quer pagar mas não tem saldo suficiente.

SITUAÇÃO:
- Valor necessário: R$ {valor_necessario:,.2f}
- Saldo disponível: R$ {saldo_atual:,.2f}
- Falta: R$ {deficit:,.2f}

Gere uma resposta NATURAL (2-3 linhas) informando a situação e oferecendo ajuda.
Mencione que você (Quitador) tem opções de financiamento disponíveis de forma conversacional.

Seja EMPÁTICO e PRESTATIVO."""

        return self._chamar_llm(prompt, max_tokens=150)
    
    def gerar_resposta_boletos_atrasados(self, atrasados: list, total_valor: float) -> str:
        """Gera resposta sobre boletos atrasados"""
        if not self.use_llm:
            return self._fallback_atrasados(atrasados, total_valor)
        
        if not atrasados:
            prompt = "Gere uma mensagem CURTA (1 linha) comemorando que não há boletos atrasados. Seja alegre e breve."
        else:
            # Lista com beneficiários
            lista_atrasados = ""
            for b in atrasados[:5]:
                beneficiario = b.get('beneficiario', 'Não informado')
                lista_atrasados += f"- {beneficiario} ({b['id']}): R$ {b['valor']:,.2f} (venceu em {b['data_vencimento']})\n"
            
            prompt = f"""Você é o QUITADOR, um assistente financeiro especializado. O usuário pediu para ver boletos atrasados.

SITUAÇÃO:
- Quantidade de boletos atrasados: {len(atrasados)}
- Valor total em atraso: R$ {total_valor:,.2f}

Principais boletos atrasados (com beneficiários):
{lista_atrasados}

Gere uma resposta CONVERSACIONAL (2-3 linhas) alertando sobre a situação, mencionando alguns beneficiários principais, e perguntando se deseja ver detalhes ou pagar.

Seja PRESTATIVO mas não alarmista."""
        
        return self._chamar_llm(prompt, max_tokens=200)
    
    def gerar_resposta_intervalo(self, dashboard: dict, data_inicio: str, data_fim: str, saldo_atual: float) -> str:
        """Gera resposta conversacional sobre dashboard de período"""
        if not self.use_llm:
            return self._fallback_intervalo(dashboard, data_inicio, data_fim)
        
        dias_boletos = dashboard.get('dias_com_mais_boletos', {})
        dias_valor = dashboard.get('dias_com_maior_valor', {})
        atrasadas = dashboard.get('contas_atrasadas', {})
        
        prompt = f"""Você é o QUITADOR, um assistente financeiro especializado do BTG. O usuário pediu visão de boletos nos próximos dias.

PERÍODO: {data_inicio} até {data_fim}

DADOS DO PERÍODO:
- Dias com mais boletos: {list(dias_boletos.items())[:3]}
- Dias com maior valor: {list(dias_valor.items())[:3]}
- Contas atrasadas: {atrasadas.get('quantidade', 0)} boletos (R$ {atrasadas.get('valor_total', 0):,.2f})

SALDO DISPONÍVEL: R$ {saldo_atual:,.2f}

Gere uma resposta CONVERSACIONAL (3-4 linhas) que:
1. Resuma os principais pontos do período
2. Destaque os dias mais críticos (mais boletos ou maior valor)
3. Se houver contas atrasadas (quantidade > 0), mencione-as. Se não houver (quantidade = 0), deixe claro que NÃO HÁ boletos atrasados ou que "todos os boletos atrasados foram quitados"
4. Pergunte se deseja ver mais detalhes ou tomar alguma ação

IMPORTANTE: Se quantidade de atrasadas = 0, diga explicitamente que não há contas atrasadas ou que foram pagas.

Seja NATURAL e PRESTATIVO. NÃO crie listas ou menus numerados. Apenas converse."""
        
        return self._chamar_llm(prompt, max_tokens=300)
    
    def gerar_resposta_generica(self, contexto: str, dados: dict = None) -> str:
        """Gera resposta genérica baseada no contexto"""
        if not self.use_llm:
            return "Como posso ajudá-lo?"
        
        prompt = f"""Você é o QUITADOR, um assistente financeiro especializado do BTG. 

Contexto: {contexto}
Dados adicionais: {json.dumps(dados or {}, ensure_ascii=False)}

Gere uma resposta NATURAL e CONVERSACIONAL (1-2 linhas) adequada ao contexto.
Mencione que você é o Quitador quando apropriado. Seja DIRETO e AMIGÁVEL."""
        
        return self._chamar_llm(prompt, max_tokens=100)
    
    def _chamar_llm(self, prompt: str, max_tokens: int = 200) -> str:
        """Chama a LLM para gerar resposta"""
        try:
            # Adiciona ao histórico
            mensagens = [
                {"role": "system", "content": f"Você é o QUITADOR, um assistente financeiro especializado do BTG em pagamentos. Seja NATURAL, DIRETO e CONVERSACIONAL. Use uma linguagem humana e amigável. Sempre se apresente como o Quitador quando apropriado. O usuário se chama {self.nome_usuario} - use este nome quando apropriado."}
            ]
            
            # Adiciona histórico recente (últimas 5 interações)
            for msg in self.historico_conversa[-5:]:
                mensagens.append(msg)
            
            # Adiciona prompt atual
            mensagens.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=mensagens,
                temperature=0.7,  # Mais criativo
                max_tokens=max_tokens
            )
            
            resposta = response.choices[0].message.content.strip()
            
            # Atualiza histórico
            self.historico_conversa.append({"role": "user", "content": prompt})
            self.historico_conversa.append({"role": "assistant", "content": resposta})
            
            return resposta
            
        except Exception as e:
            return f"Desculpe, tive um problema ao processar sua solicitação. Como posso ajudar de outra forma?"
    
    # Fallbacks para quando não há LLM
    def _fallback_boas_vindas(self, saldo: float) -> str:
        return f"Olá {self.nome_usuario}! Sou o Quitador, seu assistente de pagamentos do BTG. Seu saldo é R$ {saldo:,.2f}. Como posso ajudar?"
    
    def _fallback_visao_dia(self, dados: dict, saldo: float) -> str:
        overview = dados.get('overview', {})
        return f"Você tem {overview.get('total_boletos_no_dia', 0)} boletos hoje e {overview.get('total_boletos_vencidos', 0)} vencidos. Deseja pagar?"
    
    def _fallback_pagamento(self, valor: float, saldo_novo: float, qtd: int) -> str:
        return f"Pagamento de R$ {valor:,.2f} realizado! Seu novo saldo é R$ {saldo_novo:,.2f}. Precisa de mais algo?"
    
    def _fallback_saldo_insuficiente(self, necessario: float, atual: float, deficit: float) -> str:
        return f"Seu saldo de R$ {atual:,.2f} é insuficiente para R$ {necessario:,.2f}. Faltam R$ {deficit:,.2f}. Posso sugerir opções de financiamento?"
    
    def _fallback_atrasados(self, atrasados: list, total: float) -> str:
        if not atrasados:
            return "Ótima notícia! Você não tem boletos atrasados."
        return f"Você tem {len(atrasados)} boletos atrasados totalizando R$ {total:,.2f}. Deseja ver detalhes?"
    
    def _fallback_intervalo(self, dashboard: dict, data_inicio: str, data_fim: str) -> str:
        dias_boletos = dashboard.get('dias_com_mais_boletos', {})
        return f"No período de {data_inicio} até {data_fim}, você tem boletos distribuídos. O que gostaria de fazer?"


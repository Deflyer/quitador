import json
import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Definições de custos de financiamento
TAXA_CAPITAL_GIRO = 0.08  # 8% total do valor financiado
TAXA_ADIANTAMENTO = 0.15 # 15% total do valor financiado

# 1. Novo Schema de Input
class FinancialPlanningInput(BaseModel):
    """Input para a ferramenta de Planejamento de Pagamentos."""
    saldo_atual: float = Field(..., description="O saldo de caixa atual disponível para pagamento (float).")
    boletos_file_path: str = Field(..., description="Caminho para o arquivo JSON contendo a lista de boletos.")

# 2. Tool Subclassing BaseTool
class FinancialAnalysisTool(BaseTool):
    name: str = "Bill Payment Optimization Planner"
    description: str = (
        "Reads a list of bills from a JSON file, calculates future costs (juros), "
        "and devises an optimal payment plan using the current balance and, "
        "if necessary, the cheapest financing option (Working Capital or Advances on Receivables)."
    )
    args_schema: Type[BaseModel] = FinancialPlanningInput

    # --- Funções Auxiliares de Financiamento ---
    
    def _calculate_financing_cost(self, amount: float) -> tuple[float, str, float]:
        """Calcula a melhor opção de financiamento (100% Giro ou 100% Adiantamento)."""
        custo_giro = amount * TAXA_CAPITAL_GIRO
        custo_adiantamento = amount * TAXA_ADIANTAMENTO
        
        if custo_giro <= custo_adiantamento:
            custo = custo_giro
            metodo = f"Capital de Giro ({TAXA_CAPITAL_GIRO*100:.0f}%)"
        else:
            custo = custo_adiantamento
            metodo = f"Adiantamento de Recebíveis ({TAXA_ADIANTAMENTO*100:.0f}%)"
            
        return custo, metodo, custo + amount # Custo, Método, Total

    # Seu código adaptado (Apenas o método _run com as correções)

    def _run(self, saldo_atual: float, boletos_file_path: str) -> str:
        
        try:
            with open(boletos_file_path, 'r', encoding='utf-8') as f:
                boletos = json.load(f)
        except FileNotFoundError:
            return f"ERRO: Arquivo JSON não encontrado no caminho: {boletos_file_path}"
        except json.JSONDecodeError:
            return "ERRO: O arquivo JSON está em um formato inválido."

        # 1. Calcular Custo de Atraso e Prioridade
        for boleto in boletos:
            # Custo se for deixado vencer: Taxa diária * Valor
            # Note: A lógica de prioridade está correta, mas a nomenclatura "estimado" pode ser ajustada,
            # pois você está usando apenas o juro diário, e não multiplicando por 'dias' aqui.
            boleto['custo_atraso_estimado'] = boleto['valor'] * boleto['juros_diario'] 
        
        # 2. Ordenar Boletos: Pelo Custo de Atraso Estimado (do MAIS CARO para o MAIS BARATO)
        boletos_ordenados = sorted(boletos, key=lambda x: x['custo_atraso_estimado'], reverse=True)

        # 3. Executar o Plano de Pagamento
        
        saldo_restante = saldo_atual
        boletos_pagar_saldo = []
        boletos_financiar = []
        
        # 3.1. Tentar pagar com saldo (melhor opção, custo 0)
        for boleto in boletos_ordenados:
            if saldo_restante >= boleto['valor']:
                saldo_restante -= boleto['valor']
                boletos_pagar_saldo.append(boleto)
            else:
                # O boleto não pode ser pago à vista.
                boletos_financiar.append(boleto) 
        
        # 3.2. Decisão de Financiamento
        
        # Inicializa variáveis para serem usadas no relatório FINAL,
        # garantindo que elas existam mesmo sem financiamento.
        plano_detalhado = "NENHUM DÉFICIT ENCONTRADO APÓS APLICAÇÃO DO SALDO."
        total_a_financiar = sum(b['valor'] for b in boletos_financiar)
        divida_final_financiar = 0.0
        custo_fin = 0.0
        metodo_fin = "Nenhum"
        saldo_final = saldo_restante # Inicializa o saldo final com o que sobrou após pagar à vista

        # Lógica principal de financiamento
        if total_a_financiar > 0:
            
            # O valor total dos boletos que não foram pagos com o saldo inicial
            
            # A dívida real a financiar é o total_a_financiar (boletos remanescentes) menos o saldo_restante (se houver)
            # Note: Se saldo_restante > 0, ele deve abater a dívida remanescente antes de financiar.
            
            divida_a_cobrir = total_a_financiar - saldo_restante 

            if divida_a_cobrir <= 0:
                # O saldo restante cobre o restante das dívidas. Não precisa financiar.
                plano_detalhado = f"O SALDO restante de R${saldo_restante:.2f} cobre os R${total_a_financiar:.2f} restantes. Não é necessário financiamento."
                
                # Move os boletos para a lista de pagamentos com saldo
                boletos_pagar_saldo.extend(boletos_financiar)
                boletos_financiar = [] # Limpa a lista de financiamento
                
                saldo_final = saldo_restante - total_a_financiar # Saldo final é o que sobra

            else: # Realmente precisa financiar a divida_a_cobrir
                divida_final_financiar = divida_a_cobrir
                
                # Simula a melhor opção de financiamento para o valor exato necessário
                custo_fin, metodo_fin, total_fin_pagar = self._calculate_financing_cost(divida_final_financiar)
                
                plano_detalhado = (
                    f"É NECESSÁRIO FINANCIAR R${divida_final_financiar:.2f}. O SALDO restante de R${saldo_restante:.2f} será aplicado, "
                    f"e a MELHOR OPÇÃO DE FINANCIAMENTO para o déficit é: {metodo_fin} com um custo de R${custo_fin:.2f}."
                )
                
                # Assume que todos os boletos remanescentes serão pagos via saldo + financiamento
                boletos_pagar_saldo.extend(boletos_financiar)
                boletos_financiar = [] # Limpa a lista de financiamento
                saldo_final = 0.0 # Saldo foi consumido para abater a dívida

        boletos_nao_pagos = [b for b in boletos_ordenados if b not in boletos_pagar_saldo]


        # 4. Construção do Relatório Final
        
        relatorio = []
        relatorio.append(f"--- ANÁLISE INICIAL ---")
        relatorio.append(f"SALDO DE CAIXA INICIAL: R${saldo_atual:.2f}")
        relatorio.append(f"TOTAL DE DÍVIDAS: R${sum(b['valor'] for b in boletos):.2f}")
        relatorio.append(f"CUSTO DE PRIORIDADE (Juros/Valor): R${sum(b['custo_atraso_estimado'] for b in boletos):.2f}")
        relatorio.append("\n--- PLANO DE PAGAMENTO ÓTIMO ---\n")

        relatorio.append(f"✅ PAGAR/COBRIR ({len(boletos_pagar_saldo)} boletos, R${sum(b['valor'] for b in boletos_pagar_saldo):.2f}):")
        for b in boletos_pagar_saldo:
            # A lista boletos_financiar deve estar vazia após o processamento, então essa lista agora 
            # contém todos os boletos pagos/cobertos pelo saldo ou financiamento.
            relatorio.append(f"  - CÓDIGO {b['codigo']}: R${b['valor']:.2f}")

        relatorio.append(f"\n💡 PLANO DE FINANCIAMENTO/DÉFICIT:")
        relatorio.append(plano_detalhado)

        # Reverte a lógica: Se boletos_nao_pagos não for a lista de 'deixados vencer', ela deve estar vazia
        # Se você quer a lista de boletos 'deixados vencer', você precisaria de uma lógica de 'break-even'
        # que não está implementada. Assumindo que tudo foi coberto:
        if len(boletos_nao_pagos) > 0:
            relatorio.append(f"\n⚠️ BOLETOS NÃO PAGOS/FINANCIADOS (R${sum(b['valor'] for b in boletos_nao_pagos):.2f}):")
            for b in boletos_nao_pagos:
                relatorio.append(f"  - CÓDIGO {b['codigo']}: R${b['valor']:.2f}")

        relatorio.append(f"\n--- RESUMO DE FLUXO DE CAIXA ---")
        relatorio.append(f"SALDO DE CAIXA FINAL ESTIMADO: R${saldo_final:.2f}")
        
        if divida_final_financiar > 0:
            relatorio.append(f"DÍVIDA DE FINANCIAMENTO A CONTRATAR: R${divida_final_financiar:.2f} ({metodo_fin})")

        return "\n".join(relatorio)

    # Certifique-se de substituir o método _run original pelo código acima no seu financial_tools.py.
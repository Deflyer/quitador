"""
Ferramenta de análise financeira simplificada (compatível com todas versões do CrewAI)
"""
import json

# Definições de custos de financiamento
TAXA_CAPITAL_GIRO = 0.08  # 8% total do valor financiado
TAXA_ADIANTAMENTO = 0.15  # 15% total do valor financiado

# Dados mock de recebíveis futuros (simulação para loja de roupas)
RECEBIVEIS_FUTUROS = [
    {"data": "2025-10-25", "valor": 2500.00, "origem": "Vendas à vista"},
    {"data": "2025-10-28", "valor": 1800.00, "origem": "Cartão de crédito"},
    {"data": "2025-11-02", "valor": 3200.00, "origem": "PIX"},
    {"data": "2025-11-05", "valor": 1500.00, "origem": "Boleto bancário"},
    {"data": "2025-11-08", "valor": 2800.00, "origem": "Vendas parceladas"}
]


def calcular_melhor_financiamento(valor: float) -> tuple:
    """Calcula a melhor opção de financiamento considerando recebíveis futuros"""
    custo_giro = valor * TAXA_CAPITAL_GIRO
    
    # Calcula recebíveis disponíveis para adiantamento
    recebiveis_disponiveis = sum(r["valor"] for r in RECEBIVEIS_FUTUROS)
    
    if valor <= recebiveis_disponiveis:
        custo_adiantamento = valor * TAXA_ADIANTAMENTO
    else:
        # Se precisar de mais que os recebíveis, combina estratégias
        custo_adiantamento = recebiveis_disponiveis * TAXA_ADIANTAMENTO
        valor_restante = valor - recebiveis_disponiveis
        custo_adiantamento += valor_restante * TAXA_CAPITAL_GIRO
    
    if custo_giro <= custo_adiantamento:
        return custo_giro, f"Capital de Giro ({TAXA_CAPITAL_GIRO*100:.0f}%)", custo_giro + valor
    else:
        return custo_adiantamento, f"Adiantamento de Recebíveis ({TAXA_ADIANTAMENTO*100:.0f}%)", custo_adiantamento + valor


def analisar_pagamento_boletos(saldo_atual: float, boletos_file_path: str) -> str:
    """
    Analisa boletos e retorna plano de pagamento otimizado
    
    Args:
        saldo_atual: Saldo disponível em caixa
        boletos_file_path: Caminho para arquivo JSON com boletos
    
    Returns:
        String com relatório detalhado
    """
    try:
        # Carrega boletos
        with open(boletos_file_path, 'r', encoding='utf-8') as f:
            boletos = json.load(f)
        
        # Calcula custo de atraso e prioriza
        for boleto in boletos:
            boleto['custo_atraso_estimado'] = boleto['valor'] * boleto['juros_diario']
        
        # Ordena por custo de atraso (maior para menor)
        boletos_ordenados = sorted(boletos, key=lambda x: x['custo_atraso_estimado'], reverse=True)
        
        # Separa boletos que podem ser pagos com saldo
        saldo_restante = saldo_atual
        boletos_pagar_saldo = []
        boletos_financiar = []
        
        for boleto in boletos_ordenados:
            if saldo_restante >= boleto['valor']:
                saldo_restante -= boleto['valor']
                boletos_pagar_saldo.append(boleto)
            else:
                boletos_financiar.append(boleto)
        
        # Calcula totais
        total_a_financiar = sum(b['valor'] for b in boletos_financiar)
        divida_a_cobrir = total_a_financiar - saldo_restante
        
        # Monta relatório
        relatorio = []
        relatorio.append("=" * 60)
        relatorio.append("📊 ANÁLISE FINANCEIRA - PLANO DE PAGAMENTO OTIMIZADO")
        relatorio.append("=" * 60)
        relatorio.append("")
        relatorio.append(f"💰 SALDO DE CAIXA INICIAL: R$ {saldo_atual:,.2f}")
        relatorio.append(f"📋 TOTAL DE BOLETOS: {len(boletos)}")
        relatorio.append(f"💵 VALOR TOTAL DAS DÍVIDAS: R$ {sum(b['valor'] for b in boletos):,.2f}")
        relatorio.append("")
        relatorio.append("-" * 60)
        
        # Verifica se precisa financiar
        if divida_a_cobrir <= 0:
            # Saldo suficiente
            relatorio.append("✅ SITUAÇÃO: SALDO SUFICIENTE")
            relatorio.append("")
            relatorio.append(f"Todos os {len(boletos)} boletos podem ser pagos com o saldo disponível.")
            relatorio.append(f"Saldo restante após pagamentos: R$ {saldo_restante - total_a_financiar:,.2f}")
            relatorio.append("")
            relatorio.append("🎯 RECOMENDAÇÃO:")
            relatorio.append("   • Pagar todos os boletos imediatamente")
            relatorio.append("   • Evitar acúmulo de juros")
            relatorio.append("   • Manter fluxo de caixa saudável")
            
        else:
            # Precisa financiar
            relatorio.append("⚠️ SITUAÇÃO: SALDO INSUFICIENTE")
            relatorio.append("")
            relatorio.append(f"💵 Valor que pode ser pago: R$ {saldo_atual:,.2f}")
            relatorio.append(f"📊 Déficit a cobrir: R$ {divida_a_cobrir:,.2f}")
            relatorio.append("")
            
            # Calcula melhor opção de financiamento
            custo_fin, metodo_fin, total_fin = calcular_melhor_financiamento(divida_a_cobrir)
            
            relatorio.append("-" * 60)
            relatorio.append("💡 SIMULAÇÃO DE FINANCIAMENTO")
            relatorio.append("-" * 60)
            
            # Mostra recebíveis futuros disponíveis
            relatorio.append("📈 RECEBÍVEIS FUTUROS DISPONÍVEIS:")
            total_recebiveis = 0
            for rec in RECEBIVEIS_FUTUROS:
                relatorio.append(f"   • {rec['data']}: R$ {rec['valor']:,.2f} ({rec['origem']})")
                total_recebiveis += rec['valor']
            relatorio.append(f"   💰 Total disponível: R$ {total_recebiveis:,.2f}")
            relatorio.append("")
            relatorio.append("")
            relatorio.append(f"🏦 MELHOR OPÇÃO: {metodo_fin}")
            relatorio.append(f"💰 Valor a financiar: R$ {divida_a_cobrir:,.2f}")
            relatorio.append(f"💸 Custo do financiamento: R$ {custo_fin:,.2f}")
            relatorio.append(f"📊 Total a pagar (principal + juros): R$ {total_fin:,.2f}")
            relatorio.append("")
            
            # Comparação com a outra opção
            if "Capital de Giro" in metodo_fin:
                custo_alt = divida_a_cobrir * TAXA_ADIANTAMENTO
                relatorio.append(f"📉 Economia vs Adiantamento de Recebíveis: R$ {abs(custo_alt - custo_fin):,.2f}")
            else:
                custo_alt = divida_a_cobrir * TAXA_CAPITAL_GIRO
                relatorio.append(f"📉 Economia vs Capital de Giro: R$ {abs(custo_alt - custo_fin):,.2f}")
            
            relatorio.append("")
            relatorio.append("-" * 60)
            relatorio.append("🎯 RECOMENDAÇÃO DE PAGAMENTO")
            relatorio.append("-" * 60)
            relatorio.append("")
            relatorio.append(f"1️⃣ Pagar {len(boletos_pagar_saldo)} boletos com saldo disponível")
            relatorio.append(f"   Valor: R$ {sum(b['valor'] for b in boletos_pagar_saldo):,.2f}")
            relatorio.append("")
            relatorio.append(f"2️⃣ Financiar {len(boletos_financiar)} boletos restantes via {metodo_fin}")
            relatorio.append(f"   Valor: R$ {sum(b['valor'] for b in boletos_financiar):,.2f}")
            relatorio.append("")
            
            # Lista boletos priorizados
            relatorio.append("📋 ORDEM DE PRIORIDADE (por custo de juros):")
            relatorio.append("")
            for i, boleto in enumerate(boletos_ordenados[:5], 1):
                status = "✅ Pagar com saldo" if boleto in boletos_pagar_saldo else "💳 Financiar"
                relatorio.append(f"   {i}. {boleto['codigo']} - R$ {boleto['valor']:,.2f} - {status}")
                relatorio.append(f"      Custo de atraso diário: R$ {boleto['custo_atraso_estimado']:.2f}")
            
            if len(boletos_ordenados) > 5:
                relatorio.append(f"   ... e mais {len(boletos_ordenados) - 5} boletos")
        
        relatorio.append("")
        relatorio.append("=" * 60)
        relatorio.append("💡 ESTRATÉGIA RECOMENDADA:")
        relatorio.append("")
        relatorio.append("✓ Priorizar boletos com maiores taxas de juros")
        relatorio.append("✓ Usar saldo disponível primeiro (custo zero)")
        relatorio.append("✓ Financiar o mínimo necessário")
        relatorio.append("✓ Escolher a opção de financiamento mais barata")
        relatorio.append("=" * 60)
        
        return "\n".join(relatorio)
        
    except Exception as e:
        return f"❌ ERRO na análise: {str(e)}"


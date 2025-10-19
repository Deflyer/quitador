"""
Integração com análise financeira simplificada (sem dependência do CrewAI complexo)
"""
import sys
import os

# Adiciona o diretório Sugestao-acao ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Sugestao-acao'))


def executar_analise_financeira(saldo_atual: float, boletos_file_path: str) -> str:
    """
    Executa a análise financeira
    
    Args:
        saldo_atual: Saldo de caixa disponível
        boletos_file_path: Caminho para o arquivo JSON com os boletos
    
    Returns:
        String com o relatório da análise
    """
    try:
        # Usa a versão simplificada da análise
        from financial_tools_simple import analisar_pagamento_boletos
        
        resultado = analisar_pagamento_boletos(saldo_atual, boletos_file_path)
        return resultado
        
    except Exception as e:
        return f"❌ Erro ao executar análise: {str(e)}\n\nVerifique se o arquivo de boletos existe e está no formato correto."


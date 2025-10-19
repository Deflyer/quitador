"""
Script de teste para verificar a integração entre DDA e CrewAI
"""
import sys
import os

# Adiciona diretórios ao path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DDA'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Sugestao-acao'))

from dda_crew_adapter import DDACrewAdapter
from datetime import datetime


def testar_dda():
    """Testa as funções do DDA"""
    print("=" * 60)
    print("TESTE 1: Testando DDA - Visão do Dia")
    print("=" * 60)
    
    try:
        cnpj = "12.345.678/0001-90"
        adapter = DDACrewAdapter(cnpj)
        
        # Testa visão do dia
        overview, boletos = adapter.obter_visao_dia("2025-10-19")
        
        print(f"\n✅ Visão do dia obtida com sucesso!")
        print(f"Total de boletos no dia: {overview['total_boletos_no_dia']}")
        print(f"Valor total do dia: R$ {overview['valor_total_no_dia']:,.2f}")
        print(f"Boletos vencidos: {overview['total_boletos_vencidos']}")
        print(f"Valor vencido: R$ {overview['valor_total_vencidos']:,.2f}")
        
        print(f"\nBoletos encontrados: {len(boletos)}")
        for codigo, dados in list(boletos.items())[:3]:
            print(f"  • {codigo}: R$ {dados['valor']:,.2f}")
        
        return True
    except Exception as e:
        print(f"\n❌ Erro ao testar DDA: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def testar_conversao_crewai():
    """Testa a conversão de dados para o formato CrewAI"""
    print("\n" + "=" * 60)
    print("TESTE 2: Testando Conversão para CrewAI")
    print("=" * 60)
    
    try:
        cnpj = "12.345.678/0001-90"
        adapter = DDACrewAdapter(cnpj)
        
        # Obtém dados e converte
        overview, boletos_crewai, temp_path = adapter.preparar_para_sugestao_acao("2025-10-19")
        
        print(f"\n✅ Conversão realizada com sucesso!")
        print(f"Arquivo temporário criado em: {temp_path}")
        print(f"Boletos convertidos: {len(boletos_crewai)}")
        
        for boleto in boletos_crewai[:3]:
            print(f"  • {boleto['codigo']}: R$ {boleto['valor']:,.2f} (juros diário: {boleto['juros_diario']*100:.2f}%)")
        
        # Limpa arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"\n🗑️ Arquivo temporário removido")
        
        return True
    except Exception as e:
        print(f"\n❌ Erro ao testar conversão: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def testar_dash_intervalo():
    """Testa o dashboard de intervalo"""
    print("\n" + "=" * 60)
    print("TESTE 3: Testando Dashboard de Intervalo")
    print("=" * 60)
    
    try:
        cnpj = "12.345.678/0001-90"
        adapter = DDACrewAdapter(cnpj)
        
        dashboard = adapter.obter_dash_intervalo("2025-10-10", "2025-10-30")
        
        print(f"\n✅ Dashboard obtido com sucesso!")
        
        print("\n📈 Dias com mais boletos:")
        for dia, count in dashboard['dias_com_mais_boletos'].items():
            print(f"  • {dia}: {count} boletos")
        
        print("\n💰 Dias com maior valor:")
        for dia, valor in dashboard['dias_com_maior_valor'].items():
            print(f"  • {dia}: R$ {valor:,.2f}")
        
        print(f"\n⚠️ Contas atrasadas:")
        print(f"  • Quantidade: {dashboard['contas_atrasadas']['quantidade']}")
        print(f"  • Valor total: R$ {dashboard['contas_atrasadas']['valor_total']:,.2f}")
        
        return True
    except Exception as e:
        print(f"\n❌ Erro ao testar dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def testar_boletos_atrasados():
    """Testa a listagem de boletos atrasados"""
    print("\n" + "=" * 60)
    print("TESTE 4: Testando Boletos Atrasados")
    print("=" * 60)
    
    try:
        cnpj = "12.345.678/0001-90"
        adapter = DDACrewAdapter(cnpj)
        
        atrasados = adapter.obter_boletos_atrasados("2025-10-19")
        
        print(f"\n✅ Boletos atrasados obtidos com sucesso!")
        print(f"Total de boletos atrasados: {len(atrasados)}")
        
        for boleto in atrasados[:5]:
            print(f"  • {boleto['id']}: R$ {boleto['valor']:,.2f} (vencimento: {boleto['data_vencimento']})")
        
        return True
    except Exception as e:
        print(f"\n❌ Erro ao testar boletos atrasados: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def testar_chatbot_manager():
    """Testa o gerenciador do chatbot"""
    print("\n" + "=" * 60)
    print("TESTE 5: Testando Chatbot Manager")
    print("=" * 60)
    
    try:
        from chatbot_manager import ChatbotManager
        
        cnpj = "12.345.678/0001-90"
        chatbot = ChatbotManager(cnpj, saldo_atual=50000.0)
        
        print("\n✅ Chatbot Manager criado com sucesso!")
        
        # Testa mensagem inicial
        resposta = chatbot.processar_mensagem("iniciar")
        print(f"\n📱 Resposta inicial:")
        print(resposta[:200] + "...")
        
        # Testa escolha de opção
        resposta = chatbot.processar_mensagem("1")
        print(f"\n📱 Resposta à opção 1:")
        print(resposta[:300] + "...")
        
        print(f"\n✅ Chatbot respondeu corretamente!")
        print(f"Estado atual: {chatbot.estado.value}")
        print(f"Mensagens no histórico: {len(chatbot.historico)}")
        
        return True
    except Exception as e:
        print(f"\n❌ Erro ao testar chatbot manager: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🧪 INICIANDO TESTES DE INTEGRAÇÃO")
    print("=" * 60)
    
    resultados = []
    
    # Executa testes
    resultados.append(("DDA - Visão do Dia", testar_dda()))
    resultados.append(("Conversão para CrewAI", testar_conversao_crewai()))
    resultados.append(("Dashboard de Intervalo", testar_dash_intervalo()))
    resultados.append(("Boletos Atrasados", testar_boletos_atrasados()))
    resultados.append(("Chatbot Manager", testar_chatbot_manager()))
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO DE TESTES")
    print("=" * 60)
    
    total = len(resultados)
    sucessos = sum(1 for _, resultado in resultados if resultado)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print(f"\n{'=' * 60}")
    print(f"Testes executados: {total}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {total - sucessos}")
    print(f"Taxa de sucesso: {(sucessos/total)*100:.1f}%")
    print("=" * 60)
    
    if sucessos == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os erros acima.")
    
    return sucessos == total


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)


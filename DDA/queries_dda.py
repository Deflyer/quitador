import json
import pandas as pd
import os

def boletos_do_dia(df, cnpj, dia):
    dia = pd.to_datetime(dia)
    hoje = pd.Timestamp.now().normalize()  # Data atual (hoje)
    df_cnpj = df[df['cnpj'] == cnpj]
    
    boletos_hoje = df_cnpj[df_cnpj['data_vencimento'] == dia].copy()
    # Vencidos são sempre relativos à data ATUAL, não à data consultada
    vencidos = df_cnpj[df_cnpj['data_vencimento'] < hoje].copy()
    
    # Criar coluna formatada apenas para saída
    boletos_hoje['data_str'] = boletos_hoje['data_vencimento'].dt.strftime('%Y-%m-%d')
    vencidos['data_str'] = vencidos['data_vencimento'].dt.strftime('%Y-%m-%d')
    
    # Overview
    overview = {
        "total_boletos_no_dia": len(boletos_hoje),
        "total_boletos_vencidos": len(vencidos),
        "valor_total_no_dia": boletos_hoje['valor'].sum(),
        "valor_total_vencidos": vencidos['valor'].sum()
    }
    
    # Criar dicionário de boletos detalhado
    boletos_dict = {}
    for idx, row in boletos_hoje.iterrows():
        codigo = f"Boleto_{idx}"  # pode usar id real
        juros_acumulado = 0  # ou calcular depois
        boletos_dict[codigo] = {
            "empresa": row['cnpj'],
            "beneficiario": row.get('beneficiario', 'Não informado'),
            "valor": row['valor'],
            "juros": juros_acumulado,
            "data_vencimento": row['data_str']  # aqui usamos a string
        }
    
    return overview, boletos_dict


def detalhe_boleto(df, cnpj, id_boleto, campos=None):
    """
    Retorna os detalhes de um boleto específico pelo ID e CNPJ.
    
    Parâmetros:
    - df: DataFrame de boletos
    - cnpj: CNPJ da empresa
    - id_boleto: ID do boleto
    - campos: lista de strings com os campos desejados (ex: ['valor','data_vencimento','status'])
    
    Retorna:
    - dicionário com os campos solicitados, ou None se não encontrado
    """
    boleto = df[(df['cnpj'] == cnpj) & (df['id'] == id_boleto)].copy()
    
    if boleto.empty:
        return None
    
    # Formatar data para string
    boleto['data_vencimento_str'] = boleto['data_vencimento'].dt.strftime('%Y-%m-%d')
    
    # Converter para dicionário
    result = boleto.to_dict(orient='records')[0]
    
    # Substituir coluna datetime pela string formatada
    result['data_vencimento'] = result.pop('data_vencimento_str')
    
    # Filtrar apenas os campos desejados
    if campos is not None:
        result = {k: v for k, v in result.items() if k in campos}
    
    return result


def dash_intervalo(df, cnpj, data_inicio, data_fim):
    inicio = pd.to_datetime(data_inicio)
    fim = pd.to_datetime(data_fim)
    
    df_cnpj = df[df['cnpj'] == cnpj]
    df_periodo = df_cnpj[(df_cnpj['data_vencimento'] >= inicio) & 
                         (df_cnpj['data_vencimento'] <= fim)].copy()
    
    # Formatar datas
    df_periodo.loc[:, 'data_vencimento_str'] = df_periodo['data_vencimento'].dt.strftime('%Y-%m-%d')
    
    # Count de boletos por dia
    count_por_dia = df_periodo.groupby('data_vencimento_str').size().sort_values(ascending=False).head(3)
    
    # Dias com maior valor total
    valor_por_dia = df_periodo.groupby('data_vencimento_str')['valor'].sum().sort_values(ascending=False).head(3)
    
    # Contas atrasadas - sempre usa data ATUAL, não a data do intervalo
    hoje = pd.Timestamp.now().normalize()
    atrasadas = df_cnpj[df_cnpj['data_vencimento'] < hoje].copy()
    atrasadas.loc[:, 'data_vencimento_str'] = atrasadas['data_vencimento'].dt.strftime('%Y-%m-%d')
    
    # Visão de urgente: 3 primeiros dias do período
    primeiros_dias = df_periodo.sort_values('data_vencimento').head(3)
    urgent_overview = {}
    for dia, grupo in primeiros_dias.groupby('data_vencimento_str'):
        urgent_overview[dia] = grupo[['id','valor','status']].to_dict(orient='records')
    
    dashboard = {
        "dias_com_mais_boletos": count_por_dia.to_dict(),
        "dias_com_maior_valor": valor_por_dia.to_dict(),
        "contas_atrasadas": {
            "quantidade": len(atrasadas),
            "valor_total": atrasadas['valor'].sum()
        },
        "visao_urgente": urgent_overview
    }
    
    return dashboard


def boletos_atrasados(df, cnpj, referencia=None):
    # Se referencia não for fornecida, usa a data atual
    if referencia is None:
        hoje = pd.Timestamp.now().normalize()
    else:
        hoje = pd.to_datetime(referencia)
    
    df_cnpj = df[df['cnpj'] == cnpj]
    atrasados = df_cnpj[df_cnpj['data_vencimento'] < hoje].copy()  # copy aqui
    
    atrasados['data_vencimento'] = atrasados['data_vencimento'].dt.strftime('%Y-%m-%d')
    return atrasados.to_dict(orient='records')

def sistema_boletos(acao, **kwargs):
    """
    Função switch-case para gerenciar diferentes funções de boletos.
    
    Parâmetros:
    - df: DataFrame de boletos
    - acao: string indicando a ação a executar
    - kwargs: parâmetros adicionais necessários para cada ação
    
    Ações possíveis:
    - "overview_dia" -> chama boletos_do_dia(df, cnpj, dia)
    - "detalhe_boleto" -> chama detalhe_boleto(df, cnpj, valor, data_vencimento)
    - "dash_intervalo" -> chama dash_intervalo(df, cnpj, data_inicio, data_fim)
    - "atrasados" -> chama boletos_atrasados(df, cnpj, referencia)
    """
    
    # Permite especificar um caminho customizado para o JSON
    json_path = kwargs.get('dda_json_path', 'dda.json')
    
    # Se o caminho não for absoluto, tenta encontrar relativo ao diretório atual
    if not os.path.isabs(json_path) and not os.path.exists(json_path):
        # Tenta encontrar relativo ao diretório deste arquivo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'dda.json')
    
    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    # 2. Extrair a lista de boletos (array dentro de "data")
    boletos = json_data["data"]

    # 3. Criar DataFrame
    df = pd.json_normalize(boletos)
    df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])
    
    match acao:
        case "overview_dia":
            return boletos_do_dia(df, kwargs['cnpj'], kwargs['dia'])
        
        case "detalhe_boleto":
            return detalhe_boleto(df, kwargs['cnpj'], kwargs['id_boleto'], kwargs.get('campos'))

        case "dash_intervalo":
            return dash_intervalo(df, kwargs['cnpj'], kwargs['data_inicio'], kwargs['data_fim'])
        
        case "atrasados":
            referencia = kwargs.get('referencia')  # None se não fornecido, usa data atual
            return boletos_atrasados(df, kwargs['cnpj'], referencia)
        
        case _:
            raise ValueError(f"Ação '{acao}' não reconhecida.")



#COMO QUE USA
# # 1. Overview do dia
# overview, lista = sistema_boletos("overview_dia", cnpj="12.345.678/0001-90", dia="2025-10-19")

# print("Overview do dia:")
# print(overview)
# print(lista)
# print()

# # 2. Detalhe de um boleto
# detalhe = sistema_boletos("detalhe_boleto", cnpj="12.345.678/0001-90", id_boleto="BOL002", campos=['valor','data_vencimento','status'])
# print("Detalhe do boleto:")
# print(detalhe)
# print()

# # 3. Dash do intervalo
# dash = sistema_boletos("dash_intervalo", cnpj="12.345.678/0001-90", data_inicio="2025-10-10", data_fim="2025-10-25")
# print("Dash do intervalo:")
# print(dash)
# print()

# # 4. Boletos atrasados
# atrasados = sistema_boletos("atrasados", cnpj="12.345.678/0001-90")
# print("Boletos atrasados:")
# print(atrasados)
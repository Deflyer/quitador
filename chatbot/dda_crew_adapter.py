"""
Adaptador para integrar a saída do DDA com a entrada do CrewAI
"""
import json
import sys
import os
from datetime import datetime, timedelta

# Adiciona os diretórios ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DDA'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Sugestao-acao'))

from queries_dda import sistema_boletos


class DDACrewAdapter:
    """Adapta a saída do DDA para o formato esperado pelo CrewAI"""
    
    def __init__(self, cnpj: str, dda_json_path: str = None):
        self.cnpj = cnpj
        if dda_json_path:
            # Atualiza o caminho no queries_dda se necessário
            pass
    
    def calcular_juros_acumulado(self, valor: float, multa_percentual: float, dias_atraso: int) -> float:
        """Calcula juros acumulados de um boleto vencido"""
        if dias_atraso <= 0:
            return 0.0
        juros = valor * multa_percentual * dias_atraso
        return juros
    
    def converter_boletos_para_crewai(self, boletos_dict: dict, data_referencia: str = None) -> list:
        """
        Converte o dicionário de boletos do DDA para o formato do CrewAI
        
        DDA Output: {
            "Boleto_X": {
                "empresa": "CNPJ",
                "valor": float,
                "juros": float,
                "data_vencimento": "YYYY-MM-DD"
            }
        }
        
        CrewAI Input: [
            {
                "codigo": "B001",
                "valor": float,
                "juros_diario": float
            }
        ]
        """
        if data_referencia is None:
            data_referencia = datetime.now().strftime('%Y-%m-%d')
        
        boletos_crewai = []
        
        for codigo, dados in boletos_dict.items():
            # Calcula dias de atraso se houver
            data_venc = datetime.strptime(dados['data_vencimento'], '%Y-%m-%d')
            data_ref = datetime.strptime(data_referencia, '%Y-%m-%d')
            dias_atraso = (data_ref - data_venc).days
            
            # Estima juros diário baseado no valor (pode ser ajustado)
            juros_diario = 0.002  # 0.2% ao dia como padrão
            if dados.get('juros', 0) > 0:
                # Se já tem juros calculado, usa como base
                juros_diario = dados['juros'] / dados['valor'] if dados['valor'] > 0 else 0.002
            
            boleto_crew = {
                "codigo": codigo,
                "valor": dados['valor'],
                "juros_diario": juros_diario
            }
            boletos_crewai.append(boleto_crew)
        
        return boletos_crewai
    
    def salvar_boletos_temporarios(self, boletos_crewai: list, output_path: str = None) -> str:
        """Salva os boletos no formato CrewAI em um arquivo temporário"""
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), 'temp_boletos.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(boletos_crewai, f, indent=4, ensure_ascii=False)
        
        return output_path
    
    def obter_visao_dia(self, dia: str = None):
        """
        Obtém a visão de pagamento do dia
        Retorna: (overview, boletos_dict)
        """
        if dia is None:
            dia = datetime.now().strftime('%Y-%m-%d')
        
        overview, boletos_dict = sistema_boletos(
            "overview_dia",
            cnpj=self.cnpj,
            dia=dia
        )
        
        return overview, boletos_dict
    
    def obter_detalhe_boleto(self, id_boleto: str, campos: list = None):
        """Obtém detalhes de um boleto específico"""
        return sistema_boletos(
            "detalhe_boleto",
            cnpj=self.cnpj,
            id_boleto=id_boleto,
            campos=campos
        )
    
    def obter_dash_intervalo(self, data_inicio: str, data_fim: str):
        """Obtém dashboard de intervalo de tempo"""
        return sistema_boletos(
            "dash_intervalo",
            cnpj=self.cnpj,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
    
    def obter_boletos_atrasados(self, referencia: str = None):
        """Obtém lista de boletos atrasados"""
        if referencia is None:
            referencia = datetime.now().strftime('%Y-%m-%d')
        
        return sistema_boletos(
            "atrasados",
            cnpj=self.cnpj,
            referencia=referencia
        )
    
    def preparar_para_sugestao_acao(self, dia: str = None, boletos_pagos: list = None) -> tuple:
        """
        Prepara dados do DDA para enviar ao CrewAI
        Inclui TODOS os boletos que precisam ser pagos (do dia + vencidos)
        Filtra boletos já pagos
        Retorna: (overview, boletos_crewai_list, temp_file_path)
        """
        if dia is None:
            dia = datetime.now().strftime('%Y-%m-%d')
        
        if boletos_pagos is None:
            boletos_pagos = []
        
        # Obtém overview do dia (que já inclui info de vencidos)
        overview, boletos_dict_dia = self.obter_visao_dia(dia)
        
        # Filtra boletos do dia já pagos
        boletos_dict_dia = {k: v for k, v in boletos_dict_dia.items() if k not in boletos_pagos}
        
        # Obtém TODOS os boletos vencidos também (sempre usa data ATUAL)
        boletos_vencidos = self.obter_boletos_atrasados()
        boletos_vencidos = [b for b in boletos_vencidos if b['id'] not in boletos_pagos]
        
        # Combina boletos do dia + vencidos
        todos_boletos = {}
        
        # Adiciona boletos do dia
        todos_boletos.update(boletos_dict_dia)
        
        # Adiciona boletos vencidos (se não estiverem duplicados)
        for boleto_vencido in boletos_vencidos:
            codigo = f"Boleto_{boleto_vencido['id']}"
            if codigo not in todos_boletos:
                # Calcula juros acumulados para boletos vencidos (sempre usa data ATUAL)
                data_venc = datetime.strptime(boleto_vencido['data_vencimento'], '%Y-%m-%d')
                data_atual = datetime.now()  # Usa data atual, não a consultada
                dias_atraso = (data_atual - data_venc).days
                
                juros = boleto_vencido['valor'] * boleto_vencido.get('multa', 0.02) * dias_atraso
                
                todos_boletos[codigo] = {
                    'empresa': boleto_vencido['cnpj'],
                    'beneficiario': boleto_vencido.get('beneficiario', 'Não informado'),
                    'valor': boleto_vencido['valor'],
                    'juros': juros,
                    'data_vencimento': boleto_vencido['data_vencimento']
                }
        
        # Converte TODOS os boletos para formato CrewAI
        boletos_crewai = self.converter_boletos_para_crewai(todos_boletos, dia)
        temp_path = self.salvar_boletos_temporarios(boletos_crewai)
        
        return overview, boletos_crewai, temp_path


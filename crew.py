import sys
# Importa pysqlite3 e o coloca no lugar do sqlite3 padrão
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
from dotenv import load_dotenv
import yaml
from crewai import Agent, Task, Crew, Process

# Garante que as variáveis de ambiente (como a API Key) estão carregadas
load_dotenv()

# =================================================================
# 1. FUNÇÃO PARA CARREGAR CONFIGURAÇÕES YAML
# =================================================================
def load_yaml_config(file_path):
    """Carrega o conteúdo de um arquivo YAML."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Carrega a classe da sua Custom Tool
from financial_tools import FinancialAnalysisTool

# Instancia a Tool
financial_tool = FinancialAnalysisTool()

# =================================================================
# 2. CARREGAR E CONSTRUIR AGENTES E TAREFAS
# =================================================================

# Carrega as configurações dos arquivos YAML
agents_config = load_yaml_config('agents.yaml')
tasks_config = load_yaml_config('tasks.yaml')

# Acessa a configuração do agente (o nome do bloco no agents.yaml)
analyst_data = agents_config['financial_analyst']

# 2.1. CONSTRUIR O AGENTE MANUALMENTE (INJETANDO A TOOL)
financial_analyst = Agent(
    # Traduz as chaves do YAML para os parâmetros do Agent
    role=analyst_data['role'],
    goal=analyst_data['goal'],
    backstory=analyst_data['backstory'],
    verbose=analyst_data.get('verbose', True), # Usa valor do YAML ou True como padrão
    allow_delegation=analyst_data.get('allow_delegation', False), 
    
    # INJETA SUA TOOL CUSTOMIZADA AQUI:
    tools=[financial_tool] 
)

# Acessa a configuração da tarefa (o nome do bloco no tasks.yaml)
task_data = tasks_config['debt_analysis_task']

# 2.2. CONSTRUIR A TAREFA MANUALMENTE (CONECTANDO AO AGENTE)
debt_analysis_task = Task(
    # Traduz as chaves do YAML para os parâmetros da Task
    description=task_data['description'],
    expected_output=task_data['expected_output'],
    
    # CONECTA A TAREFA AO AGENTE CONSTRUÍDO ACIMA:
    agent=financial_analyst
)

# =================================================================
# 3. CRIAR E INICIAR O CREW
# =================================================================

crew = Crew(
    agents=[financial_analyst], # Lista dos agentes construídos
    tasks=[debt_analysis_task], # Lista das tarefas construídas
    
    process=Process.sequential,
    verbose=True,
)

print("\nIniciando a análise financeira com configurações YAML carregadas manualmente...")
result = crew.kickoff()

print("\n\n########################")
print("RELATÓRIO FINANCEIRO FINAL:")
print(result)
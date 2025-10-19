# 🏦 Chatbot de Pagamento de Boletos BTG

Sistema inteligente de gestão e pagamento de boletos com suporte a IA para sugestões de ação.

## 📋 Descrição

Este chatbot oferece uma interface conversacional para gerenciar pagamentos de boletos, integrando:

- **DDA (Débito Direto Autorizado)**: Visualização de boletos por data, detalhes e status
- **Análise Financeira com IA**: Sugestões inteligentes de priorização e financiamento usando CrewAI
- **Interface Web Moderna**: Chat em tempo real com design responsivo

## 🚀 Funcionalidades

### 1️⃣ Visão de Pagamento do Dia
- Visualiza boletos vencendo hoje
- Mostra boletos vencidos
- Calcula valores totais
- Lista detalhada com empresa, valor e juros

### 2️⃣ Consulta por Data Específica
- Escolha qualquer data para visualizar boletos
- Mesmo formato da visão do dia

### 3️⃣ Visão de Período (Intervalo)
- Dashboard com dias que têm mais boletos
- Dias com maiores valores
- Visão de urgência (primeiros dias)
- Resumo de contas atrasadas

### 4️⃣ Detalhes de Boletos
- Informações completas de cada boleto
- Código, valor, juros, data de vencimento
- Empresa emissora

### 5️⃣ Sugestão de Ação com IA
- Análise inteligente usando CrewAI
- Verifica se saldo é suficiente
- Sugere opções de financiamento:
  - Capital de Giro
  - Adiantamento de Recebíveis
- Prioriza pagamentos por juros
- Minimiza custos totais

### 6️⃣ Boletos Atrasados
- Lista completa de boletos vencidos
- Valor total em atraso
- Status de cada boleto

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript
- **IA**: CrewAI, OpenAI GPT
- **Dados**: Pandas, JSON
- **Gerenciamento de Estado**: Sessions

## 📦 Instalação

### Pré-requisitos

- Python 3.9+
- Pip
- API Key da OpenAI

### Passos

1. **Clone ou navegue até o diretório do chatbot**:
```bash
cd "/home/blomes/projects/Pagamento - BTG/chatbot"
```

2. **Crie um ambiente virtual** (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. **Instale as dependências**:
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**:
```bash
cp .env.example .env
```

Edite o arquivo `.env` e adicione sua API Key da OpenAI:
```
OPENAI_API_KEY=sua_chave_aqui
```

5. **Execute a aplicação**:
```bash
python app.py
```

6. **Acesse no navegador**:
```
http://localhost:5000
```

## 📁 Estrutura do Projeto

```
chatbot/
├── app.py                      # Aplicação Flask principal
├── chatbot_manager.py          # Gerenciador de estado e lógica do chatbot
├── dda_crew_adapter.py         # Adaptador entre DDA e CrewAI
├── crew_integration.py         # Integração com CrewAI
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de configuração
├── README.md                  # Este arquivo
└── templates/
    └── index.html             # Interface do chat

Integra com:
../DDA/
├── queries_dda.py            # Funções de consulta do DDA
└── dda.json                  # Base de dados de boletos

../Sugestao-acao/
├── crew.py                   # Configuração do CrewAI
├── financial_tools.py        # Ferramentas de análise financeira
├── agents.yaml              # Configuração dos agentes
└── tasks.yaml               # Configuração das tarefas
```

## 🎯 Fluxo de Uso

1. **Iniciar conversa**: O bot apresenta o menu principal
2. **Escolher opção**: Selecione entre as 4 opções principais
3. **Visualizar dados**: Veja informações detalhadas dos boletos
4. **Opções adicionais**:
   - Pagar boletos (se houver saldo)
   - Ver detalhes específicos
   - Obter sugestão da IA
5. **Sugestão de IA** (quando saldo insuficiente):
   - IA analisa situação
   - Sugere melhor estratégia de financiamento
   - Prioriza pagamentos por custo de juros

## 💡 Exemplos de Uso

### Consultar Pagamentos de Hoje
```
Usuário: 1
Bot: [Mostra visão do dia com boletos e valores]
```

### Ver Boletos Atrasados
```
Usuário: 4
Bot: [Lista todos os boletos vencidos com valores]
```

### Consultar Período
```
Usuário: 3
Bot: Digite o intervalo...
Usuário: 2025-10-19 até 2025-10-30
Bot: [Mostra dashboard do período]
```

### Obter Sugestão da IA
```
Usuário: 1 (visão do dia)
Bot: [Mostra opções]
Usuário: 3 (sugestão IA)
Bot: [IA analisa e sugere estratégia otimizada]
```

## 🔧 Configurações

### Alterar CNPJ Padrão
Edite o arquivo `app.py`, linha onde `cnpj_padrao` é definido, ou configure no `.env`.

### Alterar Saldo Inicial
Edite o arquivo `app.py`, linha onde `saldo_padrao` é definido, ou configure no `.env`.

### Adicionar Mais Boletos
Edite o arquivo `../DDA/dda.json` seguindo o formato existente.

## 🤖 Sobre a IA

O chatbot utiliza o **CrewAI** com agentes especializados em análise financeira. O agente:

- Analisa o fluxo de caixa disponível
- Calcula custos de juros de cada boleto
- Simula opções de financiamento
- Recomenda a estratégia de menor custo
- Prioriza pagamentos por impacto financeiro

## 🐛 Troubleshooting

### Erro: "OpenAI API Key não configurada"
Configure a variável `OPENAI_API_KEY` no arquivo `.env`.

### Erro ao importar pysqlite3
```bash
pip install pysqlite3-binary
```

### Port 5000 já em uso
Altere a porta no `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

## 📝 Notas

- O sistema simula pagamentos (não efetua transações reais)
- Em produção, integrar com APIs bancárias reais
- Histórico de sessão é mantido em memória (usar Redis em produção)
- DDA não atualiza automaticamente após "pagamento" (feature futura)

## 🔐 Segurança

- Nunca commite o arquivo `.env` com chaves reais
- Use HTTPS em produção
- Implemente autenticação para usuários reais
- Valide e sanitize todas as entradas do usuário

## 📄 Licença

Este é um projeto de demonstração e estudo.

## 👥 Contribuidores

Desenvolvido pela equipe BTG para demonstração de integração DDA + IA.

---

**Desenvolvido com ❤️ usando Flask, CrewAI e OpenAI**


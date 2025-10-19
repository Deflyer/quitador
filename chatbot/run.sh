#!/bin/bash

# Script de inicialização do Chatbot de Pagamentos BTG

echo "🏦 Chatbot de Pagamentos BTG - Inicialização"
echo "=============================================="
echo ""

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale o Python 3.9+"
    exit 1
fi

# Verifica se está em um ambiente virtual
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️ Ambiente virtual não detectado."
    echo "Recomenda-se criar um ambiente virtual:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Deseja continuar sem ambiente virtual? (s/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Verifica se as dependências estão instaladas
echo "📦 Verificando dependências..."
if ! python3 -c "import flask" &> /dev/null; then
    echo "⚠️ Dependências não instaladas."
    echo "Instalando dependências do requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Erro ao instalar dependências"
        exit 1
    fi
fi

# Verifica se o arquivo .env existe
if [ ! -f .env ]; then
    echo "⚠️ Arquivo .env não encontrado."
    if [ -f env.example ]; then
        echo "📄 Copiando env.example para .env..."
        cp env.example .env
        echo "✅ Arquivo .env criado. Por favor, configure sua OPENAI_API_KEY!"
        echo ""
        echo "Edite o arquivo .env e adicione sua chave da OpenAI:"
        echo "  OPENAI_API_KEY=sua_chave_aqui"
        echo ""
        read -p "Pressione Enter quando estiver pronto para continuar..."
    fi
fi

# Verifica se a OPENAI_API_KEY está configurada
if [ -f .env ]; then
    source .env
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sua_api_key_aqui" ]; then
        echo "⚠️ OPENAI_API_KEY não configurada no arquivo .env"
        echo "As funcionalidades de IA não funcionarão sem esta chave."
        echo ""
        read -p "Deseja continuar mesmo assim? (s/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    fi
fi

# Executa testes (opcional)
read -p "🧪 Deseja executar os testes antes de iniciar? (s/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Executando testes..."
    python3 test_integration.py
    if [ $? -ne 0 ]; then
        echo "⚠️ Alguns testes falharam. Deseja continuar?"
        read -p "Continuar? (s/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    fi
fi

# Inicia o servidor
echo ""
echo "🚀 Iniciando servidor Flask..."
echo "📍 Acesse: http://localhost:5000"
echo ""
echo "Pressione Ctrl+C para parar o servidor"
echo ""

python3 app.py


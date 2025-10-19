#!/bin/bash

# 🚀 Script de Setup Automático - Quitador
# Equipe RAIA - Hackathon BTG

echo "🤖 Iniciando setup do Quitador..."
echo "=================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para print colorido
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se Python está instalado
print_status "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 não encontrado. Por favor, instale Python 3.12+ primeiro."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python $PYTHON_VERSION encontrado"

# Verificar se pip está instalado
print_status "Verificando pip..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 não encontrado. Por favor, instale pip primeiro."
    exit 1
fi
print_success "pip3 encontrado"

# Criar ambiente virtual
print_status "Criando ambiente virtual..."
if [ -d "venv" ]; then
    print_warning "Ambiente virtual já existe. Removendo..."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -eq 0 ]; then
    print_success "Ambiente virtual criado"
else
    print_error "Falha ao criar ambiente virtual"
    exit 1
fi

# Ativar ambiente virtual
print_status "Ativando ambiente virtual..."
source venv/bin/activate
if [ $? -eq 0 ]; then
    print_success "Ambiente virtual ativado"
else
    print_error "Falha ao ativar ambiente virtual"
    exit 1
fi

# Atualizar pip
print_status "Atualizando pip..."
pip install --upgrade pip
print_success "pip atualizado"

# Instalar dependências
print_status "Instalando dependências..."
cd chatbot/
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    print_success "Dependências instaladas"
else
    print_error "Falha ao instalar dependências"
    exit 1
fi

# Verificar arquivo .env
print_status "Verificando configurações..."
if [ ! -f ".env" ]; then
    print_warning "Arquivo .env não encontrado. Criando a partir do exemplo..."
    cp env.example .env
    print_warning "IMPORTANTE: Configure sua OPENAI_API_KEY no arquivo .env"
    print_warning "Edite o arquivo .env e adicione sua chave da OpenAI"
    echo ""
    echo "Exemplo:"
    echo "OPENAI_API_KEY=sk-sua-chave-aqui"
    echo ""
    read -p "Pressione Enter quando tiver configurado a API key..."
else
    print_success "Arquivo .env encontrado"
fi

# Verificar se a API key está configurada
if grep -q "OPENAI_API_KEY=sua_chave_openai_aqui" .env; then
    print_warning "API key não configurada. Configure no arquivo .env antes de executar."
fi

# Voltar para o diretório raiz
cd ..

# Criar diretórios necessários
print_status "Criando diretórios necessários..."
mkdir -p chatbot/static/photos
mkdir -p chatbot/templates
print_success "Diretórios criados"

# Verificar se a foto do Quitador existe
if [ ! -f "chatbot/static/photos/profile.jpeg" ]; then
    print_warning "Foto do Quitador não encontrada. Criando placeholder..."
    # Criar um placeholder simples (você pode substituir por uma imagem real)
    echo "Foto do Quitador não encontrada" > chatbot/static/photos/profile.jpeg
fi

# Teste de importação
print_status "Testando importações..."
python3 -c "
try:
    import flask
    import pandas
    import openai
    print('✅ Todas as dependências principais importadas com sucesso')
except ImportError as e:
    print(f'❌ Erro na importação: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Teste de importação passou"
else
    print_error "Falha no teste de importação"
    exit 1
fi

# Instruções finais
echo ""
echo "🎉 Setup concluído com sucesso!"
echo "================================"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure sua OPENAI_API_KEY no arquivo chatbot/.env"
echo "2. Execute: cd chatbot && python app.py"
echo "3. Acesse: http://localhost:5000"
echo ""
echo "🔧 Comandos úteis:"
echo "- Ativar ambiente virtual: source venv/bin/activate"
echo "- Desativar ambiente virtual: deactivate"
echo "- Instalar nova dependência: pip install <pacote>"
echo "- Ver dependências: pip list"
echo ""
echo "📚 Documentação:"
echo "- README.md: Guia completo do projeto"
echo "- CONTRIBUTING.md: Como contribuir"
echo "- CHANGELOG.md: Histórico de versões"
echo ""
echo "🤖 Quitador está pronto para uso!"
echo "=================================="

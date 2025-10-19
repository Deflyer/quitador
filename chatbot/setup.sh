#!/bin/bash

# Script de setup completo do Chatbot de Pagamentos BTG
# Este script configura tudo automaticamente

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   🏦 CHATBOT DE PAGAMENTOS BTG - SETUP AUTOMÁTICO        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Diretório base
CHATBOT_DIR="/home/blomes/projects/Pagamento - BTG/chatbot"
SUGESTAO_DIR="/home/blomes/projects/Pagamento - BTG/Sugestao-acao"

# Navega para o diretório
cd "$CHATBOT_DIR"

# PASSO 1: Verificar Python
echo "📦 [1/7] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado!"
    echo "Instale Python 3.9+ e execute este script novamente."
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION encontrado"
echo ""

# PASSO 2: Criar ambiente virtual
echo "🔧 [2/7] Criando ambiente virtual..."
if [ -d "venv" ]; then
    echo "⚠️  Ambiente virtual já existe. Deseja recriar? (s/N)"
    read -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "✅ Ambiente virtual recriado"
    else
        echo "✅ Usando ambiente virtual existente"
    fi
else
    python3 -m venv venv
    echo "✅ Ambiente virtual criado"
fi
echo ""

# PASSO 3: Ativar ambiente virtual
echo "🔌 [3/7] Ativando ambiente virtual..."
source venv/bin/activate
echo "✅ Ambiente virtual ativado"
echo ""

# PASSO 4: Atualizar pip
echo "⬆️  [4/7] Atualizando pip..."
pip install --upgrade pip --quiet
echo "✅ Pip atualizado"
echo ""

# PASSO 5: Instalar dependências
echo "📥 [5/7] Instalando dependências (isso pode demorar)..."
pip install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    echo "✅ Dependências instaladas com sucesso"
else
    echo "❌ Erro ao instalar dependências"
    exit 1
fi
echo ""

# PASSO 6: Configurar arquivos .env
echo "🔑 [6/7] Configurando arquivos .env..."

# Verifica .env do chatbot
if [ ! -f "$CHATBOT_DIR/.env" ]; then
    echo "Criando $CHATBOT_DIR/.env..."
    cat > "$CHATBOT_DIR/.env" << EOF
# Configuração do Chatbot de Pagamentos BTG
OPENAI_API_KEY=COLE_SUA_CHAVE_AQUI
EOF
    echo "✅ Arquivo .env criado em: $CHATBOT_DIR/.env"
    ENV_PRECISA_CONFIG=1
else
    echo "✅ Arquivo .env já existe em: $CHATBOT_DIR/.env"
    ENV_PRECISA_CONFIG=0
fi

# Verifica .env do Sugestao-acao
if [ ! -f "$SUGESTAO_DIR/.env" ]; then
    echo "Criando $SUGESTAO_DIR/.env..."
    cat > "$SUGESTAO_DIR/.env" << EOF
# Configuração para o CrewAI
OPENAI_API_KEY=COLE_SUA_CHAVE_AQUI
EOF
    echo "✅ Arquivo .env criado em: $SUGESTAO_DIR/.env"
    ENV_PRECISA_CONFIG=1
else
    echo "✅ Arquivo .env já existe em: $SUGESTAO_DIR/.env"
fi
echo ""

# PASSO 7: Testar instalação (opcional)
echo "🧪 [7/7] Testes de integração..."
read -p "Deseja executar os testes agora? (s/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    python3 test_integration.py
    TEST_RESULT=$?
else
    echo "⏭️  Testes pulados"
    TEST_RESULT=0
fi
echo ""

# Verificar se precisa configurar .env
if [ $ENV_PRECISA_CONFIG -eq 1 ]; then
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ⚠️  AÇÃO NECESSÁRIA                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Os arquivos .env foram criados, mas você precisa adicionar"
    echo "sua chave da OpenAI!"
    echo ""
    echo "Execute um dos comandos abaixo para editar:"
    echo ""
    echo "  nano '$CHATBOT_DIR/.env'"
    echo "  nano '$SUGESTAO_DIR/.env'"
    echo ""
    echo "Substitua 'COLE_SUA_CHAVE_AQUI' pela sua chave real."
    echo ""
    read -p "Deseja editar o .env agora? (s/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        nano "$CHATBOT_DIR/.env"
        # Copia a mesma chave para o outro .env
        if grep -q "sk-" "$CHATBOT_DIR/.env"; then
            cp "$CHATBOT_DIR/.env" "$SUGESTAO_DIR/.env"
            echo "✅ Configuração copiada para ambos os .env"
        fi
    fi
fi

# Relatório final
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ SETUP CONCLUÍDO                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 Diretório: $CHATBOT_DIR"
echo "🐍 Python: $PYTHON_VERSION"
echo "📦 Ambiente virtual: ativado"
echo "✅ Dependências: instaladas"
echo ""

# Verifica se a chave foi configurada
if grep -q "sk-" "$CHATBOT_DIR/.env" 2>/dev/null; then
    echo "🔑 OpenAI Key: ✅ Configurada"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              🚀 PRONTO PARA USAR!                         ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Para iniciar o chatbot, execute:"
    echo ""
    echo "  cd '$CHATBOT_DIR'"
    echo "  source venv/bin/activate"
    echo "  python3 app.py"
    echo ""
    echo "Depois acesse: http://localhost:5000"
    echo ""
    
    read -p "Deseja iniciar o servidor agora? (s/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo ""
        echo "🚀 Iniciando servidor..."
        echo "📍 Acesse: http://localhost:5000"
        echo "⚠️  Pressione Ctrl+C para parar"
        echo ""
        sleep 2
        python3 app.py
    fi
else
    echo "🔑 OpenAI Key: ⚠️  NÃO configurada"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          ⚠️  CONFIGURE A CHAVE ANTES DE USAR              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "1. Edite o arquivo .env:"
    echo "   nano '$CHATBOT_DIR/.env'"
    echo ""
    echo "2. Adicione sua chave da OpenAI:"
    echo "   OPENAI_API_KEY=sk-proj-...sua_chave_aqui"
    echo ""
    echo "3. Copie a mesma chave para:"
    echo "   nano '$SUGESTAO_DIR/.env'"
    echo ""
    echo "4. Depois execute:"
    echo "   cd '$CHATBOT_DIR'"
    echo "   source venv/bin/activate"
    echo "   python3 app.py"
    echo ""
fi

echo "════════════════════════════════════════════════════════════"


"""
Aplicação Flask - Chatbot de Pagamento de Boletos BTG
"""
from flask import Flask, render_template, request, jsonify, session
import os
import sys
from datetime import datetime
import secrets

# Adiciona diretórios ao path
sys.path.append(os.path.dirname(__file__))

from chatbot_manager import ChatbotManager

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Armazena sessões de chatbot (em produção, usar Redis ou banco de dados)
chatbot_sessions = {}


def get_chatbot(session_id: str) -> ChatbotManager:
    """Obtém ou cria uma instância do chatbot para a sessão"""
    if session_id not in chatbot_sessions:
        # CNPJ padrão para demonstração
        cnpj_padrao = "12.345.678/0001-90"
        saldo_padrao = 10000.0
        
        chatbot_sessions[session_id] = ChatbotManager(
            cnpj=cnpj_padrao,
            saldo_atual=saldo_padrao,
            nome_usuario="Célia"
        )
    
    return chatbot_sessions[session_id]


@app.route('/')
def index():
    """Página principal do chatbot"""
    # Gera um ID de sessão se não existir
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
    
    return render_template('index.html')


@app.route('/api/message', methods=['POST'])
def message():
    """Endpoint para processar mensagens do usuário"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Mensagem vazia'}), 400
        
        # Obtém o chatbot da sessão
        session_id = session.get('session_id')
        if not session_id:
            session['session_id'] = secrets.token_hex(16)
            session_id = session['session_id']
        
        chatbot = get_chatbot(session_id)
        
        # Processa a mensagem
        resposta = chatbot.processar_mensagem(user_message)
        
        return jsonify({
            'response': resposta,
            'estado': chatbot.estado.value,
            'saldo_atual': chatbot.saldo_atual,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': f'Erro ao processar mensagem: {str(e)}'}), 500



@app.route('/api/historico', methods=['GET'])
def historico():
    """Retorna o histórico da conversa"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'historico': []})
        
        chatbot = get_chatbot(session_id)
        
        return jsonify({
            'historico': chatbot.historico,
            'saldo_atual': chatbot.saldo_atual
        })
    
    except Exception as e:
        return jsonify({'error': f'Erro ao obter histórico: {str(e)}'}), 500


if __name__ == '__main__':
    # Cria diretório de templates se não existir
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🚀 Iniciando Chatbot de Pagamentos BTG...")
    print("📍 Acesse: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)


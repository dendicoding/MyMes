from flask import Blueprint, render_template, request, jsonify

chatbot_bp = Blueprint('chatbot', __name__)

from chatbot import handle_chat  # Importa la funzione dal modulo chatbot.py
@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get("message")
    response = handle_chat(user_input)
    return jsonify({"response": response})

# Rotta per la chat specifica (chat.html)
@chatbot_bp.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    return render_template('chatbot.html')
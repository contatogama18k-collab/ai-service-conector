import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("WATSONX_API_KEY")
URL_WATSONX = os.getenv("WATSONX_URL")

@app.route('/api/index', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def webhook_route():
    if request.method == 'GET':
        return "Webhook RAG está Online!", 200

    # Pega o JSON de forma bruta
    data = request.get_json(force=True, silent=True) or {}
    
    # --- BUSCA EXAUSTIVA PELO INPUT ---
    # Tenta em todos os lugares que o Watson costuma esconder o texto
    user_message = (
        data.get("input") or 
        data.get("parameters", {}).get("input") or 
        data.get("text") or 
        data.get("message") or
        data.get("parameters", {}).get("text")
    )
    
    # Garante que seja string e remove espaços
    user_message = str(user_message or "").strip()

    # Se ainda estiver vazio, vamos tentar pegar o texto da "utterance" do Watson
    if not user_message and "text" in data:
        user_message = data["text"]

    if not user_message:
        return jsonify({"response": "Erro: O Webhook não encontrou o campo 'input'. Verifique o mapeamento no Watson Assistant."}), 200

    try:
        # Autenticação IBM
        iam_res = requests.post(
            "https://iam.cloud.ibm.com/identity/token", 
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        access_token = iam_res.json().get("access_token")

        # Payload para WatsonX (Role vazia conforme seu deployment)
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "", "content": user_message}]
        }

        response = requests.post(URL_WATSONX, headers=headers, json=payload)
# ... (depois do response = requests.post) ...
        result = response.json()
        
        # DEBUG: Se der erro, vamos devolver o JSON bruto da IBM para ler no Watson
        if response.status_code != 200:
            return jsonify({"response": f"Erro na IBM (Status {response.status_code}): {str(result)}"}), 200

        # Tenta extrair a resposta de vários formatos possíveis do WatsonX
        assistant_reply = ""
        try:
            if 'choices' in result:
                assistant_reply = result['choices'][0]['message']['content']
            elif 'results' in result: # Alguns modelos WatsonX usam 'results'
                assistant_reply = result['results'][0]['generated_text']
            elif 'messages' in result:
                assistant_reply = result['messages'][0]['content']
            else:
                # Se não achou nenhum campo conhecido, mostra o JSON para a gente debugar
                assistant_reply = f"Formato inesperado da IBM: {str(result)[:200]}"
        except Exception as e:
            assistant_reply = f"Erro ao processar JSON da IBM: {str(e)}"

        return jsonify({"response": assistant_reply})
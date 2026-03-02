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
        result = response.json()
        
        # Extração da resposta
        assistant_reply = ""
        if 'choices' in result:
            assistant_reply = result['choices'][0]['message']['content']
        elif 'messages' in result:
            assistant_reply = result['messages'][0]['content']
        else:
            assistant_reply = "Não foi possível extrair a resposta do WatsonX."

        return jsonify({"response": assistant_reply})

    except Exception as e:
        return jsonify({"response": f"Erro interno no conector: {str(e)}"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
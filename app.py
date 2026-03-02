import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configurações via Variáveis de Ambiente
API_KEY = os.getenv("WATSONX_API_KEY")
URL_WATSONX = os.getenv("WATSONX_URL")

@app.route('/api/index', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def webhook_route():
    if request.method == 'GET':
        return "Webhook RAG está Online!", 200

    data = request.get_json(silent=True) or {}
    user_message = data.get("input", "")
    context = data.get("context", [])

    if not user_message:
        return jsonify({"response": "Erro: Campo 'input' não encontrado."}), 400

    try:
        # 1. Autenticação IAM
        iam_res = requests.post(
            "https://iam.cloud.ibm.com/identity/token", 
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        iam_res.raise_for_status()
        access_token = iam_res.json().get("access_token")

        # 2. Chamada WatsonX
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"messages": [{"role": "user", "content": user_message}]}

        response = requests.post(URL_WATSONX, headers=headers, json=payload)
        result = response.json()
        
        # 3. Extração da resposta (simplificada)
        assistant_reply = result.get('choices', [{}])[0].get('message', {}).get('content', "Sem resposta.")

        return jsonify({
            "response": assistant_reply,
            "context": context + [{"role": "assistant", "content": assistant_reply}]
        })

    except Exception as e:
        return jsonify({"response": f"Erro interno: {str(e)}"}), 500

if __name__ == "__main__":
    # Importante para deploy local e reconhecimento de porta
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
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

    try:
        # Autenticação IBM
        iam_res = requests.post(
            "https://iam.cloud.ibm.com/identity/token", 
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        access_token = iam_res.json().get("access_token")

        # Payload para WatsonX (Role vazia conforme seu deployment)
        headers = {
            "Authorization": f"Bearer {access_token}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",  # A IBM exige 'user' aqui, não pode ser vazio
                    "content": user_message
                }
            ]
        }
        
        # 3. Chamada (Usando a URL de AI Service que você tem)
        response = requests.post(URL_WATSONX, headers=headers, json=payload)
        result = response.json()

        # 4. Extração da Resposta (Adicionando o campo 'choices' que a IBM usa no Chat)
        if 'choices' in result:
            assistant_reply = result['choices'][0]['message']['content']
        elif 'results' in result:
            assistant_reply = result['results'][0]['generated_text']
        else:
            # Se der erro de novo, o Watson vai nos mostrar o porquê
            assistant_reply = f"Erro na estrutura IBM: {str(result)}"

        return jsonify({"response": assistant_reply})

    except Exception as e:
        return jsonify({"response": f"Erro interno no conector: {str(e)}"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
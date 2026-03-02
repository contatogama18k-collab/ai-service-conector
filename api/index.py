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

    # 1. DEBUGS INICIAIS
    data = request.get_json(force=True, silent=True) or {}
    print(f"--- [DEBUG] PAYLOAD RECEBIDO DO WATSON: {data} ---")

    # Tenta capturar o input de todas as formas possíveis (Raiz ou Parameters)
    user_message = data.get("input") or data.get("parameters", {}).get("input")
    
    # Converte para string e limpa espaços (evita NoneType error)
    user_message = str(user_message or "").strip()
    print(f"--- [DEBUG] MENSAGEM EXTRAIDA: '{user_message}' ---")

    if not user_message:
        print("--- [ALERTA] Input vazio detectado! Verifique o mapeamento no Watson Assistant ---")
        return jsonify({"response": "Erro: O Webhook recebeu um texto vazio. Verifique o mapeamento no Watson."}), 200

    try:
        # 2. AUTENTICAÇÃO IAM
        iam_res = requests.post(
            "https://iam.cloud.ibm.com/identity/token", 
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        iam_res.raise_for_status()
        access_token = iam_res.json().get("access_token")

        # 3. CHAMADA WATSONX (Formato Exato do seu Deployment)
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        
        # Usando role vazia conforme o exemplo de sucesso do seu Prompt Lab
        payload = {
            "messages": [
                {
                    "role": "", 
                    "content": user_message
                }
            ]
        }
        
        print(f"--- [DEBUG] ENVIANDO PARA IBM: {payload} ---")

        response = requests.post(URL_WATSONX, headers=headers, json=payload)
        result = response.json()
        
        print(f"--- [DEBUG] RESPOSTA BRUTA DA IBM: {result} ---")

        # 4. EXTRAÇÃO DA RESPOSTA
        # Ajustado para procurar em 'choices' (padrão OpenAI/WatsonX moderno) ou 'messages'
        assistant_reply = ""
        if 'choices' in result:
            assistant_reply = result['choices'][0]['message']['content']
        elif 'messages' in result:
            assistant_reply = result['messages'][0]['content']
        else:
            assistant_reply = str(result)

        print(f"--- [DEBUG] RESPOSTA FINAL FORMATADA: {assistant_reply} ---")

        return jsonify({
            "response": assistant_reply,
            "context": [{"role": "assistant", "content": assistant_reply}]
        })

    except Exception as e:
        print(f"--- [ERRO CRÍTICO]: {str(e)} ---")
        return jsonify({"response": f"Erro interno: {str(e)}"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
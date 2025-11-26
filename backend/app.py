from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "backend"})

@app.route('/api/openrouter/chat', methods=['POST'])
def openrouter_chat():
    """
    Proxy endpoint for OpenRouter API
    """
    import requests
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return jsonify({"error": "OpenRouter API key not configured"}), 500
    
    # Get request data
    from flask import request
    data = request.get_json()
    
    # Forward to OpenRouter
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv('OPENROUTER_HTTP_REFERER', 'http://localhost:3000'),
        "X-Title": os.getenv('OPENROUTER_X_TITLE', 'AlphaLabs')
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


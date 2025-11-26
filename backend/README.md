# Backend API

Flask backend server for AlphaLabs.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `env.example` to `.env` and fill in your OpenRouter API key:
```bash
# On Windows PowerShell
Copy-Item env.example .env

# On Unix/Mac
cp env.example .env
```

3. Run the server:
```bash
python app.py
```

The server will run on `http://localhost:5000` by default.

## API Endpoints

- `GET /api/health` - Health check endpoint
- `POST /api/openrouter/chat` - Proxy endpoint for OpenRouter API


"""
Main FastAPI Application Entry Point.

Purpose:
    Initializes the FastAPI application, configures middleware (CORS), 
    sets up database connections/lifespan events, and registers API routers.

Data Flow:
    - Incoming: All HTTP requests to the backend.
    - Processing: Routes requests to specific routers (e.g., api/users.py) or handles global endpoints (health, webhooks).
    - Outgoing: HTTP responses back to the client.
    - Integration: Connects to Supabase/PostgreSQL and external APIs (OpenRouter, Clerk).
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from contextlib import asynccontextmanager
import os
import json
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database import get_supabase_client, get_db, validate_database_connection, validate_database_schema
from api import users, api_keys, agents, arena, data, results
from auth import verify_clerk_token, get_user_id_from_token
from webhooks import verify_webhook_signature, handle_user_created, handle_user_updated, handle_user_deleted
from models import User
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    
    Startup:
    - Validates database connection
    - Validates database schema (tables exist)
    - Logs configuration status
    
    Shutdown:
    - Closes database connections
    - Performs cleanup
    """
    # Startup
    logger.info("=" * 60)
    logger.info("AlphaLab Backend - Starting Application")
    logger.info("=" * 60)
    
    startup_success = False
    
    try:
        # Step 1: Validate database connection
        logger.info("Validating database connection...")
        await validate_database_connection()
        
        # Step 2: Validate database schema
        logger.info("Validating database schema...")
        await validate_database_schema()
        
        logger.info("=" * 60)
        logger.info("✓ Application startup successful")
        logger.info("  API is ready to accept requests")
        logger.info("=" * 60)
        startup_success = True
        
    except ValueError as e:
        # Configuration error (missing env vars, etc.)
        logger.error("=" * 60)
        logger.error("✗ Configuration Error")
        logger.error("=" * 60)
        logger.error(f"  {e}")
        logger.error("")
        logger.error("  Please check your environment variables:")
        logger.error("    - DATABASE_URL or SUPABASE_DB_* variables")
        logger.error("    - See backend/.env.example for reference")
        logger.error("=" * 60)
        raise SystemExit(1)
        
    except Exception as e:
        # Database connection or schema error
        logger.error("=" * 60)
        logger.error("✗ Application Startup Failed")
        logger.error("=" * 60)
        logger.error(f"  Error: {e}")
        logger.error("")
        logger.error("  Troubleshooting:")
        logger.error("    1. Verify database is running and accessible")
        logger.error("    2. Check database credentials in .env file")
        logger.error("    3. Ensure database tables are created (run migrations)")
        logger.error("    4. Run 'python init_db.py' for detailed diagnostics")
        logger.error("=" * 60)
        raise SystemExit(1)
    
    yield
    
    # Shutdown
    if startup_success:
        logger.info("Shutting down application...")
        logger.info("  Closing database connections...")
        from database import engine
        await engine.dispose()
        logger.info("✓ Shutdown complete")


from api.users import router as user_router

# ... (previous code)

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(agents.router)
app.include_router(arena.router)
app.include_router(data.router)
app.include_router(results.router)

@app.get('/api/health')
def health():
    return {"status": "ok", "service": "backend"}

@app.post('/api/openrouter/chat')
def openrouter_chat(request_data: dict):
    """
    Proxy endpoint for OpenRouter API
    """
    import requests
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
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
            json=request_data,
            timeout=30
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/webhooks/clerk')
async def clerk_webhook(request: Request, svix_id: Optional[str] = Header(None), svix_timestamp: Optional[str] = Header(None), svix_signature: Optional[str] = Header(None)):
    """
    Clerk webhook endpoint for automatic user synchronization
    Configure this URL in Clerk dashboard -> Webhooks
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature
        if svix_signature:
            # Clerk uses Svix for webhooks - signature format: v1,<signature>
            signature_parts = svix_signature.split(",")
            if len(signature_parts) == 2:
                signature = signature_parts[1]
                if not verify_webhook_signature(body, signature):
                    raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook data
        data = await request.json()
        event_type = data.get("type")
        
        # Handle different event types
        if event_type == "user.created":
            result = await handle_user_created(data)
            return result
        elif event_type == "user.updated":
            result = await handle_user_updated(data)
            return result
        elif event_type == "user.deleted":
            result = await handle_user_deleted(data)
            return result
        else:
            return {"message": f"Event type {event_type} not handled"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 5000))
    uvicorn.run("app:app", host='0.0.0.0', port=port, reload=True)


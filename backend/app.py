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


app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post('/api/users/sync')
async def sync_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync or create user in database from Clerk token.
    This endpoint should be called after user signs in/up in Clerk.
    
    Uses SQLAlchemy ORM for database operations.
    """
    try:
        # Verify Clerk token
        token_payload = await verify_clerk_token(authorization)
        clerk_user_id = get_user_id_from_token(token_payload)
        
        # Get user info from token
        # Clerk token structure: sub (user ID), email, and other claims
        # The token may contain user data directly or we may need to fetch from Clerk API
        email = token_payload.get("email")
        first_name = token_payload.get("first_name") or token_payload.get("given_name")
        last_name = token_payload.get("last_name") or token_payload.get("family_name")
        username = token_payload.get("username")
        image_url = token_payload.get("image_url") or token_payload.get("picture")
        
        # If email not in token, try to fetch from Clerk API using user ID
        if not email:
            # Fetch user details from Clerk API
            import requests
            clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
            if clerk_secret_key:
                try:
                    user_response = requests.get(
                        f"https://api.clerk.com/v1/users/{clerk_user_id}",
                        headers={"Authorization": f"Bearer {clerk_secret_key}"},
                        timeout=10
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        email = user_data.get("email_addresses", [{}])[0].get("email_address") if user_data.get("email_addresses") else None
                        first_name = first_name or user_data.get("first_name")
                        last_name = last_name or user_data.get("last_name")
                        username = username or user_data.get("username")
                        image_url = image_url or user_data.get("image_url")
                except Exception:
                    pass  # Continue with available data
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")
        
        # Check if user exists using SQLAlchemy
        stmt = select(User).where(User.clerk_id == clerk_user_id)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user
            existing_user.email = email
            if first_name is not None:
                existing_user.first_name = first_name
            if last_name is not None:
                existing_user.last_name = last_name
            if username is not None:
                existing_user.username = username
            if image_url is not None:
                existing_user.image_url = image_url
            
            await db.commit()
            await db.refresh(existing_user)
            
            return {
                "message": "User updated",
                "user": {
                    "id": str(existing_user.id),
                    "clerk_id": existing_user.clerk_id,
                    "email": existing_user.email,
                    "first_name": existing_user.first_name,
                    "last_name": existing_user.last_name,
                    "username": existing_user.username,
                    "image_url": existing_user.image_url,
                    "timezone": existing_user.timezone,
                    "plan": existing_user.plan,
                    "is_active": existing_user.is_active,
                    "created_at": existing_user.created_at.isoformat() if existing_user.created_at else None,
                    "updated_at": existing_user.updated_at.isoformat() if existing_user.updated_at else None,
                }
            }
        else:
            # Create new user
            new_user = User(
                clerk_id=clerk_user_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                username=username,
                image_url=image_url,
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            return {
                "message": "User created",
                "user": {
                    "id": str(new_user.id),
                    "clerk_id": new_user.clerk_id,
                    "email": new_user.email,
                    "first_name": new_user.first_name,
                    "last_name": new_user.last_name,
                    "username": new_user.username,
                    "image_url": new_user.image_url,
                    "timezone": new_user.timezone,
                    "plan": new_user.plan,
                    "is_active": new_user.is_active,
                    "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
                    "updated_at": new_user.updated_at.isoformat() if new_user.updated_at else None,
                }
            }
            
    except HTTPException:
        raise
    except IntegrityError as e:
        # Handle unique constraint violations
        await db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(status_code=409, detail="User with this email or clerk_id already exists")
    except SQLAlchemyError as e:
        # Handle other database errors
        await db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error syncing user: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing user: {str(e)}")

@app.get('/api/users/me')
async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile from database.
    Protected endpoint - requires valid Clerk token.
    
    Uses SQLAlchemy ORM with eager loading for related data.
    """
    try:
        # Verify Clerk token
        token_payload = await verify_clerk_token(authorization)
        clerk_user_id = get_user_id_from_token(token_payload)
        
        # Fetch user from database using SQLAlchemy
        stmt = select(User).where(User.clerk_id == clerk_user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found in database")
        
        return {
            "user": {
                "id": str(user.id),
                "clerk_id": user.clerk_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "image_url": user.image_url,
                "timezone": user.timezone,
                "plan": user.plan,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }
        }
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")

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


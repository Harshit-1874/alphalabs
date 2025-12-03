"""
FastAPI Dependencies for Dependency Injection.

Purpose:
    Provides reusable components that can be injected into API route handlers.
    Primarily handles authentication and database session management.

Data Flow:
    - Incoming: HTTP Headers (Authorization) from requests.
    - Processing: Verifies Clerk tokens, extracts user IDs, and queries the database.
    - Outgoing: Returns authenticated 'User' objects or active database sessions to route handlers.
    - Usage: Used in `Depends(...)` calls within API endpoint definitions.
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database import get_db
from auth import verify_clerk_token, get_user_id_from_token
from models import User

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to verify Clerk token and retrieve the current user from the database.
    """
    # Verify Clerk token
    token_payload = await verify_clerk_token(authorization)
    clerk_user_id = get_user_id_from_token(token_payload)
    
    # Fetch user from database
    stmt = select(User).where(User.clerk_id == clerk_user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

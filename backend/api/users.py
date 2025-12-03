"""
User Management API Endpoints.

Purpose:
    Handles all user-related HTTP requests including synchronization with Clerk,
    retrieving user profiles, and managing user settings.

Data Flow:
    - Incoming: HTTP requests with Clerk JWT tokens in headers.
    - Processing: Validates tokens, interacts with the database via SQLAlchemy.
    - Outgoing: JSON responses containing user data and settings (validated by Pydantic schemas).
    - Database: Reads/Writes to 'users' and 'user_settings' tables.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional
import os
import logging

from database import get_db
from models import User, UserSettings
from schemas import UserResponse, UserSettingsResponse, UserSettingsUpdate, UserProfileUpdate
from dependencies import get_current_user
from auth import verify_clerk_token, get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# 1. POST /api/users/sync
@router.post("/sync", response_model=UserResponse)
async def sync_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync or create user in database from Clerk token.
    This endpoint should be called after user signs in/up in Clerk.
    """
    try:
        # Verify Clerk token
        token_payload = await verify_clerk_token(authorization)
        clerk_user_id = get_user_id_from_token(token_payload)
        
        # Get user info from token
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
            return {"message": "User updated", "user": existing_user}
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
            return {"message": "User created", "user": new_user}
            
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(status_code=409, detail="User with this email or clerk_id already exists")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error syncing user: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing user: {str(e)}")

# 2. GET /api/users/me
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return {"user": current_user}

# 2.5 PUT /api/users/me
@router.put("/me", response_model=UserResponse)
async def update_me(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile fields.
    Currently supports: timezone
    Note: first_name, last_name, username, email are managed via Clerk.
    """
    try:
        # Validate timezone if provided
        if profile_update.timezone is not None:
            profile_update.validate_timezone(profile_update.timezone)
        
        # Update fields
        update_data = profile_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(current_user, key, value)
        
        await db.commit()
        await db.refresh(current_user)
        
        return {"user": current_user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error updating user profile: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


# 3. GET /api/users/me/settings
@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_my_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch settings via relationship or direct query
    stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings if they don't exist
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return {"settings": settings}

# 4. PUT /api/users/me/settings
@router.put("/me/settings", response_model=UserSettingsResponse)
async def update_my_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Should normally exist if GET was called or created on user creation, but handle safely
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    # Update fields
    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
        
    await db.commit()
    await db.refresh(settings)
    
    return {"settings": settings}

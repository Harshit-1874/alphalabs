"""
Pydantic Schemas for Data Validation.

Purpose:
    Defines the structure and validation rules for API request bodies and response models.
    Ensures type safety and consistent data formatting across the application.

Data Flow:
    - Incoming: Validates raw JSON data from API requests.
    - Outgoing: Formats internal Python objects (SQLAlchemy models) into JSON-compatible dictionaries for API responses.
    - Usage: Imported by API routers (e.g., api/users.py) to type-hint and validate endpoint signatures.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    image_url: Optional[str] = None

class User(UserBase):
    id: UUID
    clerk_id: str
    plan: str
    timezone: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):
    """Schema for updating user profile fields."""
    timezone: Optional[str] = None
    
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone string using cached timezone list."""
        from utils.timezone_cache import validate_timezone as validate_tz
        return validate_tz(v)


# --- User Settings Schemas ---
class UserSettingsBase(BaseModel):
    theme: Optional[str] = "dark"
    accent_color: Optional[str] = "cyan"
    sidebar_collapsed: Optional[bool] = False
    chart_grid_lines: Optional[bool] = True
    chart_crosshair: Optional[bool] = True
    chart_candle_colors: Optional[str] = "green_red"
    email_notifications: Optional[Dict[str, bool]] = None
    inapp_notifications: Optional[Dict[str, bool]] = None
    default_asset: Optional[str] = "BTC/USDT"
    default_timeframe: Optional[str] = "1h"
    default_capital: Optional[Decimal] = Field(default=10000.00)
    default_playback_speed: Optional[str] = "normal"
    safety_mode_default: Optional[bool] = True
    allow_leverage_default: Optional[bool] = False
    max_position_size_pct: Optional[int] = 50
    max_leverage: Optional[int] = 5
    max_loss_per_trade_pct: Optional[Decimal] = 5.00
    max_daily_loss_pct: Optional[Decimal] = 10.00
    max_total_drawdown_pct: Optional[Decimal] = 20.00

class UserSettingsUpdate(BaseModel):
    # All fields optional for updates
    theme: Optional[str] = None
    accent_color: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None
    chart_grid_lines: Optional[bool] = None
    chart_crosshair: Optional[bool] = None
    chart_candle_colors: Optional[str] = None
    email_notifications: Optional[Dict[str, bool]] = None
    inapp_notifications: Optional[Dict[str, bool]] = None
    default_asset: Optional[str] = None
    default_timeframe: Optional[str] = None
    default_capital: Optional[Decimal] = None
    default_playback_speed: Optional[str] = None
    safety_mode_default: Optional[bool] = None
    allow_leverage_default: Optional[bool] = None
    max_position_size_pct: Optional[int] = None
    max_leverage: Optional[int] = None
    max_loss_per_trade_pct: Optional[Decimal] = None
    max_daily_loss_pct: Optional[Decimal] = None
    max_total_drawdown_pct: Optional[Decimal] = None

class UserSettings(UserSettingsBase):
    user_id: UUID
    
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    message: Optional[str] = None
    user: User

class UserSettingsResponse(BaseModel):
    settings: UserSettings

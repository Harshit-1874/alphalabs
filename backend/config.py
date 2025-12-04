"""
Configuration Management for AlphaLab Backend.

Purpose:
    Centralized configuration using Pydantic BaseSettings for type-safe
    environment variable management with validation.

Usage:
    from config import settings
    api_key = settings.OPENROUTER_API_KEY
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    DATABASE_URL: str
    DB_CONNECTION_STRING: Optional[str] = None
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str  # Anon key (for public operations)
    SUPABASE_KEY2: Optional[str] = None  # Service role key (for backend operations, bypasses RLS)
    SUPABASE_DB_HOST: Optional[str] = None
    SUPABASE_DB_PORT: Optional[int] = 5432
    SUPABASE_DB_NAME: Optional[str] = "postgres"
    SUPABASE_DB_USER: Optional[str] = "postgres"
    SUPABASE_DB_PASSWORD: Optional[str] = None
    
    # External API Keys
    OPENROUTER_API_KEY: str
    OPENROUTER_HTTP_REFERER: str = "http://localhost:3000"
    OPENROUTER_X_TITLE: str = "AlphaLabs"
    
    # Clerk Authentication
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_WEBHOOK_SECRET: Optional[str] = None
    
    # Market Data API (placeholder for future use)
    MARKET_DATA_API_KEY: Optional[str] = None
    
    # Application Settings
    PORT: int = 5000
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Performance Limits
    MAX_CONCURRENT_BACKTESTS: int = 10
    MAX_CONCURRENT_FORWARD_TESTS: int = 5
    MAX_WEBSOCKET_CONNECTIONS: int = 100
    
    # Timeouts (in seconds)
    # How long we wait for an LLM trading decision before falling back to HOLD.
    # Kept intentionally low so backtests don't freeze the UI if OpenRouter is slow.
    AI_DECISION_TIMEOUT: int = 10
    MARKET_DATA_TIMEOUT: int = 10
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    
    # Retry Configuration
    # For trading decisions we generally want to fail fast rather than stall
    # the entire backtest on repeated timeouts.
    MAX_RETRIES: int = 1
    RETRY_BASE_DELAY: float = 1.0
    RETRY_MAX_DELAY: float = 5.0
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Database Connection Pool
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Cache Configuration
    CACHE_MAX_SIZE: int = 1000
    CACHE_TTL: int = 3600  # 1 hour
    
    # Export Limits
    MAX_EXPORT_SIZE_MB: int = 100
    EXPORT_EXPIRY_HOURS: int = 24
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = None
    
    # WebSocket configuration
    WEBSOCKET_BASE_URL: str = "ws://localhost:8000"
    
    # Storage / sharing
    CERTIFICATE_BUCKET: str = "certificates"
    CERTIFICATE_SHARE_BASE_URL: str = "http://localhost:3000/verify"  # Base URL for certificate verification (e.g., https://alphalab.io/verify)
    EXPORT_BUCKET: str = "exports"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency function to get settings instance.
    
    Returns:
        Settings: The global settings instance
    """
    return settings

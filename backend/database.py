"""
Database connection and utilities for Supabase
"""
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import logging

load_dotenv()

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance
    
    Requires either:
    - SUPABASE_URL and SUPABASE_KEY (recommended for Supabase client)
    - Or DB_CONNECTION_STRING (for direct PostgreSQL access, but Supabase client needs URL + KEY)
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        return create_client(supabase_url, supabase_key)
    
    # If using connection string, you still need URL and KEY for Supabase client
    # The connection string is for direct PostgreSQL access (psql, SQLAlchemy, etc.)
    db_connection_string = os.getenv("DB_CONNECTION_STRING")
    if db_connection_string:
        raise ValueError(
            "DB_CONNECTION_STRING is set, but SUPABASE_URL and SUPABASE_KEY are required "
            "for Supabase Python client. Use SUPABASE_URL and SUPABASE_KEY from your "
            "Supabase project settings (Settings -> API)."
        )
    
    raise ValueError(
        "Either SUPABASE_URL and SUPABASE_KEY, or DB_CONNECTION_STRING must be set. "
        "For Supabase client, use SUPABASE_URL and SUPABASE_KEY from project settings."
    )


# SQLAlchemy async setup
def get_database_url() -> str:
    """
    Constructs PostgreSQL connection URL from environment variables.
    
    Supports two configuration methods:
    1. DATABASE_URL: Full connection string (highest priority)
    2. Individual components: SUPABASE_DB_HOST, SUPABASE_DB_PORT, etc.
    3. DB_CONNECTION_STRING: Legacy connection string (converted to async format)
    
    Returns:
        str: Async PostgreSQL connection URL for SQLAlchemy
        
    Raises:
        ValueError: If required environment variables are missing
    """
    # Option 1: Use DATABASE_URL if provided
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Ensure it's using asyncpg driver
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql+asyncpg://"):
            return database_url
        else:
            raise ValueError("DATABASE_URL must start with 'postgresql://'")
    
    # Option 2: Use DB_CONNECTION_STRING if provided (legacy support)
    db_connection_string = os.getenv("DB_CONNECTION_STRING")
    if db_connection_string:
        # Convert to async format
        if db_connection_string.startswith("postgresql://"):
            return db_connection_string.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            raise ValueError("DB_CONNECTION_STRING must start with 'postgresql://'")
    
    # Option 3: Build from individual components
    db_host = os.getenv("SUPABASE_DB_HOST")
    db_port = os.getenv("SUPABASE_DB_PORT", "5432")
    db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
    db_user = os.getenv("SUPABASE_DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    
    if not all([db_host, db_user, db_password]):
        raise ValueError(
            "Database configuration missing. Provide either:\n"
            "1. DATABASE_URL environment variable, or\n"
            "2. DB_CONNECTION_STRING environment variable, or\n"
            "3. SUPABASE_DB_HOST, SUPABASE_DB_USER, and SUPABASE_DB_PASSWORD"
        )
    
    return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# Create async engine with connection pooling
engine: AsyncEngine = create_async_engine(
    get_database_url(),
    pool_size=20,           # Maximum number of connections in the pool
    max_overflow=10,        # Additional connections when pool is full
    pool_pre_ping=True,     # Verify connections before use
    echo=False,             # Set to True for SQL query logging
    pool_recycle=3600,      # Recycle connections after 1 hour
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI route handlers.
    
    Provides a database session that automatically handles:
    - Session creation
    - Transaction management (commit on success, rollback on error)
    - Session cleanup
    
    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def validate_database_connection() -> bool:
    """
    Validates database connection on application startup.
    
    Attempts to execute a simple query to verify:
    - Database is reachable
    - Credentials are correct
    - Connection pool is working
    
    Returns:
        bool: True if connection is successful
        
    Raises:
        Exception: If connection fails with details about the error
    """
    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))
            
            # Get PostgreSQL version for logging
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            
        # Log success with masked credentials
        db_url = get_database_url()
        masked_url = _mask_database_url(db_url)
            
        logger.info(f"✓ Database connection successful")
        logger.info(f"  Connection: {masked_url}")
        logger.info(f"  PostgreSQL: {version.split(',')[0] if version else 'Unknown'}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.error("  Please check:")
        logger.error("    - Database credentials are correct")
        logger.error("    - Database server is running and accessible")
        logger.error("    - Network connectivity to database host")
        logger.error("    - Environment variables are properly set")
        raise


def _mask_database_url(db_url: str) -> str:
    """
    Mask password in database URL for safe logging.
    
    Args:
        db_url: Database connection URL
        
    Returns:
        str: URL with password masked
    """
    if "@" in db_url:
        parts = db_url.split("@")
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            return db_url.replace(user_pass, f"{user}:***")
    return db_url


async def validate_database_schema() -> bool:
    """
    Validates that required database tables exist.
    
    Checks that all tables defined in SQLAlchemy models exist in the database.
    This is a lightweight check performed on startup to catch configuration issues.
    
    Returns:
        bool: True if all tables exist
        
    Raises:
        Exception: If tables are missing or validation fails
    """
    from sqlalchemy import inspect
    from models import Base
    
    try:
        async with engine.connect() as conn:
            # Get existing tables from database
            existing_tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
            
            # Get tables defined in models
            model_tables = set(Base.metadata.tables.keys())
            
            # Check for missing tables
            missing_tables = model_tables - existing_tables
            
            if missing_tables:
                logger.error(f"✗ Missing database tables: {sorted(missing_tables)}")
                logger.error("  Please run database migrations to create tables")
                logger.error("  See backend/migrations/ for SQL migration scripts")
                raise Exception(f"Missing required database tables: {', '.join(sorted(missing_tables))}")
            
            logger.info(f"✓ Database schema validated ({len(model_tables)} tables found)")
            return True
            
    except Exception as e:
        if "Missing required database tables" in str(e):
            raise
        logger.error(f"✗ Schema validation failed: {e}")
        raise


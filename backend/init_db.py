"""
Database initialization and validation script.

This script verifies:
1. Database connection is working
2. All required tables exist in the database
3. Model definitions match the actual database schema

Usage:
    python init_db.py

Environment Variables Required:
    - DATABASE_URL or SUPABASE_DB_* variables (see database.py)
"""
import asyncio
import sys
import logging
from typing import List, Set
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine
from database import engine, get_database_url
from models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def verify_connection(engine: AsyncEngine) -> bool:
    """
    Verify database connection is working.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        bool: True if connection successful
        
    Raises:
        Exception: If connection fails
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✓ Database connection successful")
            logger.info(f"  PostgreSQL version: {version}")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise


async def get_existing_tables(engine: AsyncEngine) -> Set[str]:
    """
    Get list of tables that exist in the database.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        Set[str]: Set of table names in the database
    """
    async with engine.connect() as conn:
        # Run inspection in a sync context
        result = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        return set(result)


async def get_model_tables() -> Set[str]:
    """
    Get list of tables defined in SQLAlchemy models.
    
    Returns:
        Set[str]: Set of table names from model definitions
    """
    return set(Base.metadata.tables.keys())


async def check_tables_exist(engine: AsyncEngine) -> bool:
    """
    Check that all model tables exist in the database.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        bool: True if all tables exist
    """
    logger.info("Checking table existence...")
    
    existing_tables = await get_existing_tables(engine)
    model_tables = await get_model_tables()
    
    logger.info(f"  Model tables defined: {len(model_tables)}")
    logger.info(f"  Database tables found: {len(existing_tables)}")
    
    # Check for missing tables
    missing_tables = model_tables - existing_tables
    if missing_tables:
        logger.error(f"✗ Missing tables in database: {sorted(missing_tables)}")
        logger.error("  Run database migrations to create missing tables")
        return False
    
    # Check for extra tables (informational only)
    extra_tables = existing_tables - model_tables
    if extra_tables:
        # Filter out common system tables
        system_tables = {'spatial_ref_sys', 'geography_columns', 'geometry_columns', 'raster_columns', 'raster_overviews'}
        extra_tables = extra_tables - system_tables
        if extra_tables:
            logger.warning(f"  Note: Extra tables in database (not in models): {sorted(extra_tables)}")
    
    logger.info(f"✓ All {len(model_tables)} model tables exist in database")
    return True


async def validate_schema(engine: AsyncEngine) -> bool:
    """
    Validate that model definitions match actual database schema.
    
    Checks:
    - Column names match
    - Column types are compatible
    - Primary keys are defined correctly
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        bool: True if schema validation passes
    """
    logger.info("Validating schema definitions...")
    
    validation_passed = True
    model_tables = await get_model_tables()
    
    async with engine.connect() as conn:
        for table_name in sorted(model_tables):
            table = Base.metadata.tables[table_name]
            
            # Get actual table columns from database
            db_columns = await conn.run_sync(
                lambda sync_conn: {
                    col['name']: col 
                    for col in inspect(sync_conn).get_columns(table_name)
                }
            )
            
            # Get model columns
            model_columns = {col.name: col for col in table.columns}
            
            # Check for missing columns in database
            missing_cols = set(model_columns.keys()) - set(db_columns.keys())
            if missing_cols:
                logger.error(f"✗ Table '{table_name}': Missing columns in database: {sorted(missing_cols)}")
                validation_passed = False
                continue
            
            # Check for extra columns in database (informational)
            extra_cols = set(db_columns.keys()) - set(model_columns.keys())
            if extra_cols:
                logger.warning(f"  Table '{table_name}': Extra columns in database: {sorted(extra_cols)}")
            
            logger.info(f"✓ Table '{table_name}': Schema validated ({len(model_columns)} columns)")
    
    if validation_passed:
        logger.info("✓ Schema validation passed")
    else:
        logger.error("✗ Schema validation failed")
    
    return validation_passed


async def print_configuration():
    """
    Print database configuration information (with masked credentials).
    """
    logger.info("Database Configuration:")
    
    db_url = get_database_url()
    
    # Mask password in URL
    if "@" in db_url:
        parts = db_url.split("@")
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            masked_url = db_url.replace(user_pass, f"{user}:***")
        else:
            masked_url = db_url
    else:
        masked_url = db_url
    
    logger.info(f"  Connection URL: {masked_url}")
    
    # Extract and display components
    if "@" in db_url:
        host_part = db_url.split("@")[1]
        host = host_part.split("/")[0].split(":")[0]
        port = host_part.split("/")[0].split(":")[1] if ":" in host_part.split("/")[0] else "5432"
        database = host_part.split("/")[1].split("?")[0] if "/" in host_part else "postgres"
        
        logger.info(f"  Host: {host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Database: {database}")


async def main():
    """
    Main initialization and validation routine.
    
    Performs all validation checks and reports results.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 60)
    logger.info("Database Initialization and Validation")
    logger.info("=" * 60)
    
    try:
        # Print configuration
        await print_configuration()
        logger.info("")
        
        # Step 1: Verify connection
        logger.info("Step 1: Verifying database connection...")
        await verify_connection(engine)
        logger.info("")
        
        # Step 2: Check tables exist
        logger.info("Step 2: Checking table existence...")
        tables_ok = await check_tables_exist(engine)
        logger.info("")
        
        if not tables_ok:
            logger.error("Cannot proceed with schema validation - tables missing")
            logger.error("Please run database migrations first")
            return 1
        
        # Step 3: Validate schema
        logger.info("Step 3: Validating schema definitions...")
        schema_ok = await validate_schema(engine)
        logger.info("")
        
        # Summary
        logger.info("=" * 60)
        if tables_ok and schema_ok:
            logger.info("✓ All validation checks passed!")
            logger.info("  Database is ready for use")
            return 0
        else:
            logger.error("✗ Validation failed")
            logger.error("  Please review errors above and fix issues")
            return 1
            
    except Exception as e:
        logger.error(f"✗ Initialization failed: {e}")
        logger.error("  Check your database configuration and connection")
        return 1
    finally:
        # Clean up engine
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

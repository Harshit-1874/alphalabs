#!/usr/bin/env python3
"""
Database migration runner for Supabase
Runs SQL migration files against the database using DB_CONNECTION_STRING
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """
    Create database connection using DB_CONNECTION_STRING
    """
    connection_string = os.getenv("DB_CONNECTION_STRING")
    if not connection_string:
        raise ValueError(
            "DB_CONNECTION_STRING environment variable is not set.\n"
            "Get it from Supabase Dashboard → Settings → Database → Connection string → URI"
        )
    
    try:
        conn = psycopg2.connect(connection_string)
        return conn
    except psycopg2.Error as e:
        raise ConnectionError(f"Failed to connect to database: {str(e)}")

def run_migration_file(conn, file_path: Path):
    """
    Execute a single SQL migration file
    """
    print(f"Running migration: {file_path.name}")
    
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        # Split by semicolons to handle multiple statements
        # But keep it simple - execute the whole file
        with conn.cursor() as cur:
            cur.execute(sql_content)
            conn.commit()
        
        print(f"✓ Successfully applied: {file_path.name}")
        return True
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"✗ Error in {file_path.name}: {str(e)}")
        return False
    except Exception as e:
        conn.rollback()
        print(f"✗ Unexpected error in {file_path.name}: {str(e)}")
        return False

def get_migration_files():
    """
    Get all SQL migration files in order
    """
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        print(f"✗ Migrations directory not found: {migrations_dir}")
        return []
    
    # Get all .sql files and sort by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    return migration_files

def run_migrations():
    """
    Run all pending migrations
    """
    print("=" * 60)
    print("Database Migration Runner")
    print("=" * 60)
    print()
    
    # Check connection
    try:
        conn = get_db_connection()
        print("✓ Connected to database")
    except Exception as e:
        print(f"✗ {str(e)}")
        sys.exit(1)
    
    # Get migration files
    migration_files = get_migration_files()
    
    if not migration_files:
        print("No migration files found")
        conn.close()
        return
    
    print(f"Found {len(migration_files)} migration file(s)")
    print()
    
    # Run migrations
    success_count = 0
    for migration_file in migration_files:
        if run_migration_file(conn, migration_file):
            success_count += 1
        print()
    
    conn.close()
    
    # Summary
    print("=" * 60)
    print(f"Migration Summary: {success_count}/{len(migration_files)} successful")
    print("=" * 60)
    
    if success_count == len(migration_files):
        print("✓ All migrations completed successfully!")
        sys.exit(0)
    else:
        print("✗ Some migrations failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()




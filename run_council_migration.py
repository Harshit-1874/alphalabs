#!/usr/bin/env python3
"""
Run Council Mode Migration
Adds council mode support to test_sessions and ai_thoughts tables
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables from backend/.env
backend_path = Path(__file__).parent / "backend"
env_path = backend_path / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded environment from {env_path}")
else:
    print(f"[WARNING] No .env file found at {env_path}, using system environment variables")

# Add backend to path
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from config import settings


def run_migration():
    """Run the council mode migration."""
    print("[START] Council Mode Migration...")
    
    # Use synchronous database URL (replace postgresql+asyncpg with postgresql)
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"[DB] Database: {db_url[:40]}...")
    
    # Read migration file
    migration_file = Path(__file__).parent / "backend" / "migrations" / "017_add_council_mode_support.sql"
    
    if not migration_file.exists():
        print(f"[ERROR] Migration file not found: {migration_file}")
        return False
    
    print(f"[READ] Reading migration: {migration_file.name}")
    migration_sql = migration_file.read_text()
    
    # Split into individual statements
    statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
    
    print(f"[INFO] Found {len(statements)} SQL statements to execute\n")
    
    # Create engine
    engine = create_engine(db_url, echo=False)
    
    try:
        with engine.begin() as conn:
            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"   [{i}/{len(statements)}] Executing...", end=" ")
                    try:
                        conn.execute(text(statement))
                        print("[OK]")
                    except Exception as e:
                        # Check if error is about column already existing (idempotent)
                        error_msg = str(e).lower()
                        if "already exists" in error_msg or "duplicate column" in error_msg:
                            print("[SKIP] Already exists")
                        else:
                            print(f"[ERROR] {e}")
                            raise
        
        print("\n[SUCCESS] Migration completed successfully!")
        
        # Verify migration
        print("\n[VERIFY] Checking new columns...")
        with engine.connect() as conn:
            # Check test_sessions columns
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'test_sessions' 
                AND column_name IN ('council_mode', 'council_models', 'council_chairman_model')
                ORDER BY column_name
            """))
            test_sessions_cols = [row[0] for row in result]
            
            # Check ai_thoughts columns
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ai_thoughts' 
                AND column_name IN ('council_stage1', 'council_stage2', 'council_metadata')
                ORDER BY column_name
            """))
            ai_thoughts_cols = [row[0] for row in result]
        
        print(f"\n[INFO] test_sessions: {', '.join(test_sessions_cols) if test_sessions_cols else 'None'}")
        print(f"[INFO] ai_thoughts: {', '.join(ai_thoughts_cols) if ai_thoughts_cols else 'None'}")
        
        expected_test_sessions = {'council_chairman_model', 'council_mode', 'council_models'}
        expected_ai_thoughts = {'council_metadata', 'council_stage1', 'council_stage2'}
        
        if set(test_sessions_cols) == expected_test_sessions and set(ai_thoughts_cols) == expected_ai_thoughts:
            print("\n" + "="*50)
            print("[SUCCESS] All columns verified!")
            print("="*50)
            print("\n=== NEXT STEPS ===")
            print("1. Restart your backend server")
            print("2. Refresh your frontend browser")
            print("3. Go to Backtest Arena page")
            print("4. You should see the Council Mode banner!")
            print("5. Enable Council Mode and start a backtest")
            print("\nCouncil Mode is ready to use!")
            return True
        else:
            print("\n[WARNING] Some columns may be missing. Please check the output above.")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        success = run_migration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[CANCEL] Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


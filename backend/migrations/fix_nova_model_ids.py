"""
Migration script to update all agents using amazon/nova-2-lite-v1 to amazon/nova-2-lite-v1:free.

This fixes agents that are using the paid version of Nova model, which requires credits.
The free version works without credits.

Run from project root: python -m backend.migrations.fix_nova_model_ids
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from models.agent import Agent
from config import settings

async def fix_nova_model_ids():
    """Update all agents with amazon/nova-2-lite-v1 to use the free version."""
    # Ensure we use asyncpg driver
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, echo=False)
    
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            # Find all agents with the old model ID (without :free)
            result = await db.execute(
                select(Agent).where(Agent.model == "amazon/nova-2-lite-v1")
            )
            agents_to_update = result.scalars().all()
            
            if not agents_to_update:
                print("No agents found with 'amazon/nova-2-lite-v1' model. Migration not needed.")
                return
            
            print(f"Found {len(agents_to_update)} agents to update:")
            
            updated_count = 0
            for agent in agents_to_update:
                old_model = agent.model
                agent.model = "amazon/nova-2-lite-v1:free"
                print(f"  - Agent '{agent.name}' (ID: {agent.id}): {old_model} -> {agent.model}")
                updated_count += 1
            
            await db.commit()
            print(f"\n[SUCCESS] Successfully updated {updated_count} agents to use the free Nova model.")
            
    except Exception as e:
        print(f"[ERROR] Error updating agents: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("Starting Nova model ID fix migration...")
    asyncio.run(fix_nova_model_ids())
    print("Migration complete!")


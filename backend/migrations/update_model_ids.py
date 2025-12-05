"""
Migration script to update agent model IDs to match OpenRouter's exact format.

This script updates all agents in the database that have old model IDs
to use the correct OpenRouter model IDs with provider prefixes.

Run from project root: python -m backend.migrations.update_model_ids
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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from models.agent import Agent
from config import settings

# Mapping of old model IDs to new OpenRouter model IDs
MODEL_ID_MAPPING = {
    "olmo-3-32b-think": "allenai/olmo-3-32b-think:free",
    "qwen3-235b-a22b": "qwen/qwen3-235b-a22b",
    "qwen3-coder-480b-a35b": "qwen/qwen3-coder",
    "qwen3-4b": "qwen/qwen3-4b:free",
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "trinity-mini": "arcee-ai/trinity-mini",
    "nova-2-lite": "amazon/nova-2-lite-v1:free",
    "amazon/nova-2-lite-v1": "amazon/nova-2-lite-v1:free",  # Fix agents using paid version
    "hermes-3-405b-instruct": "nousresearch/hermes-3-llama-3.1-405b",
    "nemotron-nano-12b-vl": "nvidia/nemotron-nano-12b-v2-vl",
    "nemotron-nano-9b-v2": "nvidia/nemotron-nano-9b-v2",
    "kimi-k2-0711": "moonshotai/kimi-k2",
    "gemma-3-27b": "google/gemma-3-27b-it",
    "gemma-3n-4b": "google/gemma-3n-e4b-it",
    "gemma-3n-2b": "google/gemma-3n-e2b-it:free",
    "gemma-3-4b": "google/gemma-3-4b-it",
    "gemma-3-12b": "google/gemma-3-12b-it",
    "gemma-3n-27b": "google/gemma-3-27b-it",
    "mistral-7b-instruct": "mistralai/mistral-7b-instruct-v0.3",
    "llama-3.3-70b-instruct": "meta-llama/llama-3.1-70b-instruct",  # Updated to available model
}


async def update_agent_model_ids():
    """Update all agents with old model IDs to use new OpenRouter format."""
    # Ensure we use asyncpg driver
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, echo=False)
    
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            # Find all agents with old model IDs
            result = await db.execute(
                select(Agent).where(Agent.model.in_(list(MODEL_ID_MAPPING.keys())))
            )
            agents_to_update = result.scalars().all()
            
            if not agents_to_update:
                print("No agents found with old model IDs. Migration not needed.")
                return
            
            print(f"Found {len(agents_to_update)} agents to update:")
            
            updated_count = 0
            for agent in agents_to_update:
                old_model = agent.model
                new_model = MODEL_ID_MAPPING[old_model]
                agent.model = new_model
                print(f"  - Agent '{agent.name}' (ID: {agent.id}): {old_model} -> {new_model}")
                updated_count += 1
            
            await db.commit()
            print(f"\n✅ Successfully updated {updated_count} agents.")
            
    except Exception as e:
        print(f"❌ Error updating agents: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("Starting model ID migration...")
    asyncio.run(update_agent_model_ids())
    print("Migration complete!")

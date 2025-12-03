"""
Agent Service.

Purpose:
    Encapsulates business logic for managing AI Agents.
    Handles database interactions, ownership verification, and data integrity for agents.

Data Flow:
    - Incoming: Validated schema objects (AgentCreate, AgentUpdate) from the API layer.
    - Processing:
        - Verifies that the referenced API key belongs to the user.
        - Checks for duplicate agent names per user.
        - Performs DB operations (INSERT, SELECT, UPDATE, DELETE).
    - Outgoing: SQLAlchemy model instances (Agent) returned to the API layer.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.orm import joinedload
from uuid import UUID
from typing import List, Optional, Dict, Any

from models import Agent, ApiKey
from schemas.agent_schemas import AgentCreate, AgentUpdate

class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_agent(self, user_id: UUID, agent_data: AgentCreate) -> Agent:
        """Create a new agent."""
        # Verify API key belongs to user
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == agent_data.api_key_id, ApiKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise ValueError("Invalid API key")

        # Check for duplicate name for this user
        result = await self.db.execute(
            select(Agent).where(Agent.user_id == user_id, Agent.name == agent_data.name)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Agent with name '{agent_data.name}' already exists")

        new_agent = Agent(
            user_id=user_id,
            **agent_data.model_dump()
        )
        self.db.add(new_agent)
        await self.db.commit()
        # Refresh with relationship
        result = await self.db.execute(
            select(Agent).options(joinedload(Agent.api_key)).where(Agent.id == new_agent.id)
        )
        return result.scalar_one()

    async def get_agent(self, user_id: UUID, agent_id: UUID) -> Optional[Agent]:
        """Get a single agent by ID."""
        result = await self.db.execute(
            select(Agent)
            .options(joinedload(Agent.api_key))
            .where(Agent.id == agent_id, Agent.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_agents(
        self, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        include_archived: bool = False
    ) -> List[Agent]:
        """List agents for a user."""
        query = select(Agent).options(joinedload(Agent.api_key)).where(Agent.user_id == user_id)
        
        if not include_archived:
            query = query.where(Agent.is_archived == False)
            
        query = query.order_by(Agent.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_agent(self, user_id: UUID, agent_id: UUID, agent_data: AgentUpdate) -> Optional[Agent]:
        """Update an agent."""
        agent = await self.get_agent(user_id, agent_id)
        if not agent:
            return None

        update_data = agent_data.model_dump(exclude_unset=True)
        
        # If updating API key, verify ownership
        if "api_key_id" in update_data and update_data["api_key_id"]:
            result = await self.db.execute(
                select(ApiKey).where(ApiKey.id == update_data["api_key_id"], ApiKey.user_id == user_id)
            )
            if not result.scalar_one_or_none():
                raise ValueError("Invalid API key")

        for key, value in update_data.items():
            setattr(agent, key, value)

        await self.db.commit()
        # Refresh with relationship
        result = await self.db.execute(
            select(Agent).options(joinedload(Agent.api_key)).where(Agent.id == agent.id)
        )
        return result.scalar_one()

    async def delete_agent(self, user_id: UUID, agent_id: UUID, hard_delete: bool = False) -> bool:
        """Delete or archive an agent."""
        agent = await self.get_agent(user_id, agent_id)
        if not agent:
            return False

        if hard_delete:
            await self.db.delete(agent)
        else:
            agent.is_archived = True
        
        await self.db.commit()
        return True

    async def duplicate_agent(self, user_id: UUID, agent_id: UUID, new_name: str) -> Optional[Agent]:
        """Duplicate an existing agent."""
        agent = await self.get_agent(user_id, agent_id)
        if not agent:
            return None
            
        # Check for duplicate name
        result = await self.db.execute(
            select(Agent).where(Agent.user_id == user_id, Agent.name == new_name)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Agent with name '{new_name}' already exists")

        new_agent = Agent(
            user_id=user_id,
            api_key_id=agent.api_key_id,
            name=new_name,
            mode=agent.mode,
            model=agent.model,
            indicators=agent.indicators,
            custom_indicators=agent.custom_indicators,
            strategy_prompt=agent.strategy_prompt
        )
        
        self.db.add(new_agent)
        await self.db.commit()
        # Refresh with relationship
        result = await self.db.execute(
            select(Agent).options(joinedload(Agent.api_key)).where(Agent.id == new_agent.id)
        )
        return result.scalar_one()

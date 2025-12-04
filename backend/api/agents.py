"""
Agent Endpoints.

Purpose:
    Exposes RESTful API endpoints for Agent CRUD operations.
    Acts as the interface between the frontend and the Agent Service.

Data Flow:
    - Incoming: HTTP requests for agent operations (Create, Read, Update, Delete, Duplicate).
    - Processing:
        - Authenticates user via Clerk.
        - Delegates business logic to AgentService.
        - Handles HTTP errors (404 Not Found, 400 Bad Request).
    - Outgoing: JSON responses containing agent details or status messages to the client.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from database import get_db
from dependencies import get_current_user
from services.agent_service import AgentService
from schemas.agent_schemas import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse, AgentDuplicateRequest

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("", response_model=AgentListResponse)
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    sort: Optional[str] = Query("newest", regex="^(newest|oldest|performance|tests|alpha)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agents for the current user."""
    service = AgentService(db)
    agents = await service.list_agents(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        include_archived=include_archived,
        sort=sort
    )
    return {"agents": agents, "total": len(agents)}

@router.post("", response_model=dict)
async def create_agent(
    agent_data: AgentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent."""
    service = AgentService(db)
    try:
        new_agent = await service.create_agent(
            user_id=current_user.id,
            agent_data=agent_data
        )
        return {"agent": AgentResponse.model_validate(new_agent), "message": "Agent created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent details."""
    service = AgentService(db)
    agent = await service.get_agent(user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an agent."""
    service = AgentService(db)
    try:
        updated_agent = await service.update_agent(
            user_id=current_user.id,
            agent_id=agent_id,
            agent_data=agent_data
        )
        if not updated_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return updated_agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{agent_id}", response_model=dict)
async def delete_agent(
    agent_id: UUID,
    archive: bool = True,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete or archive an agent."""
    service = AgentService(db)
    success = await service.delete_agent(
        user_id=current_user.id,
        agent_id=agent_id,
        hard_delete=not archive
    )
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    action = "archived" if archive else "deleted"
    return {"message": f"Agent {action}", "id": agent_id}

@router.post("/{agent_id}/restore", response_model=dict)
async def restore_agent(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore an archived agent."""
    service = AgentService(db)
    success = await service.restore_agent(
        user_id=current_user.id,
        agent_id=agent_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent restored", "id": agent_id}

@router.post("/{agent_id}/duplicate", response_model=dict)
async def duplicate_agent(
    agent_id: UUID,
    request: AgentDuplicateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Duplicate an existing agent."""
    service = AgentService(db)
    try:
        new_agent = await service.duplicate_agent(
            user_id=current_user.id,
            agent_id=agent_id,
            new_name=request.new_name
        )
        if not new_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"agent": AgentResponse.model_validate(new_agent), "message": "Agent duplicated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{agent_id}/stats", response_model=dict)
async def get_agent_stats(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed agent stats."""
    service = AgentService(db)
    agent = await service.get_agent(user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Return computed stats from agent model
    return {
        "stats": {
            "total_tests": agent.tests_run,
            "profitable_tests": agent.total_profitable_tests,
            "best_pnl": agent.best_pnl,
            "avg_win_rate": agent.avg_win_rate,
            "avg_drawdown": agent.avg_drawdown
        }
    }

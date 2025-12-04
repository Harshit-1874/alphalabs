"""
Agent Schemas.

Purpose:
    Defines Pydantic models for AI Agent configuration.
    Validates agent creation and update requests, ensuring correct types and constraints.

Data Flow:
    - Incoming: JSON payloads for creating/updating agents (name, model, strategy, etc.).
    - Processing: Validates constraints (e.g., mode must be 'monk' or 'omni', strategy length).
    - Outgoing: Structured data for the Agent Service, and JSON responses for the API.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class CustomIndicator(BaseModel):
    name: str
    formula: str

class AgentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    mode: str = Field(..., pattern="^(monk|omni)$")
    model: str = Field(..., min_length=1)
    indicators: List[str] = Field(..., min_items=1)
    custom_indicators: Optional[List[CustomIndicator]] = []
    strategy_prompt: str = Field(..., min_length=50, max_length=4000)

class AgentCreate(AgentBase):
    api_key_id: UUID

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    mode: Optional[str] = Field(None, pattern="^(monk|omni)$")
    model: Optional[str] = Field(None, min_length=1)
    indicators: Optional[List[str]] = Field(None, min_items=1)
    custom_indicators: Optional[List[CustomIndicator]] = None
    strategy_prompt: Optional[str] = Field(None, min_length=50, max_length=4000)
    api_key_id: Optional[UUID] = None
    is_archived: Optional[bool] = None

class AgentResponse(AgentBase):
    id: UUID
    user_id: UUID
    api_key_id: Optional[UUID]
    api_key_masked: Optional[str] = None
    
    # Computed stats
    tests_run: int
    best_pnl: Optional[Decimal]
    total_profitable_tests: int
    avg_win_rate: Optional[Decimal]
    avg_drawdown: Optional[Decimal]
    
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int

class AgentDuplicateRequest(BaseModel):
    new_name: str = Field(..., min_length=2, max_length=100)
"""
Models package for AlphaLab backend.

This package provides SQLAlchemy ORM models for all database tables,
organized by domain. All models are exported from this module for
convenient importing throughout the application.

Usage:
    from models import User, Agent, TestSession
    from models import Base  # For metadata operations
"""

# Base classes and mixins
from models.base import Base, TimestampMixin, UUIDMixin

# User domain models
from models.user import User, UserSettings, ApiKey

# Agent domain models
from models.agent import Agent

# Arena domain models
from models.arena import TestSession, Trade, AiThought

# Result domain models
from models.result import TestResult, Certificate

# Activity domain models
from models.activity import Notification, ActivityLog, MarketDataCache


__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    
    # User models
    "User",
    "UserSettings",
    "ApiKey",
    
    # Agent models
    "Agent",
    
    # Arena models
    "TestSession",
    "Trade",
    "AiThought",
    
    # Result models
    "TestResult",
    "Certificate",
    
    # Activity models
    "Notification",
    "ActivityLog",
    "MarketDataCache",
]

"""
Dashboard Service.

Purpose:
    Encapsulates business logic for dashboard statistics and activity feed.
    Handles aggregation of user metrics, trend calculations, and activity retrieval.

Data Flow:
    - Incoming: User ID and query parameters from API layer
    - Processing:
        - Aggregates statistics from agents, test_results, and test_sessions
        - Calculates trends by comparing current vs previous periods
        - Retrieves recent activity from activity_logs
        - Determines quick-start onboarding progress
    - Outgoing: Dictionaries with dashboard data returned to API layer
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import joinedload
from uuid import UUID
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from models import Agent, TestResult, ActivityLog, Certificate, TestSession


class DashboardService:
    """Service for dashboard statistics and activity."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the dashboard service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def get_stats(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get dashboard overview statistics.
        
        Aggregates key metrics including:
        - Total agents (not archived)
        - Total tests run
        - Best PnL across all results
        - Average win rate
        - Trends (comparison to previous period)
        - Best performing agent
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with dashboard statistics
        """
        # Count total agents (not archived)
        total_agents_result = await self.db.execute(
            select(func.count(Agent.id))
            .where(
                Agent.user_id == user_id,
                Agent.is_archived == False
            )
        )
        total_agents = total_agents_result.scalar_one()
        
        # Count total tests run (completed test results)
        tests_run_result = await self.db.execute(
            select(func.count(TestResult.id))
            .where(TestResult.user_id == user_id)
        )
        tests_run = tests_run_result.scalar_one()
        
        # Get best PnL
        best_pnl_result = await self.db.execute(
            select(func.max(TestResult.total_pnl_pct))
            .where(TestResult.user_id == user_id)
        )
        best_pnl = best_pnl_result.scalar_one()
        
        # Get average win rate
        avg_win_rate_result = await self.db.execute(
            select(func.avg(TestResult.win_rate))
            .where(TestResult.user_id == user_id)
        )
        avg_win_rate = avg_win_rate_result.scalar_one()
        
        # Calculate trends (compare last 30 days vs previous 30 days)
        trends = await self._calculate_trends(user_id)
        
        # Get best performing agent
        best_agent = await self._get_best_agent(user_id)
        
        return {
            "total_agents": total_agents,
            "tests_run": tests_run,
            "best_pnl": float(best_pnl) if best_pnl else None,
            "avg_win_rate": float(avg_win_rate) if avg_win_rate else None,
            "trends": trends,
            "best_agent": best_agent
        }
    
    async def _calculate_trends(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate trend metrics by comparing current period to previous period.
        
        Compares last 30 days vs previous 30 days for:
        - Tests run
        - Average PnL
        - Win rate
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with trend data
        """
        now = datetime.utcnow()
        current_period_start = now - timedelta(days=30)
        previous_period_start = now - timedelta(days=60)
        
        # Current period stats (last 30 days)
        current_tests_result = await self.db.execute(
            select(func.count(TestResult.id))
            .where(
                TestResult.user_id == user_id,
                TestResult.created_at >= current_period_start
            )
        )
        current_tests = current_tests_result.scalar_one()
        
        current_pnl_result = await self.db.execute(
            select(func.avg(TestResult.total_pnl_pct))
            .where(
                TestResult.user_id == user_id,
                TestResult.created_at >= current_period_start
            )
        )
        current_avg_pnl = current_pnl_result.scalar_one()
        
        current_win_rate_result = await self.db.execute(
            select(func.avg(TestResult.win_rate))
            .where(
                TestResult.user_id == user_id,
                TestResult.created_at >= current_period_start
            )
        )
        current_avg_win_rate = current_win_rate_result.scalar_one()
        
        # Previous period stats (30-60 days ago)
        previous_tests_result = await self.db.execute(
            select(func.count(TestResult.id))
            .where(
                TestResult.user_id == user_id,
                TestResult.created_at >= previous_period_start,
                TestResult.created_at < current_period_start
            )
        )
        previous_tests = previous_tests_result.scalar_one()
        
        previous_pnl_result = await self.db.execute(
            select(func.avg(TestResult.total_pnl_pct))
            .where(
                TestResult.user_id == user_id,
                TestResult.created_at >= previous_period_start,
                TestResult.created_at < current_period_start
            )
        )
        previous_avg_pnl = previous_pnl_result.scalar_one()
        
        previous_win_rate_result = await self.db.execute(
            select(func.avg(TestResult.win_rate))
            .where(
                TestResult.user_id == user_id,
                TestResult.created_at >= previous_period_start,
                TestResult.created_at < current_period_start
            )
        )
        previous_avg_win_rate = previous_win_rate_result.scalar_one()
        
        # Calculate percentage changes
        def calculate_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
            """Calculate percentage change between two values."""
            if current is None or previous is None or previous == 0:
                return None
            return ((current - previous) / abs(previous)) * 100
        
        tests_change = calculate_change(
            float(current_tests) if current_tests else None,
            float(previous_tests) if previous_tests else None
        )
        
        pnl_change = calculate_change(
            float(current_avg_pnl) if current_avg_pnl else None,
            float(previous_avg_pnl) if previous_avg_pnl else None
        )
        
        win_rate_change = calculate_change(
            float(current_avg_win_rate) if current_avg_win_rate else None,
            float(previous_avg_win_rate) if previous_avg_win_rate else None
        )
        
        return {
            "tests_run_change": tests_change,
            "avg_pnl_change": pnl_change,
            "win_rate_change": win_rate_change,
            "period_days": 30
        }
    
    async def _get_best_agent(
        self,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best performing agent based on best_pnl.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with best agent data, or None if no agents
        """
        result = await self.db.execute(
            select(Agent)
            .where(
                Agent.user_id == user_id,
                Agent.is_archived == False,
                Agent.best_pnl.isnot(None)
            )
            .order_by(desc(Agent.best_pnl))
            .limit(1)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            return None
        
        return {
            "id": str(agent.id),
            "name": agent.name,
            "mode": agent.mode,
            "model": agent.model,
            "best_pnl": float(agent.best_pnl) if agent.best_pnl else None,
            "tests_run": agent.tests_run,
            "avg_win_rate": float(agent.avg_win_rate) if agent.avg_win_rate else None
        }
    
    async def get_activity(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity feed for dashboard.
        
        Retrieves activity logs ordered by created_at descending.
        Includes agent name and result PnL when available.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of activity items to return (default: 10, max: 50)
            
        Returns:
            List of activity items with formatted data
        """
        # Enforce maximum limit
        limit = min(limit, 50)
        
        # Query activity logs with related data
        result = await self.db.execute(
            select(ActivityLog)
            .options(
                joinedload(ActivityLog.agent),
                joinedload(ActivityLog.result)
            )
            .where(ActivityLog.user_id == user_id)
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
        )
        activity_logs = result.scalars().all()
        
        # Format activity items
        activity_items = []
        for log in activity_logs:
            item = {
                "id": str(log.id),
                "type": log.activity_type,
                "description": log.description,
                "timestamp": log.created_at.isoformat(),
                "agent_name": log.agent.name if log.agent else None,
                "pnl": float(log.result.total_pnl_pct) if log.result else None,
                "result_id": str(log.result_id) if log.result_id else None
            }
            activity_items.append(item)
        
        return activity_items
    
    async def get_quick_start_progress(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get onboarding quick-start progress.
        
        Checks completion status for key onboarding steps:
        1. Create first agent
        2. Run first backtest
        3. Generate first certificate
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with steps and progress percentage
        """
        # Check if user has created an agent
        has_agent_result = await self.db.execute(
            select(func.count(Agent.id))
            .where(Agent.user_id == user_id)
            .limit(1)
        )
        has_agent = has_agent_result.scalar_one() > 0
        
        # Check if user has run a backtest
        has_backtest_result = await self.db.execute(
            select(func.count(TestResult.id))
            .where(
                TestResult.user_id == user_id,
                TestResult.type == 'backtest'
            )
            .limit(1)
        )
        has_backtest = has_backtest_result.scalar_one() > 0
        
        # Check if user has generated a certificate
        has_certificate_result = await self.db.execute(
            select(func.count(Certificate.id))
            .where(Certificate.user_id == user_id)
            .limit(1)
        )
        has_certificate = has_certificate_result.scalar_one() > 0
        
        # Define steps
        steps = [
            {
                "id": "create_agent",
                "label": "Create Your First Agent",
                "description": "Design an AI trading agent with custom indicators and strategy",
                "is_complete": has_agent,
                "href": "/dashboard/agents/new",
                "cta_text": "Create Agent"
            },
            {
                "id": "run_backtest",
                "label": "Run Your First Backtest",
                "description": "Test your agent on historical data to see how it performs",
                "is_complete": has_backtest,
                "href": "/dashboard/arena/backtest",
                "cta_text": "Start Backtest"
            },
            {
                "id": "generate_certificate",
                "label": "Generate a Certificate",
                "description": "Share your profitable results with a verified certificate",
                "is_complete": has_certificate,
                "href": "/dashboard/results",
                "cta_text": "View Results"
            }
        ]
        
        # Calculate progress percentage
        completed_steps = sum(1 for step in steps if step["is_complete"])
        total_steps = len(steps)
        progress_pct = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
        
        return {
            "steps": steps,
            "progress_pct": round(progress_pct, 2)
        }

"""
Export Service.

Purpose:
    Encapsulates business logic for generating user data export packages.
    Handles export job creation, data collection, packaging, and status tracking.

Data Flow:
    - Incoming: User ID and export configuration from API layer
    - Processing:
        - Creates export job record (or tracks in-memory if no Export model)
        - Collects user data from multiple tables (agents, results, trades, settings)
        - Packages data as JSON or ZIP archive
        - Generates download URL with expiration
    - Outgoing: Export status and download information returned to API layer

Note:
    This implementation uses an in-memory tracking approach since the Export model
    doesn't exist yet. For production, implement task 16 to add the Export model.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from uuid import UUID, uuid4
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import zipfile
import io
import os

from models import (
    User, UserSettings, Agent, TestResult, TestSession, 
    Trade, Certificate, Notification, ActivityLog, ApiKey
)


# In-memory export tracking (replace with database model in production)
_export_jobs: Dict[UUID, Dict[str, Any]] = {}


class ExportService:
    """Service for generating user data export packages."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the export service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_export(
        self,
        user_id: UUID,
        include: Dict[str, bool],
        format: str = "zip"
    ) -> Dict[str, Any]:
        """
        Create a data export job for a user.
        
        Initiates an export job that will collect and package user data
        based on the specified inclusions. The actual export generation
        should be run as a background task.
        
        Args:
            user_id: ID of the user requesting export
            include: Dictionary specifying what to include:
                - agents: Include agent configurations
                - results: Include test results
                - trades: Include trade history
                - settings: Include user settings
                - reasoning_traces: Include AI reasoning logs
            format: Export format ('json' or 'zip')
            
        Returns:
            Dictionary with export job information:
                - export_id: UUID of the export job
                - status: Current status ('processing')
                - created_at: Job creation timestamp
                
        Raises:
            ValueError: If format is invalid
        """
        # Validate format
        if format not in ['json', 'zip']:
            raise ValueError(f"Invalid format '{format}'. Must be 'json' or 'zip'")
        
        # Create export job
        export_id = uuid4()
        export_job = {
            'export_id': export_id,
            'user_id': user_id,
            'include': include,
            'format': format,
            'status': 'processing',
            'progress_pct': 0.0,
            'download_url': None,
            'expires_at': None,
            'size_mb': None,
            'error': None,
            'created_at': datetime.utcnow()
        }
        
        # Store in memory (replace with database insert in production)
        _export_jobs[export_id] = export_job
        
        return {
            'export_id': str(export_id),
            'status': 'processing',
            'progress_pct': 0.0,
            'created_at': export_job['created_at'].isoformat()
        }
    
    async def get_export_status(
        self,
        export_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get the status of an export job.
        
        Args:
            export_id: ID of the export job
            user_id: ID of the user (for ownership validation)
            
        Returns:
            Dictionary with export status information, or None if not found:
                - export_id: UUID of the export job
                - status: Current status ('processing', 'ready', 'failed')
                - progress_pct: Progress percentage (0-100)
                - download_url: Download URL if ready
                - expires_at: Expiration timestamp if ready
                - size_mb: File size in MB if ready
                - error: Error message if failed
                - created_at: Job creation timestamp
        """
        # Retrieve from memory (replace with database query in production)
        export_job = _export_jobs.get(export_id)
        
        if not export_job:
            return None
        
        # Validate ownership
        if export_job['user_id'] != user_id:
            return None
        
        return {
            'export_id': str(export_job['export_id']),
            'status': export_job['status'],
            'progress_pct': export_job['progress_pct'],
            'download_url': export_job['download_url'],
            'expires_at': export_job['expires_at'].isoformat() if export_job['expires_at'] else None,
            'size_mb': export_job['size_mb'],
            'error': export_job['error'],
            'created_at': export_job['created_at'].isoformat()
        }
    
    async def generate_export_package(
        self,
        export_id: UUID
    ) -> None:
        """
        Background task to generate the export package.
        
        This method should be called as a background task after create_export().
        It collects all requested data, packages it, and updates the export job
        status with the download URL.
        
        Args:
            export_id: ID of the export job to process
            
        Raises:
            ValueError: If export job not found
            Exception: If export generation fails
        """
        # Retrieve export job
        export_job = _export_jobs.get(export_id)
        
        if not export_job:
            raise ValueError(f"Export job {export_id} not found")
        
        try:
            user_id = export_job['user_id']
            include = export_job['include']
            format = export_job['format']
            
            # Update progress: Starting data collection
            export_job['progress_pct'] = 10.0
            
            # Collect user data
            user_data = await self._collect_user_data(user_id, include)
            
            # Update progress: Data collected
            export_job['progress_pct'] = 60.0
            
            # Package data
            if format == 'zip':
                file_data, size_bytes = await self._create_zip_archive(user_data)
            else:  # json
                file_data = json.dumps(user_data, indent=2, default=str).encode('utf-8')
                size_bytes = len(file_data)
            
            # Update progress: Package created
            export_job['progress_pct'] = 80.0
            
            # In production, upload to storage (Supabase Storage)
            # For now, we'll simulate with a placeholder URL
            # storage_client = StorageClient()
            # download_url = await storage_client.upload_file(
            #     bucket='exports',
            #     file_name=f'export_{export_id}.{format}',
            #     file_data=file_data
            # )
            
            # Placeholder download URL (replace with actual storage upload)
            download_url = f"https://storage.example.com/exports/export_{export_id}.{format}"
            
            # Calculate expiration (24 hours from now by default)
            expiry_hours = int(os.getenv('EXPORT_EXPIRY_HOURS', '24'))
            expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
            
            # Update export job with success
            export_job['status'] = 'ready'
            export_job['progress_pct'] = 100.0
            export_job['download_url'] = download_url
            export_job['expires_at'] = expires_at
            export_job['size_mb'] = round(size_bytes / (1024 * 1024), 2)
            
        except Exception as e:
            # Update export job with failure
            export_job['status'] = 'failed'
            export_job['error'] = str(e)
            raise
    
    async def _collect_user_data(
        self,
        user_id: UUID,
        include: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Collect all requested user data from the database.
        
        Args:
            user_id: ID of the user
            include: Dictionary specifying what data to include
            
        Returns:
            Dictionary with all collected data organized by category
        """
        data = {
            'export_metadata': {
                'user_id': str(user_id),
                'exported_at': datetime.utcnow().isoformat(),
                'version': '1.0'
            }
        }
        
        # Collect agents
        if include.get('agents', True):
            agents_result = await self.db.execute(
                select(Agent)
                .where(Agent.user_id == user_id)
                .order_by(Agent.created_at.desc())
            )
            agents = agents_result.scalars().all()
            
            data['agents'] = [
                {
                    'id': str(agent.id),
                    'name': agent.name,
                    'mode': agent.mode,
                    'model': agent.model,
                    'indicators': agent.indicators,
                    'custom_indicators': agent.custom_indicators,
                    'strategy_prompt': agent.strategy_prompt,
                    'tests_run': agent.tests_run,
                    'best_pnl': float(agent.best_pnl) if agent.best_pnl else None,
                    'total_profitable_tests': agent.total_profitable_tests,
                    'avg_win_rate': float(agent.avg_win_rate) if agent.avg_win_rate else None,
                    'avg_drawdown': float(agent.avg_drawdown) if agent.avg_drawdown else None,
                    'is_archived': agent.is_archived,
                    'created_at': agent.created_at.isoformat(),
                    'updated_at': agent.updated_at.isoformat()
                }
                for agent in agents
            ]
        
        # Collect test results
        if include.get('results', True):
            results_result = await self.db.execute(
                select(TestResult)
                .options(joinedload(TestResult.agent))
                .where(TestResult.user_id == user_id)
                .order_by(TestResult.created_at.desc())
            )
            results = results_result.scalars().all()
            
            data['test_results'] = [
                {
                    'id': str(result.id),
                    'agent_id': str(result.agent_id),
                    'agent_name': result.agent.name,
                    'type': result.type,
                    'asset': result.asset,
                    'mode': result.mode,
                    'timeframe': result.timeframe,
                    'start_date': result.start_date.isoformat(),
                    'end_date': result.end_date.isoformat(),
                    'duration_seconds': result.duration_seconds,
                    'duration_display': result.duration_display,
                    'starting_capital': float(result.starting_capital),
                    'ending_capital': float(result.ending_capital),
                    'total_pnl_amount': float(result.total_pnl_amount),
                    'total_pnl_pct': float(result.total_pnl_pct),
                    'total_trades': result.total_trades,
                    'winning_trades': result.winning_trades,
                    'losing_trades': result.losing_trades,
                    'win_rate': float(result.win_rate),
                    'max_drawdown_pct': float(result.max_drawdown_pct) if result.max_drawdown_pct else None,
                    'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else None,
                    'profit_factor': float(result.profit_factor) if result.profit_factor else None,
                    'avg_trade_pnl': float(result.avg_trade_pnl) if result.avg_trade_pnl else None,
                    'best_trade_pnl': float(result.best_trade_pnl) if result.best_trade_pnl else None,
                    'worst_trade_pnl': float(result.worst_trade_pnl) if result.worst_trade_pnl else None,
                    'avg_holding_time_seconds': result.avg_holding_time_seconds,
                    'avg_holding_time_display': result.avg_holding_time_display,
                    'equity_curve': result.equity_curve,
                    'ai_summary': result.ai_summary,
                    'is_profitable': result.is_profitable,
                    'created_at': result.created_at.isoformat()
                }
                for result in results
            ]
        
        # Collect trade history
        if include.get('trades', True):
            # Get all test sessions for the user
            sessions_result = await self.db.execute(
                select(TestSession.id)
                .where(TestSession.user_id == user_id)
            )
            session_ids = [row[0] for row in sessions_result.all()]
            
            if session_ids:
                trades_result = await self.db.execute(
                    select(Trade)
                    .where(Trade.session_id.in_(session_ids))
                    .order_by(Trade.entry_time.desc())
                )
                trades = trades_result.scalars().all()
                
                data['trades'] = [
                    {
                        'id': str(trade.id),
                        'session_id': str(trade.session_id),
                        'trade_number': trade.trade_number,
                        'type': trade.type,
                        'entry_price': float(trade.entry_price),
                        'entry_time': trade.entry_time.isoformat(),
                        'entry_candle': trade.entry_candle,
                        'entry_reasoning': trade.entry_reasoning if include.get('reasoning_traces', False) else None,
                        'exit_price': float(trade.exit_price) if trade.exit_price else None,
                        'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                        'exit_candle': trade.exit_candle,
                        'exit_type': trade.exit_type,
                        'exit_reasoning': trade.exit_reasoning if include.get('reasoning_traces', False) else None,
                        'size': float(trade.size),
                        'leverage': trade.leverage,
                        'pnl_amount': float(trade.pnl_amount) if trade.pnl_amount else None,
                        'pnl_pct': float(trade.pnl_pct) if trade.pnl_pct else None,
                        'stop_loss': float(trade.stop_loss) if trade.stop_loss else None,
                        'take_profit': float(trade.take_profit) if trade.take_profit else None,
                        'created_at': trade.created_at.isoformat()
                    }
                    for trade in trades
                ]
            else:
                data['trades'] = []
        
        # Collect user settings
        if include.get('settings', True):
            settings_result = await self.db.execute(
                select(UserSettings)
                .where(UserSettings.user_id == user_id)
            )
            settings = settings_result.scalar_one_or_none()
            
            if settings:
                data['settings'] = {
                    'theme': settings.theme,
                    'accent_color': settings.accent_color,
                    'sidebar_collapsed': settings.sidebar_collapsed,
                    'chart_grid_lines': settings.chart_grid_lines,
                    'chart_crosshair': settings.chart_crosshair,
                    'chart_candle_colors': settings.chart_candle_colors,
                    'email_notifications': settings.email_notifications,
                    'inapp_notifications': settings.inapp_notifications,
                    'default_asset': settings.default_asset,
                    'default_timeframe': settings.default_timeframe,
                    'default_capital': float(settings.default_capital),
                    'default_playback_speed': settings.default_playback_speed,
                    'safety_mode_default': settings.safety_mode_default,
                    'allow_leverage_default': settings.allow_leverage_default,
                    'max_position_size_pct': settings.max_position_size_pct,
                    'max_leverage': settings.max_leverage,
                    'max_loss_per_trade_pct': float(settings.max_loss_per_trade_pct),
                    'max_daily_loss_pct': float(settings.max_daily_loss_pct),
                    'max_total_drawdown_pct': float(settings.max_total_drawdown_pct)
                }
            else:
                data['settings'] = None
        
        return data
    
    async def _create_zip_archive(
        self,
        user_data: Dict[str, Any]
    ) -> tuple[bytes, int]:
        """
        Create a ZIP archive containing the user data.
        
        Creates a ZIP file with:
        - data.json: All user data in JSON format
        - README.txt: Information about the export
        
        Args:
            user_data: Dictionary with all collected user data
            
        Returns:
            Tuple of (zip_bytes, size_in_bytes)
        """
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add data.json
            data_json = json.dumps(user_data, indent=2, default=str)
            zip_file.writestr('data.json', data_json)
            
            # Add README.txt
            readme_content = f"""AlphaLab Data Export
=====================

Export Date: {user_data['export_metadata']['exported_at']}
User ID: {user_data['export_metadata']['user_id']}
Version: {user_data['export_metadata']['version']}

Contents:
---------
- data.json: All your AlphaLab data in JSON format

Data Included:
--------------
"""
            if 'agents' in user_data:
                readme_content += f"- Agents: {len(user_data['agents'])} agent configurations\n"
            if 'test_results' in user_data:
                readme_content += f"- Test Results: {len(user_data['test_results'])} completed tests\n"
            if 'trades' in user_data:
                readme_content += f"- Trades: {len(user_data['trades'])} trade records\n"
            if 'settings' in user_data and user_data['settings']:
                readme_content += "- Settings: User preferences and configuration\n"
            
            readme_content += """
How to Use:
-----------
1. Extract this ZIP file to a folder
2. Open data.json in any text editor or JSON viewer
3. Import into other tools or analyze as needed

For questions or support, visit: https://alphalab.io/support
"""
            
            zip_file.writestr('README.txt', readme_content)
        
        # Get ZIP bytes
        zip_bytes = zip_buffer.getvalue()
        size_bytes = len(zip_bytes)
        
        return zip_bytes, size_bytes

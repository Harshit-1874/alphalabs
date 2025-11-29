"""
WebSocket Route Handlers.

Purpose:
    FastAPI route handlers for WebSocket endpoints.
    Handles connection lifecycle and message routing.
"""

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Optional
import logging

from .manager import websocket_manager
from .events import create_error_event

logger = logging.getLogger(__name__)


async def handle_backtest_websocket(
    websocket: WebSocket,
    session_id: str,
    # user_id: str = Depends(get_current_user)  # TODO: Add auth when routes are integrated
):
    """
    Handle WebSocket connection for backtest session.
    
    Args:
        websocket: The WebSocket connection
        session_id: The backtest session ID
    """
    connection_id = None
    
    try:
        # TODO: Validate session exists and user has access
        # For now, accept all connections
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(websocket, session_id)
        
        logger.info(f"Backtest WebSocket connected: session={session_id}, conn={connection_id}")
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Receive messages from client (e.g., pause/resume commands)
                data = await websocket.receive_text()
                logger.debug(f"Received from client {connection_id}: {data}")
                
                # TODO: Handle client commands (pause, resume, stop)
                # For now, just acknowledge receipt
                
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {connection_id}")
                break
                
    except Exception as e:
        logger.error(f"Error in backtest WebSocket handler: {e}")
        if connection_id:
            error_event = create_error_event(
                error_code="WEBSOCKET_ERROR",
                message=str(e)
            )
            await websocket_manager.send_to_connection(connection_id, error_event)
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


async def handle_forward_websocket(
    websocket: WebSocket,
    session_id: str,
    # user_id: str = Depends(get_current_user)  # TODO: Add auth when routes are integrated
):
    """
    Handle WebSocket connection for forward test session.
    
    Args:
        websocket: The WebSocket connection
        session_id: The forward test session ID
    """
    connection_id = None
    
    try:
        # TODO: Validate session exists and user has access
        # For now, accept all connections
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(websocket, session_id)
        
        logger.info(f"Forward test WebSocket connected: session={session_id}, conn={connection_id}")
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Receive messages from client (e.g., stop commands)
                data = await websocket.receive_text()
                logger.debug(f"Received from client {connection_id}: {data}")
                
                # TODO: Handle client commands (stop)
                # For now, just acknowledge receipt
                
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {connection_id}")
                break
                
    except Exception as e:
        logger.error(f"Error in forward test WebSocket handler: {e}")
        if connection_id:
            error_event = create_error_event(
                error_code="WEBSOCKET_ERROR",
                message=str(e)
            )
            await websocket_manager.send_to_connection(connection_id, error_event)
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)

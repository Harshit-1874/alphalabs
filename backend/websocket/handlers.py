"""
WebSocket Route Handlers.

Purpose:
    FastAPI route handlers for WebSocket endpoints.
    Handles connection lifecycle and message routing.
"""

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Optional
import logging
import jwt

from .manager import websocket_manager
from .events import create_error_event

logger = logging.getLogger(__name__)


async def authenticate_websocket(token: Optional[str]) -> Optional[str]:
    """
    Authenticate WebSocket connection using JWT token.
    
    Args:
        token: JWT token from query parameter
        
    Returns:
        clerk_user_id if authenticated, None otherwise
    """
    if not token:
        logger.warning("WebSocket connection attempted without token")
        return None
    
    try:
        # Decode token without verification (same as HTTP auth fallback)
        # In production, this should verify the signature
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        # Extract user ID from token
        clerk_user_id = decoded.get("sub") or decoded.get("userId") or decoded.get("id")
        
        if not clerk_user_id:
            logger.warning("Token missing user ID")
            return None
            
        return clerk_user_id
        
    except jwt.DecodeError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error authenticating WebSocket: {e}")
        return None


async def handle_backtest_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    Handle WebSocket connection for backtest session.
    
    Args:
        websocket: The WebSocket connection
        session_id: The backtest session ID
        token: JWT token for authentication (query parameter)
    """
    connection_id = None
    
    try:
        # Authenticate the connection
        clerk_user_id = await authenticate_websocket(token)
        
        if not clerk_user_id:
            await websocket.close(code=1008, reason="Authentication required")
            logger.warning(f"Rejected unauthenticated backtest WebSocket: session={session_id}")
            return
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(websocket, session_id)
        
        logger.info(
            f"Backtest WebSocket connected: session={session_id}, "
            f"conn={connection_id}, user={clerk_user_id}"
        )
        
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
    token: Optional[str] = Query(None)
):
    """
    Handle WebSocket connection for forward test session.
    
    Args:
        websocket: The WebSocket connection
        session_id: The forward test session ID
        token: JWT token for authentication (query parameter)
    """
    connection_id = None
    
    try:
        # Authenticate the connection
        clerk_user_id = await authenticate_websocket(token)
        
        if not clerk_user_id:
            await websocket.close(code=1008, reason="Authentication required")
            logger.warning(f"Rejected unauthenticated forward test WebSocket: session={session_id}")
            return
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(websocket, session_id)
        
        logger.info(
            f"Forward test WebSocket connected: session={session_id}, "
            f"conn={connection_id}, user={clerk_user_id}"
        )
        
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

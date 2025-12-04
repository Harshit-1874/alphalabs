"""
WebSocket Route Handlers.

Purpose:
    FastAPI route handlers for WebSocket endpoints.
    Handles connection lifecycle and message routing.
"""

import json
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy import select

from auth import verify_clerk_token, get_user_id_from_token
from database import async_session_maker
from models.arena import TestSession
from models.user import User
from websocket.events import create_error_event, create_heartbeat_event, Event
from websocket.manager import websocket_manager
from services.trading.engine_factory import get_backtest_engine, get_forward_engine

logger = logging.getLogger(__name__)


async def authenticate_websocket(token: Optional[str]) -> Optional[str]:
    """
    Authenticate WebSocket connection using Clerk token.
    """
    if not token:
        logger.warning("WebSocket connection attempted without token")
        return None
    
    try:
        payload = await verify_clerk_token(f"Bearer {token}")
        return get_user_id_from_token(payload)
    except HTTPException as exc:
        logger.warning(f"WebSocket token verification failed: {exc.detail}")
    except Exception as exc:
        logger.error(f"Error authenticating WebSocket: {exc}")
    return None


async def _load_authorized_session(session_id: str, clerk_user_id: str) -> Optional[TestSession]:
    """
    Ensure the requested session exists and belongs to the connected user.
    
    Args:
        session_id: Test session UUID
        clerk_user_id: Clerk user ID (string, not UUID)
    """
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        logger.warning("Invalid session ID supplied to WebSocket handler")
        return None
    
    async with async_session_maker() as db:
        # First, find the User by clerk_id to get the UUID
        user_result = await db.execute(
            select(User).where(User.clerk_id == clerk_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for clerk_id: {clerk_user_id}")
            return None
        
        # Now query the session using the User's UUID
        result = await db.execute(
            select(TestSession).where(
                TestSession.id == session_uuid,
                TestSession.user_id == user.id
            )
        )
        return result.scalar_one_or_none()


async def _send_error(connection_id: Optional[str], error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
    if not connection_id:
        return
    event = create_error_event(error_code=error_code, message=message, details=details or {})
    await websocket_manager.send_to_connection(connection_id, event)


async def _send_ack(connection_id: Optional[str], action: str, payload: Optional[Dict[str, Any]] = None):
    if not connection_id:
        return
    ack_event = Event(
        type="command_ack",
        data={
            "action": action,
            **(payload or {})
        }
    )
    await websocket_manager.send_to_connection(connection_id, ack_event)


async def _handle_backtest_command(connection_id: Optional[str], session_id: str, payload: Dict[str, Any]):
    action = (payload.get("action") or "").lower()
    if not action:
        await _send_error(connection_id, "INVALID_COMMAND", "Missing 'action' field in command.")
        return
    
    engine = get_backtest_engine()
    
    try:
        if action == "pause":
            await engine.pause_backtest(session_id)
            await _send_ack(connection_id, action)
        elif action == "resume":
            await engine.resume_backtest(session_id)
            await _send_ack(connection_id, action)
        elif action == "stop":
            close_position = bool(payload.get("close_position", True))
            result_id = await engine.stop_backtest(session_id, close_position=close_position)
            await _send_ack(connection_id, action, {"result_id": result_id})
        elif action == "ping":
            if connection_id:
                await websocket_manager.send_to_connection(connection_id, create_heartbeat_event())
        else:
            await _send_error(connection_id, "UNKNOWN_COMMAND", f"Unsupported action '{action}'.")
    except Exception as exc:
        logger.exception("Error handling backtest WebSocket command")
        await _send_error(connection_id, "COMMAND_FAILED", str(exc))


async def _handle_forward_command(connection_id: Optional[str], session_id: str, payload: Dict[str, Any]):
    action = (payload.get("action") or "").lower()
    if not action:
        await _send_error(connection_id, "INVALID_COMMAND", "Missing 'action' field in command.")
        return
    
    engine = get_forward_engine()
    
    try:
        if action == "stop":
            close_position = bool(payload.get("close_position", True))
            result_id, position_closed = await engine.stop_forward_test(session_id, close_position=close_position)
            await _send_ack(
                connection_id,
                action,
                {
                    "result_id": result_id,
                    "position_closed": position_closed
                }
            )
        elif action == "ping":
            if connection_id:
                await websocket_manager.send_to_connection(connection_id, create_heartbeat_event())
        else:
            await _send_error(connection_id, "UNKNOWN_COMMAND", f"Unsupported action '{action}'.")
    except Exception as exc:
        logger.exception("Error handling forward WebSocket command")
        await _send_error(connection_id, "COMMAND_FAILED", str(exc))


async def _handle_client_message(session_type: str, connection_id: Optional[str], session_id: str, raw_message: str):
    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError:
        await _send_error(connection_id, "INVALID_MESSAGE", "Messages must be valid JSON.")
        return
    
    if not isinstance(payload, dict):
        await _send_error(connection_id, "INVALID_MESSAGE", "Message payload must be a JSON object.")
        return
    
    if session_type == "backtest":
        await _handle_backtest_command(connection_id, session_id, payload)
    else:
        await _handle_forward_command(connection_id, session_id, payload)


async def handle_backtest_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    Handle WebSocket connection for backtest session.
    """
    connection_id = None
    
    try:
        clerk_user_id = await authenticate_websocket(token)
        if not clerk_user_id:
            await websocket.close(code=1008, reason="Authentication required")
            logger.warning(f"Rejected unauthenticated backtest WebSocket: session={session_id}")
            return
        
        session_record = await _load_authorized_session(session_id, clerk_user_id)
        if not session_record or session_record.type != "backtest":
            await websocket.close(code=1008, reason="Unauthorized session access")
            logger.warning("Rejected backtest WebSocket due to unauthorized session access")
            return
        
        connection_id = await websocket_manager.connect(websocket, session_id)
        
        logger.info(
            f"Backtest WebSocket connected: session={session_id}, conn={connection_id}, user={clerk_user_id}"
        )
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received from client {connection_id}: {data}")
                await _handle_client_message("backtest", connection_id, session_id, data)
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {connection_id}")
                break
                
    except Exception as exc:
        logger.error(f"Error in backtest WebSocket handler: {exc}")
        await _send_error(connection_id, "WEBSOCKET_ERROR", str(exc))
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
    """
    connection_id = None
    
    try:
        clerk_user_id = await authenticate_websocket(token)
        if not clerk_user_id:
            await websocket.close(code=1008, reason="Authentication required")
            logger.warning(f"Rejected unauthenticated forward test WebSocket: session={session_id}")
            return
        
        session_record = await _load_authorized_session(session_id, clerk_user_id)
        if not session_record or session_record.type != "forward":
            await websocket.close(code=1008, reason="Unauthorized session access")
            logger.warning("Rejected forward WebSocket due to unauthorized session access")
            return
        
        connection_id = await websocket_manager.connect(websocket, session_id)
        
        logger.info(
            f"Forward test WebSocket connected: session={session_id}, conn={connection_id}, user={clerk_user_id}"
        )
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received from client {connection_id}: {data}")
                await _handle_client_message("forward", connection_id, session_id, data)
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {connection_id}")
                break
                
    except Exception as exc:
        logger.error(f"Error in forward test WebSocket handler: {exc}")
        await _send_error(connection_id, "WEBSOCKET_ERROR", str(exc))
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)

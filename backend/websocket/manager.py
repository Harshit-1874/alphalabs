"""
WebSocket Manager for AlphaLab Trading Engine.

Purpose:
    Manages WebSocket connections from frontend clients and broadcasts
    real-time events during backtests and forward tests.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from fastapi import WebSocket, WebSocketDisconnect
import logging

if TYPE_CHECKING:
    from .events import Event

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and event broadcasting.
    
    Supports:
    - Multiple connections per session (multi-tab support)
    - Connection lifecycle management
    - Event broadcasting to session or individual connections
    - Heartbeat for connection health
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        # Store active WebSocket connections by connection_id
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Map session_id to list of connection_ids
        self.session_connections: Dict[str, Set[str]] = {}
        
        # Store connection metadata
        self.connection_metadata: Dict[str, Dict] = {}
        
        # Heartbeat task tracking
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("WebSocketManager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str) -> str:
        """
        Accept a WebSocket connection from frontend.
        
        Args:
            websocket: The WebSocket connection object
            session_id: The test session ID this connection is for
            
        Returns:
            connection_id: Unique identifier for this connection
        """
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Store the connection
        self.active_connections[connection_id] = websocket
        
        # Add to session mapping
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "session_id": session_id,
            "connected_at": datetime.utcnow(),
            "last_heartbeat": datetime.utcnow()
        }
        
        # Start heartbeat task for this connection
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(connection_id)
        )
        self.heartbeat_tasks[connection_id] = heartbeat_task
        
        logger.info(
            f"WebSocket connected: connection_id={connection_id}, "
            f"session_id={session_id}, "
            f"total_connections={len(self.active_connections)}"
        )
        
        return connection_id
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and clean up a WebSocket connection.
        
        Args:
            connection_id: The connection to disconnect
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Attempted to disconnect unknown connection: {connection_id}")
            return
        
        # Get session_id before cleanup
        metadata = self.connection_metadata.get(connection_id, {})
        session_id = metadata.get("session_id")
        
        # Cancel heartbeat task if exists
        if connection_id in self.heartbeat_tasks:
            self.heartbeat_tasks[connection_id].cancel()
            del self.heartbeat_tasks[connection_id]
        
        # Remove from active connections
        websocket = self.active_connections.pop(connection_id, None)
        
        # Close the WebSocket if still open
        if websocket:
            try:
                # Check if WebSocket is still open before closing
                # WebSocket has a 'client_state' attribute that indicates connection state
                if hasattr(websocket, 'client_state') and websocket.client_state.name != 'DISCONNECTED':
                    await websocket.close()
            except Exception as e:
                # Ignore errors if connection is already closed
                if "already closed" not in str(e).lower() and "websocket.close" not in str(e):
                    logger.warning(f"Error closing WebSocket: {e}")
        
        # Remove from session mapping
        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            
            # Clean up empty session entries
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        # Remove metadata
        self.connection_metadata.pop(connection_id, None)
        
        logger.info(
            f"WebSocket disconnected: connection_id={connection_id}, "
            f"session_id={session_id}, "
            f"remaining_connections={len(self.active_connections)}"
        )
    
    def get_session_connections(self, session_id: str) -> List[str]:
        """
        Get all connection IDs for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of connection IDs
        """
        return list(self.session_connections.get(session_id, set()))
    
    def get_connection_count(self, session_id: Optional[str] = None) -> int:
        """
        Get the number of active connections.
        
        Args:
            session_id: Optional session ID to count connections for
            
        Returns:
            Number of active connections
        """
        if session_id:
            return len(self.session_connections.get(session_id, set()))
        return len(self.active_connections)
    
    def is_connected(self, connection_id: str) -> bool:
        """
        Check if a connection is active.
        
        Args:
            connection_id: The connection ID to check
            
        Returns:
            True if connected, False otherwise
        """
        return connection_id in self.active_connections
    
    async def send_to_connection(self, connection_id: str, event: "Event") -> bool:
        """
        Send an event to a specific connection.
        
        Args:
            connection_id: The connection to send to
            event: The event to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Cannot send to unknown connection: {connection_id}")
            return False
        
        websocket = self.active_connections[connection_id]
        
        try:
            await websocket.send_text(event.to_json())
            logger.debug(f"Sent event {event.type} to connection {connection_id}")
            return True
        except WebSocketDisconnect:
            logger.info(f"Connection {connection_id} disconnected during send")
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_session(self, session_id: str, event: "Event") -> int:
        """
        Broadcast an event to all connections in a session.
        
        Args:
            session_id: The session to broadcast to
            event: The event to broadcast
            
        Returns:
            Number of connections successfully sent to
        """
        if session_id not in self.session_connections:
            logger.debug(f"No connections for session {session_id}")
            return 0
        
        connection_ids = list(self.session_connections[session_id])
        successful_sends = 0
        
        # Send to all connections concurrently
        send_tasks = [
            self.send_to_connection(conn_id, event)
            for conn_id in connection_ids
        ]
        
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, bool) and result:
                successful_sends += 1
        
        logger.debug(
            f"Broadcast event {event.type} to session {session_id}: "
            f"{successful_sends}/{len(connection_ids)} successful"
        )
        
        return successful_sends
    
    async def broadcast_to_all(self, event: "Event") -> int:
        """
        Broadcast an event to all active connections.
        
        Args:
            event: The event to broadcast
            
        Returns:
            Number of connections successfully sent to
        """
        connection_ids = list(self.active_connections.keys())
        successful_sends = 0
        
        # Send to all connections concurrently
        send_tasks = [
            self.send_to_connection(conn_id, event)
            for conn_id in connection_ids
        ]
        
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, bool) and result:
                successful_sends += 1
        
        logger.debug(
            f"Broadcast event {event.type} to all: "
            f"{successful_sends}/{len(connection_ids)} successful"
        )
        
        return successful_sends
    
    async def _heartbeat_loop(self, connection_id: str) -> None:
        """
        Send periodic heartbeat messages to keep connection alive.
        
        Args:
            connection_id: The connection to send heartbeats to
        """
        from .events import create_heartbeat_event
        
        try:
            while connection_id in self.active_connections:
                # Wait 30 seconds between heartbeats
                await asyncio.sleep(30)
                
                # Check if connection still exists
                if connection_id not in self.active_connections:
                    break
                
                # Send heartbeat
                heartbeat_event = create_heartbeat_event()
                success = await self.send_to_connection(connection_id, heartbeat_event)
                
                if success:
                    # Update last heartbeat time
                    if connection_id in self.connection_metadata:
                        self.connection_metadata[connection_id]["last_heartbeat"] = datetime.utcnow()
                    logger.debug(f"Heartbeat sent to connection {connection_id}")
                else:
                    # Connection failed, exit loop
                    logger.warning(f"Heartbeat failed for connection {connection_id}")
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat loop cancelled for connection {connection_id}")
        except Exception as e:
            logger.error(f"Error in heartbeat loop for connection {connection_id}: {e}")
    
    def get_connection_metadata(self, connection_id: str) -> Optional[Dict]:
        """
        Get metadata for a connection.
        
        Args:
            connection_id: The connection ID
            
        Returns:
            Connection metadata or None if not found
        """
        return self.connection_metadata.get(connection_id)
    
    async def cleanup_stale_connections(self, max_age_seconds: int = 300) -> int:
        """
        Clean up connections that haven't received a heartbeat response.
        
        Args:
            max_age_seconds: Maximum age in seconds before considering stale
            
        Returns:
            Number of connections cleaned up
        """
        now = datetime.utcnow()
        stale_connections = []
        
        for connection_id, metadata in self.connection_metadata.items():
            last_heartbeat = metadata.get("last_heartbeat")
            if last_heartbeat:
                age = (now - last_heartbeat).total_seconds()
                if age > max_age_seconds:
                    stale_connections.append(connection_id)
        
        # Disconnect stale connections
        for connection_id in stale_connections:
            logger.info(f"Cleaning up stale connection: {connection_id}")
            await self.disconnect(connection_id)
        
        return len(stale_connections)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()

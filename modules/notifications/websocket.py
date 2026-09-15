from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])

class ConnectionManager:
    """Manages active WebSocket connections for notifications and live feeds."""
    def __init__(self):
        # Maps user_id -> set of active WebSockets
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # Set of active admin connection sockets
        self.admin_connections: Set[WebSocket] = set()
        # Maps project_id -> set of active WebSockets
        self.project_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_type: str, target_id: str | None = None):
        """Register a new connection."""
        await websocket.accept()
        
        if client_type == "admin":
            self.admin_connections.add(websocket)
            logger.info("Admin WebSocket connected.")
        elif client_type == "user" and target_id:
            if target_id not in self.user_connections:
                self.user_connections[target_id] = set()
            self.user_connections[target_id].add(websocket)
            logger.info(f"User '{target_id}' WebSocket connected.")
        elif client_type == "project" and target_id:
            if target_id not in self.project_connections:
                self.project_connections[target_id] = set()
            self.project_connections[target_id].add(websocket)
            logger.info(f"Project '{target_id}' WebSocket connected.")

    def disconnect(self, websocket: WebSocket, client_type: str, target_id: str | None = None):
        """Remove a closed connection."""
        if client_type == "admin":
            if websocket in self.admin_connections:
                self.admin_connections.remove(websocket)
                logger.info("Admin WebSocket disconnected.")
        elif client_type == "user" and target_id:
            if target_id in self.user_connections and websocket in self.user_connections[target_id]:
                self.user_connections[target_id].remove(websocket)
                if not self.user_connections[target_id]:
                    del self.user_connections[target_id]
                logger.info(f"User '{target_id}' WebSocket disconnected.")
        elif client_type == "project" and target_id:
            if target_id in self.project_connections and websocket in self.project_connections[target_id]:
                self.project_connections[target_id].remove(websocket)
                if not self.project_connections[target_id]:
                    del self.project_connections[target_id]
                logger.info(f"Project '{target_id}' WebSocket disconnected.")

    async def send_to_user(self, user_id: str, message: dict):
        """Send a notification to a specific user's active sockets."""
        payload = json.dumps(message)
        sockets = self.user_connections.get(user_id, set())
        dead_sockets = set()
        
        for ws in list(sockets):
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.add(ws)
                
        for ws in dead_sockets:
            self.disconnect(ws, "user", user_id)

    async def broadcast_to_admins(self, message: dict):
        """Send an activity or metric update to all active admin panels."""
        payload = json.dumps(message)
        dead_sockets = set()
        
        for ws in list(self.admin_connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.add(ws)
                
        for ws in dead_sockets:
            self.disconnect(ws, "admin")

    async def broadcast_to_project(self, project_id: str, message: dict):
        """Send an agent update to developers watching a specific project build."""
        payload = json.dumps(message)
        sockets = self.project_connections.get(project_id, set())
        dead_sockets = set()
        
        for ws in list(sockets):
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.add(ws)
                
        for ws in dead_sockets:
            self.disconnect(ws, "project", project_id)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_type: str = Query("user"), # admin, user, project
    target_id: str | None = Query(None), # user_id or project_id
    token: str | None = Query(None) # Option for auth checks
):
    """WebSocket gate for real-time events and streaming."""
    # Authenticate token here if supplied
    if token:
        from modules.auth.service import verify_token
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    await manager.connect(websocket, client_type, target_id)
    
    try:
        # Keep connection open and listen for ping/pong or queries
        while True:
            data = await websocket.receive_text()
            # Parse query if needed
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_type, target_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_type, target_id)

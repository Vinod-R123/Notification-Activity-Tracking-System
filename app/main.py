from fastapi import FastAPI, WebSocket, Query, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.config import settings
from app.routers import auth, project, task, log
from app.security import decode_access_token
from app.services.websocket import manager

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Notification & Activity Tracking Project Management API with Audit Trails",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(project.router)
app.include_router(task.router)
app.include_router(log.router)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Authenticate token
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Register the WebSocket connection
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Maintain connection, handle incoming client heartbeats or dummy pings
            await websocket.receive_text()
    except Exception:
        # Client disconnected or error occurred
        pass
    finally:
        manager.disconnect(websocket, user_id)

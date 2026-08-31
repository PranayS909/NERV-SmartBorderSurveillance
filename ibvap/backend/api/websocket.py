from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):

    await manager.connect(websocket)

    print("WebSocket client connected")

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket client disconnected")
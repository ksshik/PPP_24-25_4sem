import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, WebSocket, Header
import uvicorn
from app.api.endpoints import auth, media 
from app.websocket.handlers import websocket_endpoint

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(media.router, prefix="/image", tags=["image"])

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        await websocket.close(code=1008, reason="Invalid or missing Authorization header")
        return
    token = authorization[len("Bearer "):]
    await websocket_endpoint(websocket, token)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8185,
        reload=True
    )
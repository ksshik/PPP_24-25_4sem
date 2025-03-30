import os  
import sys  

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Добавление пути к корневой папке

from fastapi import FastAPI, WebSocket  
import uvicorn  
from app.api.endpoints import auth, media 

app = FastAPI() 
app.include_router(auth.router, prefix="/auth", tags=["auth"])  # Подключение роутеров
app.include_router(media.router, prefix="/image", tags=["image"])  

@app.websocket("/ws")  
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # Подключение
    await websocket.send_text("WebSocket connected")  
    await websocket.close()  # Закрываем соединение

if __name__ == "__main__":  # Запуск приложения
    uvicorn.run( 
        "app.main:app",
        host="127.0.0.1",
        port=8185,
        reload=True,  
        ws="wsproto")

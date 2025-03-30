from fastapi import WebSocket  
from app.services.image_processing import binarize_image  

async def websocket_endpoint(websocket: WebSocket):  # определение асинхронного эндпоинта WebSocket
    await websocket.accept()  
    try:
        while True:  # Бесконечный цикл для постоянного приема данных
            data = await websocket.receive_json()  
            image = data.get("image")  # Извлекаем изображение 
            algorithm = data.get("algorithm", "niblack") 
            binarized_image = binarize_image(image, algorithm)  # Бинаризация
            await websocket.send_json({"binarized_image": binarized_image})  
    except Exception as e:  
        await websocket.close()  

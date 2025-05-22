import logging
import json
from fastapi import WebSocket
from app.celery_config import celery_app
from app.tasks import process_image_task
from celery.result import AsyncResult
import asyncio
from starlette.websockets import WebSocketDisconnect  

logger = logging.getLogger(__name__)
active_connections = {}

async def websocket_endpoint(websocket: WebSocket, token: str):
    logger.info(f"WebSocket connection attempt with token: {token}")
    try:
        await websocket.accept()
        logger.info("WebSocket accepted")
        active_connections[token] = websocket
        await websocket.send_json({"message": "WebSocket connected"})
        
        while True:
            logger.info("Waiting for message...")
            data = await websocket.receive_json()
            logger.info(f"Received message: {data}")
            action = data.get("action")
            
            if action == "binarize_image":
                image = data.get("image")
                algorithm = data.get("algorithm", "niblack")
                logger.info(f"Processing binarize_image with algorithm: {algorithm}, image length: {len(image)}")
                
                from app.tasks import process_image_task
                task = process_image_task.delay(image, algorithm, token=token)
                logger.info(f"Task sent to Celery: {task.id}")
                
                start_message = {
                    "status": "STARTED",
                    "task_id": task.id,
                    "algorithm": algorithm
                }
                logger.info(f"Sending message: {json.dumps(start_message)}")
                await websocket.send_json(start_message)
                
                asyncio.create_task(monitor_task_progress(task.id, websocket, token))
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if token in active_connections:
            error_message = {"error": str(e)}
            logger.info(f"Sending message: {json.dumps(error_message)}")
            await active_connections[token].send_json(error_message)
    finally:
        if token in active_connections:
            del active_connections[token]
            try:
                if websocket.client_state != "DISCONNECTED":
                    await websocket.close()
                    logger.info("WebSocket closed")
            except Exception as e:
                logger.warning(f"Error closing WebSocket (ignored): {str(e)}")

async def monitor_task_progress(task_id: str, websocket: WebSocket, token: str):
    result = AsyncResult(task_id, app=celery_app)
    last_progress = -1
    while not result.ready():
        state = result.state
        meta = result.info or {}
        if state == "PROGRESS" and token in active_connections and websocket.client_state != "DISCONNECTED":
            progress = meta.get("progress", 0)
            if progress != last_progress:
                progress_message = {
                    "status": "PROGRESS",
                    "task_id": task_id,
                    "progress": progress
                }
                logger.info(f"Sending message: {json.dumps(progress_message)}")
                try:
                    await active_connections[token].send_json(progress_message)
                    last_progress = progress
                except Exception as e:
                    logger.warning(f"Failed to send PROGRESS message: {str(e)}")
                    break
        await asyncio.sleep(0.5)
    if result.successful() and token in active_connections and websocket.client_state != "DISCONNECTED":
        task_result = result.get()
        completed_message = {
            "status": "COMPLETED",
            "task_id": task_id,
            "binarized_image": task_result.get("binarized_image", "")
        }
        logger.info(f"Sending message: {json.dumps(completed_message)}")
        try:
            await active_connections[token].send_json(completed_message)
        except Exception as e:
            logger.warning(f"Failed to send COMPLETED message: {str(e)}")
    elif token in active_connections and websocket.client_state != "DISCONNECTED":
        error = result.get(propagate=False) or "Unknown error"
        failed_message = {
            "status": "FAILED",
            "task_id": task_id,
            "error": str(error)
        }
        logger.info(f"Sending message: {json.dumps(failed_message)}")
        try:
            await active_connections[token].send_json(failed_message)
        except Exception as e:
            logger.warning(f"Failed to send FAILED message: {str(e)}")
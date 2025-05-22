import argparse
import asyncio
import json
import aiohttp
import base64
import os
import sys
import logging
from aiohttp import ClientWSTimeout
from aioconsole import ainput  # асинхронный ввод

# кастомный асинхронный обработчик логов, тк не работает из-за длинного кода изображения
class AsyncHandler(logging.Handler):
    def __init__(self, filename, stream):
        super().__init__()
        self.filename = filename
        self.stream = stream
        self.file = open(filename, "a", encoding="utf-8")
        self.chunk_size = 1024  # размер части для длинных сообщений

    def emit(self, record):
        try:
            msg = self.format(record)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                self.file.write(msg + "\n")
                self.file.flush()
                self.stream.write(msg + "\n")
                self.stream.flush()
                return

            if len(msg) > self.chunk_size:
                asyncio.create_task(self._async_write_long_message(msg, loop))
            else:
                asyncio.create_task(self._async_write(msg, loop))
        except Exception as e:
            print(f"Error in AsyncHandler: {str(e)}", file=sys.stderr)

    async def _async_write(self, msg, loop):
        try:
            self.file.write(msg + "\n")
            self.file.flush()
            self.stream.write(msg + "\n")
            self.stream.flush()
        except Exception as e:
            print(f"Error writing log: {str(e)}", file=sys.stderr)
        await asyncio.sleep(0.01)  #

    async def _async_write_long_message(self, msg, loop):
        # разбиваем длинное сообщение на части
        for i in range(0, len(msg), self.chunk_size):
            chunk = msg[i:i + self.chunk_size]
            await self._async_write(chunk, loop)
            await asyncio.sleep(0.01)  # задержка между частями

    def close(self):
        self.file.close()
        super().close()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        AsyncHandler("client_output.log", sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8185"
WS_URL = "ws://127.0.0.1:8185/ws"

async def authenticate(email: str, password: str) -> str:
    async with aiohttp.ClientSession() as session:
        login_url = f"{BASE_URL}/auth/login/"
        login_data = {"email": email, "password": password}
        async with session.post(login_url, json=login_data) as response:
            if response.status != 200:
                error = await response.json()
                logger.error(f"Authentication failed: {error['detail']}")
                return None
            data = await response.json()
            token = data["token"]
            logger.info("Authentication successful!")
            return token

async def listen_websocket(websocket, active_tasks):
    logger.info("Starting WebSocket listener...")
    while True:
        try:
            if websocket.closed:
                logger.warning("WebSocket is closed, stopping listener")
                break
            msg = await websocket.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if "status" in data:
                        task_id = data.get("task_id")
                        if task_id:
                            if data["status"] == "STARTED":
                                logger.info(f"Task {task_id} started with algorithm {data.get('algorithm', 'unknown')}")
                                active_tasks[task_id] = {"status": "STARTED"}
                            elif data["status"] == "PROGRESS":
                                progress = data.get("progress")
                                if progress is not None:
                                    logger.info(f"Task {task_id} progress: {progress}%")
                                    active_tasks[task_id]["progress"] = progress
                            elif data["status"] == "COMPLETED":
                                logger.info(f"Task {task_id} completed.")
                                binarized_image = data.get("binarized_image", "No image")
                                logger.info(f"Binarized image base64: {binarized_image}")
                                active_tasks[task_id]["status"] = "COMPLETED"
                                del active_tasks[task_id]
                    elif "error" in data:
                        logger.error(f"Error: {data['error']}")
                        task_id = data.get("task_id")
                        if task_id:
                            active_tasks[task_id]["status"] = "FAILED"
                            del active_tasks[task_id]
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON: {e}")
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                logger.warning(f"WebSocket connection interrupted: {msg.type}")
                break
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {str(e)}")
            await asyncio.sleep(1)
            continue

async def run_interactive_mode():
    email = input("Enter email: ")  # Синхронный ввод для простоты
    password = input("Enter password: ")
    token = await authenticate(email, password)
    if not token:
        return

    logger.info("\nInteractive mode. Commands:")
    logger.info("- 'ws': Connect to WebSocket and listen for messages")
    logger.info("- 'binarize file:<path> [algorithm]': Send image binarization task from a .txt file")
    logger.info("- 'exit': Exit")

    session = None
    websocket = None
    active_tasks = {}

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    cmd = await ainput("\n> ")
                    if not cmd:
                        continue

                    if cmd == "exit":
                        if websocket and not websocket.closed:
                            await websocket.close()
                            logger.info("WebSocket connection closed")
                        break

                    elif cmd == "ws":
                        if websocket:
                            logger.info("Already connected to WebSocket")
                            continue

                        headers = {"Authorization": f"Bearer {token}"}
                        websocket = await session.ws_connect(
                            WS_URL,
                            headers=headers,
                            max_msg_size=10*1024*1024,
                            timeout=ClientWSTimeout(ws_close=30)
                        )
                        logger.info("Connected to WebSocket")
                        asyncio.create_task(listen_websocket(websocket, active_tasks))

                    elif cmd.startswith("binarize"):
                        if not websocket or websocket.closed:
                            logger.error("Error: WebSocket connection is closed. Run 'ws' first.")
                            continue

                        remainder = cmd[len("binarize"):].strip()
                        if not remainder:
                            logger.error("Invalid format. Use: binarize file:<path> [algorithm]")
                            continue

                        parts = remainder.split(maxsplit=1)
                        if len(parts) < 1:
                            logger.error("Invalid format. Use: binarize file:<path> [algorithm]")
                            continue

                        source = parts[0]
                        algorithm = parts[1] if len(parts) > 1 else "niblack"

                        if source.startswith("file:"):
                            file_path = source.replace("file:", "")
                            try:
                                with open(file_path, "r") as f:
                                    image_base64 = f.read().strip()
                                logger.info(f"Loaded image data from file (length: {len(image_base64)})")

                                if not image_base64:
                                    logger.error("Error: File is empty")
                                    continue
                            except FileNotFoundError:
                                logger.error(f"Error: File {file_path} not found")
                                continue
                            except Exception as e:
                                logger.error(f"Error reading file: {str(e)}")
                                continue

                        else:
                            logger.error("Invalid format. Use: binarize file:<path> [algorithm]")
                            continue

                        if len(image_base64) % 4 != 0:
                            missing_padding = (4 - len(image_base64) % 4) % 4
                            image_base64 += "=" * missing_padding
                            logger.info(f"Added padding, new length: {len(image_base64)}")

                        try:
                            base64.b64decode(image_base64, validate=True)
                        except base64.binascii.Error as e:
                            logger.error(f"Invalid base64 string: {str(e)}")
                            continue

                        message = json.dumps({
                            "action": "binarize_image",
                            "image": image_base64,
                            "algorithm": algorithm
                        })
                        logger.info(f"Sending message length: {len(message)}")
                        try:
                            await websocket.send_str(message)
                            logger.info("Message sent successfully")
                        except Exception as e:
                            logger.error(f"Failed to send message: {str(e)}")
                            websocket = None

                    else:
                        logger.error("Unknown command")

                except asyncio.CancelledError:
                    if websocket and not websocket.closed:
                        await websocket.close()
                        logger.info("WebSocket connection closed")
                    break

    except Exception as e:
        logger.error(f"Error in interactive mode: {str(e)}")
    finally:
        if websocket and not websocket.closed:
            await websocket.close()
            logger.info("WebSocket connection closed")

async def run_script_mode(script_file: str):
    with open(script_file, "r") as f:
        lines = f.readlines()

    email = None
    password = None
    token = None
    session = None
    websocket = None
    active_tasks = {}

    try:
        async with aiohttp.ClientSession() as session:
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line == "exit":
                    if websocket:
                        await websocket.close()
                        logger.info("WebSocket connection closed")
                    break
                elif line == "ws":
                    if not token:
                        logger.error("Not authenticated. Use 'auth' first.")
                        return
                    if websocket:
                        logger.info("Already connected to WebSocket")
                        continue
                    headers = {"Authorization": f"Bearer {token}"}
                    websocket = await session.ws_connect(
                        WS_URL,
                        headers=headers,
                        max_msg_size=10*1024*1024,
                        timeout=ClientWSTimeout(ws_close=30)
                    )
                    logger.info("Connected to WebSocket")
                    asyncio.create_task(listen_websocket(websocket, active_tasks))
                elif line.startswith("auth"):
                    parts = line.split(maxsplit=2)
                    if len(parts) < 3:
                        logger.error("Invalid auth command. Use: auth <email> <password>")
                        continue
                    email, password = parts[1], parts[2]
                    token = await authenticate(email, password)
                    if not token:
                        return
                elif line.startswith("binarize"):
                    if not websocket:
                        logger.error("Error: Not connected to WebSocket. Run 'ws' first.")
                        continue

                    remainder = line[len("binarize"):].strip()
                    if not remainder:
                        logger.error("Invalid format. Use: binarize file:<path> [algorithm]")
                        continue

                    parts = remainder.split(maxsplit=1)
                    if len(parts) < 1:
                        logger.error("Invalid format. Use: binarize file:<path> [algorithm]")
                        continue

                    source = parts[0]
                    algorithm = parts[1] if len(parts) > 1 else "niblack"

                    if source.startswith("file:"):
                        file_path = source.replace("file:", "")
                        try:
                            with open(file_path, "r") as f:
                                image_base64 = f.read().strip()
                            logger.info(f"Loaded image data from file (length: {len(image_base64)})")

                            if not image_base64:
                                logger.error("Error: File is empty")
                                continue
                        except FileNotFoundError:
                            logger.error(f"Error: File {file_path} not found")
                            continue
                        except Exception as e:
                            logger.error(f"Error reading file: {str(e)}")
                            continue

                    else:
                        logger.error("Invalid format. Use: binarize file:<path> [algorithm]")
                        continue

                    if len(image_base64) % 4 != 0:
                        missing_padding = (4 - len(image_base64) % 4) % 4
                        image_base64 += "=" * missing_padding
                        logger.info(f"Added padding, new length: {len(image_base64)}")

                    try:
                        base64.b64decode(image_base64, validate=True)
                    except base64.binascii.Error as e:
                        logger.error(f"Invalid base64 string: {str(e)}")
                        continue

                    message = json.dumps({
                        "action": "binarize_image",
                        "image": image_base64,
                        "algorithm": algorithm
                    })
                    logger.info(f"Sending message length: {len(message)}")
                    await websocket.send_str(message)

    except Exception as e:
        logger.error(f"Error in script mode: {str(e)}")
    finally:
        if websocket and not websocket.closed:
            await websocket.close()
            logger.info("WebSocket connection closed")

async def main():
    parser = argparse.ArgumentParser(description="Console client for image processing server")
    parser.add_argument("--script", help="Path to script file")
    args = parser.parse_args()

    try:
        if args.script:
            await run_script_mode(args.script)
        else:
            await run_interactive_mode()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
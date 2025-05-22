from celery import Celery
import redislite
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# загрузка переменных окружения
load_dotenv()

# инициализация redislite
try:
    redis_db_path = os.getenv("REDIS_DB_PATH", "/mnt/c/Users/kseni/PPP_24-25_4sem/3lab/project/redis.db")
    redis_instance = redislite.Redis(redis_db_path)
    redis_socket = redis_instance.socket_file

    # проверка существования сокета
    if not os.path.exists(redis_socket):
        logger.error(f"Redis socket {redis_socket} not found!")
        raise RuntimeError("Redis socket not created by redislite")

    # проверка доступности Redis
    if not redis_instance.ping():
        logger.error("Failed to ping Redis!")
        raise RuntimeError("Redis is not responding")

    logger.info(f"Redis socket created at: {redis_socket}")
except Exception as e:
    logger.error(f"Failed to initialize redislite: {str(e)}")
    raise

def create_celery_app():
    # формируем правильный URL для сокета с тремя слешами
    redis_url = f"redis+socket:///{redis_socket}"

    celery_app = Celery(
        "tasks",
        broker=redis_url,
        backend=redis_url  # используем redislite как бэкенд
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        broker_transport_options={
            'socket_timeout': 5
        },
        result_backend_transport_options={
            'socket_timeout': 5
        }
    )
    celery_app.autodiscover_tasks(['app'])
    return celery_app

celery_app = create_celery_app()

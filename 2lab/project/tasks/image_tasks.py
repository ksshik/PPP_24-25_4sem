from celery import Celery  
from app.core.config import settings  
from app.services.image_processing import binarize_image 

celery = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)  # Создание экземпляра Celery

@celery.task  
def process_image_task(image: str, algorithm: str = "niblack"):  # Бинаризация изображения
    return binarize_image(image, algorithm)  

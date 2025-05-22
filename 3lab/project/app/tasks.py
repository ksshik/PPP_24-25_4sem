from app.celery_config import celery_app
from celery import shared_task
from app.services.image_processing import binarize_image
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_image_task(self, image: str, algorithm: str = "niblack", token: str = None):
    logger.info(f"Received image: {image[:50]}... (length: {len(image)})")
    
    for progress in range(0, 101, 20):
        time.sleep(1) 
        self.update_state(state='PROGRESS', meta={'progress': progress})
    
    result = binarize_image(image, algorithm)
    
    self.update_state(state='COMPLETED', meta={'binarized_image': result})
    
    return {'binarized_image': result}
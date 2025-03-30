from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from app.schemas.image import ImageBinarizationRequest
import base64
from io import BytesIO
from PIL import Image
import numpy as np
from skimage import filters

router = APIRouter()

@router.post("/binary_image/json") # Эндпоинт для JSON-запроса
async def binary_image_json(request: ImageBinarizationRequest):
    try:
        image_data = base64.b64decode(request.image)     # Декодируем строку base64 в изображение
        image = Image.open(BytesIO(image_data)).convert("L")
        if request.algorithm.lower() != "niblack":         # Применяем бинаризацию
            raise HTTPException(status_code=400, detail="Only 'niblack' algorithm is supported")
        image_array = np.array(image)
        threshold = filters.threshold_niblack(image_array)
        binarized_array = image_array > threshold
        binarized_image = Image.fromarray(binarized_array.astype(np.uint8) * 255)
        buffered = BytesIO()
        binarized_image.save(buffered, format="PNG")
        binarized_image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"binarized_image": binarized_image_base64}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")

@router.post("/binary_image") # Эндпоинт для загрузки файла
async def binary_image_file(image: UploadFile = File(...)):
    try:
        image_data = await image.read() # Читаем файл
        image = Image.open(BytesIO(image_data)).convert("L")
        image_array = np.array(image) # Бинаризация
        threshold = filters.threshold_niblack(image_array)
        binarized_array = image_array > threshold
        binarized_image = Image.fromarray(binarized_array.astype(np.uint8) * 255)
        buffered = BytesIO()
        binarized_image.save(buffered, format="PNG")
        binarized_image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"binarized_image": binarized_image_base64}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")
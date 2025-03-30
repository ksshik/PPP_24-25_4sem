import base64
from io import BytesIO
from PIL import Image
import cv2
import numpy as np

def binarize_image(image_base64: str, algorithm: str = "niblack") -> str:
    image_data = base64.b64decode(image_base64)     # Декодируем base64 в изображение
    image = Image.open(BytesIO(image_data))
    img_array = np.array(image.convert("L"))  # Преобразуем в градации серого

    if algorithm == "niblack":
        # Параметры для Ниблэка
        window_size = 25  # Размер окна для локального анализа 
        k = -0.2  
        binarized = cv2.adaptiveThreshold(
            img_array,
            255,  # Максимальное значение для бинарного изображения
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # Метод вычисления среднего (гауссово взвешивание)
            cv2.THRESH_BINARY,  # Тип бинаризации
            window_size,  # Размер окна
            k  # Константа C влияет на порог
        )
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Supported algorithm: 'niblack'")

    result_image = Image.fromarray(binarized)     # Кодируем результат обратно в base64
    buffered = BytesIO()
    result_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
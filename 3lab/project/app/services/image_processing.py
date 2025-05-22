
import base64
from io import BytesIO
from PIL import Image
import numpy as np
from skimage import filters
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def binarize_image(image_base64: str, algorithm: str = "niblack") -> str:
    try:
        # отладочный вывод длины входной строки
        logger.info(f"Received image_base64 length: {len(image_base64)}")

        # удаляем префикс data:image/jpeg;base64, если он есть
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]

        # удаляем пробелы и переносы строк
        image_base64 = image_base64.strip()
        if not image_base64:
            raise ValueError("Пустая строка base64 после обработки")

        # проверяем валидность длины base64 (должна быть кратна 4)
        if len(image_base64) % 4 != 0:
            logger.info(f"Invalid base64 length: {len(image_base64)}. Attempting to fix padding...")
            missing_padding = (4 - len(image_base64) % 4) % 4
            image_base64 += "=" * missing_padding
        logger.info(f"Processed image_base64 length after padding: {len(image_base64)}")

        # декодируем base64 в бинарные данные
        try:
            image_data = base64.b64decode(image_base64, validate=True)
        except base64.binascii.Error as e:
            raise ValueError(f"Ошибка декодирования base64: {str(e)}")
        logger.info(f"Decoded image_data length: {len(image_data)}")

        image = Image.open(BytesIO(image_data)).convert("L")
        img_array = np.array(image)

        if algorithm.lower() != "niblack":
            raise ValueError("Only 'niblack' algorithm is supported")

        threshold = filters.threshold_niblack(img_array)
        binarized_array = img_array > threshold
        binarized_image = Image.fromarray(binarized_array.astype(np.uint8) * 255)

        # кодируем результат обратно в base64
        buffered = BytesIO()
        binarized_image.save(buffered, format="PNG")
        binarized_image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        logger.info(f"Output base64 length: {len(binarized_image_base64)}")
        return binarized_image_base64

    except base64.binascii.Error as e:
        raise ValueError(f"Ошибка декодирования base64: {str(e)}")
    except Exception as e:
        raise ValueError(f"Ошибка при обработке изображения: {str(e)}")
"""
API клиент для работы с Nebius API
"""
import requests
import logging
from typing import Optional
from PIL import Image
import io
import base64
from config import NEBUS_API_KEY, NEBUS_API_URL, API_TIMEOUT, IMAGE_MAX_SIZE, IMAGE_QUALITY

logger = logging.getLogger(__name__)

class NebiusAPIClient:
    """Клиент для работы с Nebius API"""
    
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _prepare_image(self, image_data: bytes) -> str:
        """Подготовка изображения для API"""
        try:
            # Открываем изображение
            image = Image.open(io.BytesIO(image_data))
            
            # Оптимизируем размер изображения для API
            image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
            
            # Конвертируем в base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=IMAGE_QUALITY)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return img_base64
        except Exception as e:
            logger.error(f"Error preparing image: {e}")
            raise
    
    def analyze_image(self, image_data: bytes) -> str:
        """Анализ изображения еды через Nebius API"""
        try:
            # Подготавливаем изображение
            img_base64 = self._prepare_image(image_data)
            
            # Данные для запроса
            data = {
                "model": "Qwen/Qwen2.5-VL-72B-Instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Проанализируй это изображение еды и определи примерное количество калорий. Ответь только числом калорий, без дополнительного текста."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            # Отправляем запрос к API
            response = requests.post(
                f"{self.api_url}chat/completions",
                headers=self.headers,
                json=data,
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    calories = result['choices'][0]['message']['content'].strip()
                    return f"Примерное количество калорий: {calories}"
                else:
                    logger.error(f"Unexpected API response format: {result}")
                    return "Извините, не удалось получить корректный ответ от API. Попробуйте еще раз."
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return "Извините, не удалось проанализировать изображение. Попробуйте еще раз."
                
        except requests.exceptions.Timeout:
            logger.error("API request timeout")
            return "Превышено время ожидания ответа от сервера. Попробуйте еще раз."
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return "Ошибка соединения с сервером. Попробуйте еще раз."
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return "Произошла ошибка при анализе изображения. Попробуйте еще раз."
    
    def analyze_text(self, text_description: str) -> str:
        """Анализ текстового описания еды через Nebius API"""
        try:
            # Данные для запроса
            data = {
                "model": "Qwen/Qwen2.5-VL-72B-Instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Проанализируй это описание еды и определи примерное количество калорий: '{text_description}'. Ответь только числом калорий, без дополнительного текста."
                    }
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            # Отправляем запрос к API
            response = requests.post(
                f"{self.api_url}chat/completions",
                headers=self.headers,
                json=data,
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    calories = result['choices'][0]['message']['content'].strip()
                    return f"Примерное количество калорий: {calories}"
                else:
                    logger.error(f"Unexpected API response format: {result}")
                    return "Извините, не удалось получить корректный ответ от API. Попробуйте еще раз."
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return "Извините, не удалось проанализировать описание. Попробуйте еще раз."
                
        except requests.exceptions.Timeout:
            logger.error("API request timeout")
            return "Превышено время ожидания ответа от сервера. Попробуйте еще раз."
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return "Ошибка соединения с сервером. Попробуйте еще раз."
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return "Произошла ошибка при анализе описания. Попробуйте еще раз."

# Создаем глобальный экземпляр клиента
api_client = NebiusAPIClient(NEBUS_API_KEY, NEBUS_API_URL)

from datetime import datetime, timezone
import time
from celery import Celery
from PIL import Image, ImageFilter, ImageEnhance
import re
import os


# Celery-worker - Python Процесс: 
# Постоянно «слушает» очередь
# Получает сообщение, декодирует его
# Видит, нужно вызвать задачу 
# выполняет задачи в отдельных процессах
# 




# Инициализация Celery
celery_app = Celery(
    __name__,
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    
)


@celery_app.task(time_limit=12)
def test_task(file_id: int):
    print(f"[{file_id}] Начало выполнения...")
    time.sleep(4)
    return f"First Task completed! file: {file_id}"


@celery_app.task(time_limit=40)
def process_image_task(file_id: int, original_path: str):
    """
    Обрабатывает изображение и обновляет is_processed в БД
    """
    
    try:
        print(f"[File ID: {file_id}] Начало обработки...")
        
        # Логика обработки с PIL
        with Image.open(original_path) as img:
            width = height = 400
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Сохраняем результат
            processed_filename = f"processed_{file_id}.jpg"
            processed_path = os.path.join("processed", processed_filename)
            os.makedirs("processed", exist_ok=True)
            img.save(processed_path, "JPEG", quality=85)
        
        
        return {
            "status": "success",
            "file_id": file_id,
            "is_processed": True,
            "processed_path": processed_path
        }
        
    except Exception as e:
        print(f"[File ID: {file_id}] Ошибка обработки: {str(e)}")
        return {
            "status": "error", 
            "file_id": file_id,
            "is_processed": False,
            "error": str(e)
        }


@celery_app.task(bind=True, time_limit=30)
def analyze_text_task(self, text: str, analysis_type: str):
    """
    Анализирует текст и возвращает статистику
    """

    try:
        # твоя логика
        if not text.strip():
            raise ValueError("Empty text provided")
        
    except Exception as e:
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat() }
    if analysis_type != "full":
        return {
            "status": "error",
            "message": "write 'full' in 'analysis_type' "}
    else:
        word_count = len(re.findall(r'\b\w+\b', text)) 
        char_count = len(text)
        time.sleep(3)
        
        return {
            "task_id": self.request.id,
            "status": "success", 
            "analysis_type": analysis_type,
            "results": {
                "word_count": word_count,
                "char_count": char_count,
                "avg_word_length": round(char_count / word_count, 2) if word_count > 0 else 0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    



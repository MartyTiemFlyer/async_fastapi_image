import time
from celery import Celery



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
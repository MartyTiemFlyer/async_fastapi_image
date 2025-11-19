from fastapi import FastAPI
from celery import Celery

app = FastAPI()

# Инициализация Celery
celery = Celery(
    __name__,
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Простая тестовая задача
@celery.task
def test_task():
    return "Task completed!"



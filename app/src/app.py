from typing import Annotated
from fastapi import Depends, FastAPI, Query, UploadFile
from sqlalchemy.orm import Session
from celery import Celery
import uvicorn

from .models import File_model, SessionLocal

app = FastAPI()

# Инициализация Celery
celery = Celery(
    __name__,
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# Зависимость - подключение
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Простая тестовая задача
@celery.task
def test_task():
    return "Task completed!"


@app.post("/upload-file")
async def upload_file(file: UploadFile | None = None):
    if not file:
        return {"message": "No upload file sent"}
    else:
        return {"filename": file.filename}

###################################################
async def pagination_params(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=10)
):
    """Зависимость - параметры пагинации"""
    
    return {"skip": skip, "limit": limit}

async def validate_status():
    """Зависимость - для проверки статусов"""
    
    return {}


@app.get("/files")
async def get_files(
    pagination: dict = Depends(pagination_params),
    db: Session = Depends(get_db)  # получаем готовую сессию
):
    skip = pagination["skip"]
    limit = pagination["limit"]
    
    files = db.query(File_model).offset(skip).limit(limit).all()
    return files

@app.post("/files")
async def create_file(
    file_name: str,
    file_size: int, 
    mime_type: str,
    file_path: str,
    db: Session = Depends(get_db)
):
    # Создаём объект файла
    new_file = File_model(
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type, 
        file_path=file_path
    )
    
    # Добавляем в БД
    db.add(new_file)
    db.commit()
    db.refresh(new_file)  #  получаем ID созданной записи
    
    return new_file




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    
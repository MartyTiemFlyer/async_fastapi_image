from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Path, Query, UploadFile
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

async def validate_status(s: str) -> bool:
    """Зависимость - для проверки статусов"""
    if s.lower() in ('true', '1', 'yes', 'on'):
        return True
    if s.lower() in ('false', '0', 'no', 'off'):
        return False
    raise HTTPException(
        status_code=400,
        detail=f"Не удаётся преобразовать '{s}' в булево значение"
    )



###################################################
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

@app.patch("/files/{file_id}/status")
async def update_status(
    file_id: int = Path(..., ge=1),
    new_status: str = Depends(validate_status), 
    db: Session = Depends(get_db)
):
    # 1. Найти файл в БД
    file = db.query(File_model).filter(File_model.file_id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # 2. Обновить статус
    file.is_processed = new_status  # используем существующее поле
    db.commit()
    
    return {"file_id": file_id, "new_status": new_status}
    



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    
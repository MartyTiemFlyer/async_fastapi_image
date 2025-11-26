import json
import os
import time
from typing import Annotated
from fastapi import Depends, FastAPI, Form, HTTPException, Path, Query, UploadFile
from sqlalchemy.orm import Session
import uvicorn
from .models import File_model, SessionLocal
from app.src.worker import analyze_text_task, celery_app, process_image_task


app = FastAPI()


###################################################
# Depends 
###################################################

async def get_db():
    """Зависимость - подключение к БД mysql"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
# Endpoints 
###################################################
@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/upload-file")
async def upload_file(file: UploadFile | None = None):
    if not file:
        return {"message": "No upload file sent"}
    else:
        return {"filename": file.filename}

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
    
###################################################
# CELERY 
###################################################
@app.post("/test-task/{file_id}")
async def run_test_task(file_id: int):
    """ Отправляем тест-задачу в очередь (полный путь - app.src.worker)"""
    
    # кладёт задачу в Redis
    task = celery_app.send_task(
        'app.src.worker.test_task', args=[file_id]) 

    # мгновенный ответ клиенту
    return {
        "message": "Задача отправлена в очередь",
        "task_id": task.id,
        "file_id": file_id
    }

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Запрос статуса по задаче из редис """
    task = celery_app.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {"status": "Ожидает выполнения"}
    elif task.state != 'FAILURE':
        response = {
            "status": task.state,
            "result": task.result
        }
    else:
        # Ошибка
        response = {
            "status": "Ошибка",
            "error": str(task.info)  # Сообщение об ошибке
        }
    
    return response


@app.post("/upload-and-process/")
async def upload_and_process(
    file: UploadFile,
    db: Session = Depends(get_db)
):
    """Загружает файл, сохраняет в БД и запускает обработку в Celery"""
    
    # Сохраняем файл на диск
    UPLOAD_DIR = "/app/uploads"  # абсолютный путь
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Создаем запись в БД 
    new_file = File_model(
        file_name=file.filename,
        file_size=len(content),
        mime_type=file.content_type,
        file_path=file_path
        # is_processed автоматически False
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    
    # Запускаем фоновую задачу process_image_task
    task = process_image_task.delay(new_file.file_id, file_path)  # Используем file_id из БД
    
    
    return {
        "message": "Изображение загружено и отправлено на обработку",
        "task_id": task.id,
        "file_id": new_file.file_id,
        "file_name": file.filename,
        "is_processed": False  # Показываем текущий статус
    }


@app.post("/text-analyze")
async def analyze_text( text: str, analysis_type: str):
    """
    Ручка: анализ текста в фоне
    """

    task = analyze_text_task.delay(text, analysis_type)


    return {
        "task_id": task.id,
        "message": "Сообщение отправлено на обработку"
    }





if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    
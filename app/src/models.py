from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String
DATABASE_URL = "mysql+pymysql://app_user:app_password@mysql:3306/app_db"


# Создаём движок SQLAlchemy
engine = create_engine(DATABASE_URL)

# Создаём фабрику сессий для взаимодействия с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

# Модель 
class File_model(Base):
    __tablename__ = "files"

    file_id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), index=True) 
    file_size = Column(Integer)      # размер в байтах
    mime_type = Column(String(100))  # например "image/jpeg"
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_path = Column(String(500))  # путь к файлу на диске
    is_processed = Column(Boolean, default=False) 

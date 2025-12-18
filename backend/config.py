from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str = 'localhost'
    DB_PORT: str = '54326'
    DB_NAME: str = 'tabloidproteome_modpa'
    DB_USER: str = 'postgres'
    DB_PASSWORD: str = 'admin'
    ENVIRONMENT: str = 'DEV'

    class Config:
        env_file = '.env'

settings = Settings()
print('settings', settings)

def config_uri():
    DATABASE_NAME = settings.DB_NAME
    PASSWORD = settings.DB_PASSWORD
    HOST = settings.DB_HOST
    USER = settings.DB_USER
    PORT = settings.DB_PORT
    DATABASE_URI = 'postgresql+psycopg2://' + USER +':' + PASSWORD + '@' + HOST + ':' + PORT + '/' + DATABASE_NAME
    return DATABASE_URI

def get_db():
    database_uri = config_uri()

    engine = create_engine(database_uri)
    SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
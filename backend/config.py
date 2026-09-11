from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Generic placeholders only — real local/prod values belong in the gitignored .env, not here.
    DB_HOST: str = 'localhost'
    DB_PORT: str = '54326'
    DB_NAME: str = 'tabloidproteome_modpa'
    DB_USER: str = 'postgres'
    DB_PASSWORD: str = 'admin'
    ENVIRONMENT: str = 'DEV'
    DATA_DIR: str = 'data/'

    class Config:
        env_file = '.env'

settings = Settings()
print('settings loaded for', settings.ENVIRONMENT, settings.DB_NAME)

def config_uri(for_settings: Settings = None) -> str:
    """Build a DB URI from the given Settings, or the default `.env`-backed settings."""
    s = for_settings or settings
    return f'postgresql+psycopg2://{s.DB_USER}:{s.DB_PASSWORD}@{s.DB_HOST}:{s.DB_PORT}/{s.DB_NAME}'

def get_db():
    database_uri = config_uri()

    engine = create_engine(database_uri)
    SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
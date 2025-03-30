from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key"  # Ключ для подписания JWT токенов
    ALGORITHM: str = "HS256"  # Алгоритм для подписания JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Время жизни токена (в минутах)
    DATABASE_URL: str = "sqlite:///./app.db"  # URL для базы данных
    REDIS_URL: str = "redis://localhost:6379/0"  # URL для Redis

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite:///./app.db"
    REDIS_DB_PATH: str = "/mnt/c/Users/kseni/PPP_24-25_4sem/2lab/project/redis.db"  

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
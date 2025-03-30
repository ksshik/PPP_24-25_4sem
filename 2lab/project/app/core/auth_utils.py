from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from fastapi import Depends, HTTPException, status  
import jwt 
from datetime import datetime, timedelta, timezone  
from app.core.config import settings  

security = HTTPBearer()  

def create_access_token(data: dict):  # Создание токена
    to_encode = data.copy() 
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)  # Время истечения
    to_encode.update({"exp": expire})  
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)  # JWT токен с секретным ключом
    return encoded_jwt  

def verify_password(plain_password: str, hashed_password: str) -> bool:  # Проверка пароля
    from passlib.context import CryptContext  
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  
    return pwd_context.verify(plain_password, hashed_password)  

def get_password_hash(password: str) -> str:  # Хеширование пароля
    from passlib.context import CryptContext  
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") 
    return pwd_context.hash(password)  

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):  # Извлечение текущего пользователя
    token = credentials.credentials  
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])  # Декодируем токен с помощью секретного ключа
        user_id: str = payload.get("sub")  #
        if user_id is None:  
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,  # Ошибка авторизации
                detail="Invalid authentication credentials",  
                headers={"WWW-Authenticate": "Bearer"}, 
            )
    except jwt.PyJWTError:  # Если произошла ошибка при декодировании токена
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  
            detail="Invalid authentication credentials",  
            headers={"WWW-Authenticate": "Bearer"},  
        )
    return user_id  

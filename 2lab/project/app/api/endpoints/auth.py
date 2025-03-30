from fastapi import APIRouter, Depends, HTTPException, status  
from sqlalchemy.orm import Session  
from app.schemas.user import UserCreate, UserResponse  
from app.cruds.user import create_user, get_user_by_email  
from app.core.security import create_access_token, verify_password, get_current_user 
from app.db.session import get_db  

router = APIRouter()

@router.post("/sign-up/", response_model=UserResponse) # Маршрут для регистрации нового пользователя
def sign_up(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email) # Проверка, существует ли уже пользователь с таким email
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    new_user = create_user(db, user, user.password)     # Создание нового пользователя и сохранение в базу
    access_token = create_access_token(data={"sub": new_user.email})  # Передаем email в токен
    return {"id": new_user.id, "email": new_user.email, "token": access_token}

@router.post("/login/", response_model=UserResponse) # Маршрут для логина пользователя
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)     # Проверка, существует ли пользователь с таким email
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": db_user.email})  
    return {"id": db_user.id, "email": db_user.email, "token": access_token}

@router.get("/users/me/", response_model=UserResponse) # Маршрут для получения информации о текущем пользователе
def read_users_me(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user_id)     # Получаем пользователя по его id (из токена)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": db_user.id, "email": db_user.email}  

    
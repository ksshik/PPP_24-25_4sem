from sqlalchemy.orm import Session  
from app.models.account import User  
from app.schemas.account import UserCreate 
from app.core.auth_utils import get_password_hash  

def create_user(db: Session, user: UserCreate, password: str):  # создание пользователя
    hashed_password = get_password_hash(password)  # хеширование пароля
    db_user = User(email=user.email, hashed_password=hashed_password)  
    db.add(db_user)  
    db.commit() 
    db.refresh(db_user)  
    return db_user  

def get_user_by_email(db: Session, email: str):  # функция для получения пользователя по email
    return db.query(User).filter(User.email == email).first() 

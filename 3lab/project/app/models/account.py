from sqlalchemy import Column, Integer, String
from app.db.models_base import Base

class User(Base): # база данных пользователей 
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
from pydantic import BaseModel, EmailStr # Описание типов данных

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    email: str
    token: str | None = None
    

    class Config:
        from_attributes = True  
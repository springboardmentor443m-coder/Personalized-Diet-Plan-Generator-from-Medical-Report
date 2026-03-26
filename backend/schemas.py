from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

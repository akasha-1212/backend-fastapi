from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str

 


class UploadOut(BaseModel):
    id: int
    shop_id: int
    customer_name: str
    file_name: str
    file_path: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
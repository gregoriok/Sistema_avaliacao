from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile, File
from enum import Enum
from typing import List
# Pydantic schemas for validation

class CategoryEnum(str, Enum):
    category_1 = "1"
    category_2 = "2"
    category_3 = "3"
    category_4 = "4"

class getRateRequest(BaseModel):
    user_id: UUID
    category: str

class RatingItem(BaseModel):
    criteria: str
    score: int

class RateRequest(BaseModel):
    evaluated_user_id: UUID
    ratings: List[RatingItem]
    category: str
    evaluator_id: UUID

class UserCreate(BaseModel):
    name: str
    document: str
    email: str
    user_type: str
    password: str
    category: CategoryEnum

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    name: Optional[str]
    document: Optional[str]
    email: Optional[str]
    user_type: Optional[str]
    file: Optional[str]
    category: Optional[CategoryEnum]
    password: Optional[str]

class UserOut(BaseModel):
    name: str
    document: str
    email: str
    user_type: str
    category: CategoryEnum
    id: UUID
    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    token: str
    token_type: str
    expiration_date: datetime
    class Config:
        orm_mode = True

class ImageCreate(BaseModel):
    user_id: UUID
    subcategory: str
    description: Optional[str] = None

class ImageUpdate(BaseModel):
    subcategory: Optional[str] = None
    description: Optional[str] = None

class ImageRatingCreate(BaseModel):
    rating: int

class ImageRatingUpdate(BaseModel):
    rating: int

class TokenCreate(BaseModel):
    token: str

class TokenUpdate(BaseModel):
    used: bool

class SendEmailRequest(BaseModel):
    email: str
    name: str

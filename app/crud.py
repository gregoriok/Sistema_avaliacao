import uuid

from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional
from app.utils import *
from uuid import UUID
from fastapi import UploadFile



def create_user(db: Session, user: schemas.UserCreate, file_content: bytes):
    db_user_existing = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.document == user.document)
    ).first()

    if db_user_existing:
        return None

    hashed_password = hash_password(user.password)
    db_user = models.User(name=user.name,
                          document=user.document,
                          email=user.email,
                          user_type=user.user_type,
                          file=file_content,
                          password=hashed_password,
                          category=user.category)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_id(db: Session, user_id: UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 10) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: UUID, user: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db_user.name = user.name
        db_user.document = user.document
        db_user.email = user.email
        db_user.user_type = user.user_type
        db_user.file = user.file
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: UUID):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user and verify_password(password, user.password):
        return user
    return None


def generate_token_for_user(db: Session, user_id: UUID):
    token_data = {"sub": str(user_id)}
    token = create_access_token(token_data, expires_delta=timedelta(days=5))

    db_token = models.Token(token=token, expiration_date=datetime.utcnow() + timedelta(days=5))
    db.add(db_token)
    db.commit()

    return {
        "token": db_token.token,
        "expiration_date": db_token.expiration_date
    }

def upload_image(db: Session, image: schemas.ImageCreate):
    db_image = models.Image(
        user_id=image.user_id,
        image_data=image.image_data,
        subcategory=image.subcategory,
        description=image.description
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return db_image

def get_image_by_id(db:Session,image_id: UUID):
    return db.query(models.Image).filter(models.Image.id == image_id).first()

def delete_image(db: Session, image_id: UUID):
    db_image = db.query(models.Image).filter(models.Image.id == image_id).first()

    if db_image:
        db.delete(db_image)
        db.commit()

    return db_image

async def update_image(db: Session, image_id: UUID, new_image: Optional[UploadFile], description:Optional[str] = None):
    db_image = db.query(models.Image).filter(models.Image.id == image_id).first()

    if not db_image:
        return None

    if description is not None:
        db_image.description = description

    if new_image:
        image_data = await new_image.read()
        db_image.image_data = image_data  # Atualiza o campo binário da imagem

    # Commit das alterações no banco de dados
    db.commit()
    db.refresh(db_image)

    return db_image

def get_images_by_user(db: Session, user_id: UUID, subcategory: Optional[str] = None):
    query = db.query(models.Image).filter(models.Image.user_id == user_id)

    if subcategory:
        query = query.filter(models.Image.subcategory == subcategory)

    return query.all()


def set_image_rating(db:Session, image_id: UUID, rating: int, user_id: UUID):
    user_data = get_user_by_id(db=db, user_id=user_id)
    if user_data.user_type != 'A':
        raise HTTPException(status_code=500, detail="Apenas usuario avaliador pode dar notas")

    if not (0 <= rating <= 10):
        raise HTTPException(status_code=400, detail="Nota deve ser entre 0 e 10.")

    db_image = get_image_by_id(db, image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Imagem não encontrada.")

    db_image_rating = models.ImageRating(
        evaluator_id=user_id, image_id=image_id, rating=rating
    )
    db.add(db_image_rating)
    db.commit()
    db.refresh(db_image_rating)
    return db_image_rating

def get_image_rating(db:Session,user_id:UUID,subcategory:str):
    rating: int = 0
    image_count: int = 0
    db_image_set = get_images_by_user(db=db, user_id=user_id, subcategory=subcategory)
    if not db_image_set:
        return 0
    for image in db_image_set:
        image_rating = db.query(models.ImageRating).filter(image.id == models.ImageRating.image_id).first()
        if not image_rating:
            return 0
        rating += image_rating.rating
        image_count += 1

    return rating / image_count
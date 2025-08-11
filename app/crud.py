import uuid

from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional
from app.utils import *
from uuid import UUID
from fastapi import UploadFile
import logging
from .models import ImageRating
from app.schemas import RatingItem
from sqlalchemy import and_, cast, or_
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_user(db: Session, user: schemas.UserCreate, file_content: bytes = None):
    if user.document or user.email:
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
                          category=user.category,
                          cep=user.cep,
                          complete_adress=user.complete_adress,
                          institution=user.institution)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_id(db: Session, user_id: UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 10) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def update_password(db: Session, user_id: UUID, password: str):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        hashed_password = hash_password(password)
        db_user.password = hashed_password
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
    token = create_access_token(token_data)

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
        description=image.description,
        title=image.title,
        place=image.place,
        equipment=image.equipment
    )
    print(db_image.__dict__)
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


def set_user_rating(
    db: Session,
    evaluated_user_id: UUID,
    ratings: List[RatingItem],
    evaluator_id: UUID,
    category: str
):
    user_data = get_user_by_id(db=db, user_id=evaluator_id)
    if user_data.user_type != 'A':
        raise HTTPException(status_code=403, detail="Apenas usuário avaliador pode dar notas.")

    evaluated_user = get_user_by_id(db=db, user_id=evaluated_user_id)
    if not evaluated_user:
        raise HTTPException(status_code=404, detail="Usuário avaliado não encontrado.")

    for rating_item in ratings:
        # Verifica se já existe nota para o critério informado
        existing = db.query(ImageRating).filter_by(
            evaluator_id=str(evaluator_id),
            evaluated_user_id=str(evaluated_user_id),
            category=category,
            criteria=rating_item.criteria
        ).first()

        if existing:
            existing.rating = rating_item.score  # Atualiza nota existente
        else:
            new_rating = ImageRating(
                evaluator_id=str(evaluator_id),
                evaluated_user_id=str(evaluated_user_id),
                category=category,
                rating=rating_item.score,
                criteria=rating_item.criteria
            )
            db.add(new_rating)

    db.commit()
    return True

def get_image_rating(db: Session, user_id: str, category: str, evaluator_id: str):
    image_rating = db.query(models.ImageRating).filter(
        and_(
            models.ImageRating.evaluated_user_id == user_id,
            models.ImageRating.category == category,
            models.ImageRating.evaluator_id == evaluator_id
        )
    ).all()  # Pega todas as notas da categoria para o usuário

    if image_rating:
        return [
            {"criteria": r.criteria, "rating": r.rating} for r in image_rating
        ]
    return False

def get_user_by_email_or_document(db: Session, email: str, document: str):
    query = db.query(models.User)
    conditions = []
    if email:
        conditions.append(models.User.email == email)
    if document:
        conditions.append(models.User.document == document)
    if conditions:
        return query.filter(or_(*conditions)).first()
    else:
        return None

def get_user_media(db: Session):
    medias = (
        db.query(
            models.ImageRating.evaluated_user_id.label("user_id"),
            models.User.name,
            models.User.category.label("user_category"),
            models.ImageRating.category,
            func.avg(models.ImageRating.rating).label("media")
        )
        .join(models.User, cast(models.ImageRating.evaluated_user_id, UUID) == models.User.id)
        .group_by(
            models.ImageRating.evaluated_user_id,
            models.ImageRating.category,
            models.User.name,
            models.User.category
        )
        .all()
    )

    usuarios = {}
    for row in medias:
        uid = str(row.user_id)
        if uid not in usuarios:
            usuarios[uid] = {
                "user_id": uid,
                "name": row.name,
                "user_category": row.user_category,
                "categoria_a_media": None,
                "categoria_b_media": None
            }
        if row.category == "A":
            usuarios[uid]["categoria_a_media"] = round(row.media, 2)
        elif row.category == "B":
            usuarios[uid]["categoria_b_media"] = round(row.media, 2)

    return list(usuarios.values())

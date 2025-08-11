from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime, Text, LargeBinary, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
import datetime
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa
# Users Table
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    document = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    user_type = Column(String)
    file = Column(LargeBinary)
    password = Column(String)
    category = Column(String, index=True)
    images = relationship("Image", back_populates="user")
    cep = Column(String)
    complete_adress = Column(String)
    institution = Column(String)

# Images Table
class Image(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    image_data = Column(LargeBinary)
    subcategory = Column(String, index=True)
    description = Column(String(1500))
    title = Column(String(50))
    place = Column(String(500))
    equipment = Column(String(100))

    user = relationship("User", back_populates="images")

# Image Ratings Table
class ImageRating(Base):
    __tablename__ = 'image_ratings'
    id = sa.Column(sa.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluator_id = sa.Column(sa.String, nullable=False)
    evaluated_user_id = sa.Column(sa.String, nullable=False)
    category = sa.Column(sa.String(1), nullable=False)
    rating = sa.Column(sa.Integer, nullable=False)
    criteria = Column(String, nullable=False)

class Token(Base):
    __tablename__ = "tokens"

    token = Column(String, primary_key=True, index=True)
    expiration_date = Column(DateTime, default=datetime.datetime.utcnow() + datetime.timedelta(days=7))

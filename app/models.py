from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime, Text, LargeBinary, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
import datetime
from sqlalchemy.dialects.postgresql import UUID

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
    ratings = relationship("ImageRating", back_populates="evaluator")

# Images Table
class Image(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    image_data = Column(LargeBinary)
    subcategory = Column(String, index=True)
    description = Column(String(500))

    user = relationship("User", back_populates="images")
    ratings = relationship("ImageRating", back_populates="image")

# Image Ratings Table
class ImageRating(Base):
    __tablename__ = "image_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"))
    rating = Column(Integer)

    evaluator = relationship("User", back_populates="ratings")
    image = relationship("Image", back_populates="ratings")

class Token(Base):
    __tablename__ = "tokens"

    token = Column(String, primary_key=True, index=True)
    expiration_date = Column(DateTime, default=datetime.datetime.utcnow() + datetime.timedelta(days=7))

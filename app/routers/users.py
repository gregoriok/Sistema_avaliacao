from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, FastAPI, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, models, schemas
from ..database import get_db
import logging
from uuid import UUID
from app.utils import *
from fastapi.security import OAuth2PasswordBearer
from fastapi.encoders import jsonable_encoder

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@router.get("/api/validate-token/")
async def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        # Aqui você chama a função de validação que você já tem
        payload = verify_token_expiration(token)
        return payload  # Retorna o payload para uso nas rotas
    except HTTPException:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

# Criar um novo usuário
@router.post("/api/users/", response_model=Optional[schemas.UserOut])
async def create_user(name: str = Form(...),
    document: str =Form(...),
    user_type: str =Form(...),
    email: str = Form(...),
    password: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...), db: Session = Depends(get_db)):

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="O arquivo deve ser um PDF")

    # Lê o conteúdo do arquivo
    file_content = await file.read()

    # Criação do objeto UserCreate para ser passado ao CRUD
    user_data = schemas.UserCreate(
        name=name,
        email=email,
        password=password,
        document=document,
        user_type=user_type,
        category=category
    )

    # Chama a função de criação do usuário com o conteúdo do arquivo
    db_user = crud.create_user(db=db, user=user_data,file_content=file_content)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já existe com o mesmo e-mail ou documento"
        )

    return db_user

# Obter todos os usuários
@router.get("/api/users/", response_model=Optional[List[schemas.UserOut]])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    db_users = crud.get_users(db=db, skip=skip, limit=limit)
    if not db_users:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No users found.")
    return db_users

# Obter um usuário por ID
@router.get("/api/users/{user_id}", response_model=Optional[schemas.UserOut])
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Atualizar um usuário
@router.put("/api/users/{user_id}", response_model=Optional[schemas.UserUpdate])
def update_user(user_id: UUID, user: dict, db: Session = Depends(get_db)):
    user_data = jsonable_encoder(user)
    db_user = crud.update_user(db=db, user_id=user_id, user=user_data)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Deletar um usuário
@router.delete("/api/users/{user_id}", response_model=Optional[schemas.UserOut])
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    db_user = crud.delete_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post(path="/api/users/login")
def authenticate_user(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.authenticate_user(db, user_login.email, user_login.password)
    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = crud.generate_token_for_user(db, db_user.id)
    user_data = crud.get_user_by_id(db, db_user.id)
    return {
        "token": token_data["token"],
        "token_type": "bearer",
        "expiration_date": token_data["expiration_date"],
        "user": {
            "name": user_data.name,
            "email": user_data.email,
            "user_id": db_user.id,
            "user_type": user_data.user_type
        }
    }

@router.get("/api/users/{user_id}/file", response_class=Response)
def get_user_file(user_id: UUID, db: Session = Depends(get_db)):
    # Busca o usuário no banco
    db_user = crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not db_user.file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return Response(
        content=db_user.file,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={db_user.name}_document.pdf"}
    )
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, FastAPI, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, models, schemas
from ..database import get_db
import logging
from uuid import UUID
from app.utils import get_current_user,oauth2_scheme
from fastapi.security import OAuth2PasswordBearer
from fastapi.encoders import jsonable_encoder
from app.routers.items import send_email
router = APIRouter()

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

@router.post("/api/users/")
async def create_user(name: str = Form(...),
    document: str =Form(...),
    user_type: str =Form(...),
    email: str = Form(...),
    password: str = Form(...),
    category: str = Form(...),
    cep: str = Form(...),
    complete_adress: str = Form(...),
    institution: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)):

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="O arquivo deve ser um PDF")

    file_content = await file.read()

    user_data = schemas.UserCreate(
        name=name,
        email=email,
        password=password,
        document=document,
        user_type=user_type,
        category=category,
        cep=cep,
        complete_adress=complete_adress,
        institution=institution
    )
    db_user = crud.create_user(db=db, user=user_data, file_content=file_content)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já existe com o mesmo e-mail ou documento"
        )

    email_content = ("E-mail automático para confirmar que seu usuário foi criado com sucesso")

    subject = "Confirmação da criação do seu usuario no concurso do LAGIM"
    email_sended = send_email(to_email=email, subject=subject, content=email_content)
    if email_sended:
        return {"message": "Usuário cadastrado com sucesso "}
    else:
        return {"message": "Usuário cadastrado com sucesso porem ocorreu erro ao enviar e-mail de confirmação"}



@router.get("/api/users/", response_model=Optional[List[schemas.UserOut]])
def get_users(skip: int = 0,
              limit: int = 10,
              db: Session = Depends(get_db)):
    db_users = crud.get_users(db=db, skip=skip, limit=limit)
    if not db_users:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No users found.")
    return db_users

# Obter um usuário por ID
@router.get("/api/users/{user_id}", response_model=Optional[schemas.UserOut])
def get_user(user_id: UUID,
             db: Session = Depends(get_db),
             current_user: models.User = Depends(get_current_user)):
    db_user = crud.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Deletar um usuário
@router.delete("/api/users/{user_id}", response_model=Optional[schemas.UserOut])
def delete_user(user_id: UUID,
                db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    db_user = crud.delete_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/api/users/{user_id}",response_model=Optional[schemas.UserOut])
def update_password(user_id: UUID,
    password_data: schemas.UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):

    db_user = crud.update_password(db=db, user_id=user_id, password=password_data.password)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/api/users/{user_id}/file", response_class=Response)
def get_user_file(user_id: UUID, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
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
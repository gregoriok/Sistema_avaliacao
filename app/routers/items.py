from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, FastAPI, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, models, schemas
from ..database import get_db
from uuid import UUID
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.utils import  *
from app.schemas import RateRequest,getRateRequest,SendEmailRequest
import secrets
import string
router = APIRouter()

@router.post("/api/images/upload/")
async def upload_image(user_id: UUID,
    image: UploadFile = File(...),
    subcategory: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
):
    if image.content_type not in ["image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="O arquivo deve ser uma imagem JPG ou JPEG")

    if len(await image.read()) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="O arquivo deve ter no máximo 10MB")

    if subcategory not in MAX_UPLOADS:
        raise HTTPException(status_code=400, detail="Categoria inválida.")

    uploads = crud.get_images_by_user(db=db, user_id=user_id,subcategory=subcategory)
    if len(uploads) >= MAX_UPLOADS[subcategory]:
        raise HTTPException(
            status_code=400,
            detail=f"Você atingiu o limite de {MAX_UPLOADS[subcategory]} imagens para a categoria {subcategory}."
        )

    image.file.seek(0)
    image_content = await image.read()

    image_data = models.Image(
        user_id=user_id,
        image_data=image_content,
        subcategory=subcategory,
        description=description
    )
    db_image = crud.upload_image(db=db, image=image_data)
    if not db_image:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar a imagem")

    return {"message": "Imagem carregada com sucesso"}


@router.get("/api/images/{image_id}/", response_class=StreamingResponse)
async def get_image_by_id(image_id: UUID, db: Session = Depends(get_db)):
    # Recupera a imagem do banco de dados
    db_image = crud.get_image_by_id(db=db, image_id=image_id)

    if db_image is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    image_stream = BytesIO(db_image.image_data)
    return StreamingResponse(image_stream, media_type="image/jpeg")


@router.delete("/api/images/{image_id}", response_model=dict)
def delete_image(image_id: UUID, db: Session = Depends(get_db)):
    db_image = crud.delete_image(db=db, image_id=image_id)

    if db_image is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    return {"sucess": True, "message": "Imagem deletada com sucesso"}

@router.put("/api/images/{image_id}")
async def update_image(
        image_id: UUID,  # O ID vem diretamente da URL
        new_image: Optional[UploadFile] = File(None),
        description: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    updated_image = await crud.update_image(db=db, image_id=image_id, new_image=new_image, description=description)

    if not updated_image:
        raise HTTPException(status_code=404, detail="Image not found")

    return {"sucess": True, "message": "Imagem atualizada com sucesso"}

@router.get("/api/user/images/{user_id}")
async def get_image_by_user(user_id: UUID, subcategory: Optional[str] = None, db: Session = Depends(get_db)):
    db_images = crud.get_images_by_user(db=db, user_id=user_id, subcategory=subcategory)

    if not db_images:
        raise HTTPException(status_code=404, detail="Nenhuma imagem encontrada para este usuário")

    # Retorna uma lista de IDs das imagens
    image_ids = [{"image_id": str(image.id)} for image in db_images]

    return {"sucess": True,
            "images": image_ids}

@router.get("/api/images/{image_id}/details", response_model=dict)
async def get_image_details(image_id: UUID, db: Session = Depends(get_db)):
    db_image = crud.get_image_by_id(db=db, image_id=image_id)

    if db_image is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    print(db_image.subcategory)
    return {
        "image_id": str(db_image.id),
        "description": db_image.description,
        "subcategory": db_image.subcategory,
    }

@router.post("/api/users/{user_id}/rate/")
async def rate_user(rate_request: RateRequest, db: Session = Depends(get_db)):
    db_rating = crud.set_user_rating(
        db=db,
        evaluated_user_id=rate_request.evaluated_user_id,
        rating=rate_request.rating,
        evaluator_id=rate_request.evaluator_id,
        category=rate_request.category
    )
    if not db_rating:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atribuir a nota para o usuario"
        )
    return {"message": "Nota atribuida com sucesso."}

@router.post("/api/images/rate/")
def get_image_rate_by_category(rate_request: getRateRequest, db: Session = Depends(get_db)):

    rating = crud.get_image_rating(db=db, user_id=rate_request.user_id, category=rate_request.category)
    return {"rating": rating}

@router.post("/api/invite")
def send_mail(EmailRequest: SendEmailRequest, db: Session = Depends(get_db)):
    user_email = EmailRequest.email
    user_name = EmailRequest.name
    user = crud.get_user_by_email(db, email=user_email)
    if user:
        raise HTTPException(status_code=400, detail="Usuário já cadastrado.")

    password = generate_random_password()

    user_data = schemas.UserCreate(
        name=user_name,
        email=user_email,
        password=password,
        user_type='A',
        document='',
        category='4'
    )

    crud.create_user(db=db, user=user_data)

    email_content = f"Olá, você foi cadastrado como avaliador, acesse usando seu e-mail e sua nova senha : {password}"
    send_email(user_email, "Novo cadastro como Avaliador", email_content)

    return {"message": "Convite enviado com sucesso!"}


def send_email(to_email: str, subject: str, content: str):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    from_email = "gregoriosteinke@gmail.com"
    password = "zbgg djan hziq gszi"

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(content, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao enviar email: " + str(e))

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password
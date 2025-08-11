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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from app.routers.users import get_current_user
load_dotenv()
router = APIRouter()

@router.post("/api/images/upload/")
async def upload_image(
    image: UploadFile = File(...),
    user_id: UUID = Form(...),
    subcategory: str = Form(...),
    description: str = Form(...),
    title: str = Form(...),
    place: str = Form(...),
    equipment: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user = crud.get_user_by_id(db=db, user_id=user_id)
    ADM_TYPE = os.getenv("ADM_TYPE")
    if user.user_type == ADM_TYPE:
        raise HTTPException(status_code=400, detail="Usuários avaliadores não podem enviar imagens")

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
    print(title)
    print(place)
    image_data = models.Image(
        user_id=user_id,
        image_data=image_content,
        subcategory=subcategory,
        description=description,
        title=title,
        place=place,
        equipment=equipment
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


@router.get("/api/user/images/{user_id}")
async def get_image_by_user(user_id: UUID, subcategory: Optional[str] = None, db: Session = Depends(get_db),
                            current_user: models.User = Depends(get_current_user)):
    db_images = crud.get_images_by_user(db=db, user_id=user_id, subcategory=subcategory)

    if not db_images:
        raise HTTPException(status_code=404, detail="Nenhuma imagem encontrada para este usuário")

    # Retorna uma lista de IDs das imagens
    image_ids = [{"image_id": str(image.id)} for image in db_images]

    return {"sucess": True,
            "images": image_ids}

@router.get("/api/images/{image_id}/details", response_model=dict,)
async def get_image_details(image_id: UUID, db: Session = Depends(get_db),
                            current_user: models.User = Depends(get_current_user)):
    db_image = crud.get_image_by_id(db=db, image_id=image_id)
    print(db_image)
    if db_image is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    return {
        "image_id": str(db_image.id),
        "description": db_image.description,
        "subcategory": db_image.subcategory,
        "equipment": db_image.equipment,
        "place": db_image.place,
        "title": db_image.title
    }

@router.post("/api/users/rate/")
async def rate_user(rate_request: RateRequest,
                    db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    if len(rate_request.ratings) != 5:
        raise HTTPException(
            status_code=400,
            detail="Devem ser fornecidas exatamente 5 notas com critérios."
        )

    for item in rate_request.ratings:
        if not (0 <= item.score <= 20):
            raise HTTPException(
                status_code=400,
                detail=f"Nota para o critério '{item.criteria}' deve estar entre 0 e 20."
            )

    if rate_request.evaluated_user_id == rate_request.evaluator_id:
        raise HTTPException(
            status_code=400,
            detail="O avaliador nao pode se auto avaliar."
        )

    evaluator = crud.get_user_by_id(db=db, user_id=rate_request.evaluator_id)
    if evaluator.user_type != "A":
        raise HTTPException(
            status_code=400,
            detail="O usuario nao é avaliador."
        )

    try:
        crud.set_user_rating(
            db=db,
            evaluated_user_id=rate_request.evaluated_user_id,
            ratings=rate_request.ratings,
            evaluator_id=rate_request.evaluator_id,
            category=rate_request.category
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atribuir as notas."
        )
    return {"message": "Notas atribuídas com sucesso."}

@router.post("/api/images/rate/")
def get_image_rate_by_category(rate_request: getRateRequest, db: Session = Depends(get_db),
                               current_user: models.User = Depends(get_current_user)):
    ratings = crud.get_image_rating(db=db, user_id=str(rate_request.user_id), category=rate_request.category, evaluator_id=str(rate_request.evaluator_id))
    if ratings:
        return {"ratings": ratings}
    raise HTTPException(status_code=400, detail="Imagens não encontradas para este usuário nesta categoria")

@router.post("/api/invite")
def send_mail_api(EmailRequest: SendEmailRequest,
              db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_user)):
    user_email = EmailRequest.email
    user_name = EmailRequest.name
    user_document = EmailRequest.document
    user = crud.get_user_by_email_or_document(db, email=user_email,document=user_document)

    if user:
        raise HTTPException(status_code=400, detail="Usuário já cadastrado com este e-mail ou documento")

    password = generate_random_password()
    fake_adress = 'endereço dos avaliadores'
    fake_cep ='00000000'
    fake_Institution = 'Avaliador'

    user_data = schemas.UserCreate(
        name=user_name,
        email=user_email,
        password=password,
        user_type='A',
        document=user_document,
        category='4',
        institution='Avaliador',
        complete_adress='endereço dos avaliadores',
        cep='00000000'
    )
    try:
        crud.create_user(db=db, user=user_data)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Erro ao cadastrar usuario")

    email_content = f"Olá, você foi cadastrado como avaliador, acesse usando seu e-mail e sua nova senha : {password}"
    sended_email = send_email(user_email, "Novo cadastro como Avaliador no concurso do LAGIM", email_content)
    if sended_email:
        return {"message": "Convite enviado com sucesso!"}
    else:
        user = crud.get_user_by_email(db=db, email=user_email)
        crud.delete_user(user.id)
        raise HTTPException(status_code=500, detail="Erro ao enviar email")

def send_email(to_email: str, subject: str, content: str):
    from_email = os.getenv("EMAIL_GMAIL")
    password = os.getenv("SENHA_GMAIL")

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
        return False
    return True

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

@router.get("/api/avaliacoes/media-por-usuario")
def listar_medias_por_usuario(db: Session = Depends(get_db)):
    dados_medias = crud.get_user_media(db)
    if not dados_medias:
        raise HTTPException(status_code=404, detail="Nenhum dado de avaliação encontrado.")

    pdf_buffer = criar_pdf_medias(dados_medias)

    headers = {'Content-Disposition': 'attachment; filename="media_usuarios_endereco.pdf"'}

    return StreamingResponse(pdf_buffer, media_type='application/pdf', headers=headers)

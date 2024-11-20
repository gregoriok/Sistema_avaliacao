from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, FastAPI, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, models, schemas
from ..database import get_db
from uuid import UUID
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.utils import  *
from app.schemas import RateRequest,getRateRequest
router = APIRouter()

@router.post("/api/images/upload/")
async def upload_image(user_id: UUID,
    image: UploadFile = File(...),
    subcategory: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
):
    if image.content_type not in ["image/jpeg", "image/jpg"]:
        return HTTPException(status_code=400, detail="O arquivo deve ser uma imagem JPG ou JPEG")

    if len(await image.read()) > MAX_FILE_SIZE:
        return HTTPException(status_code=400, detail="O arquivo deve ter no máximo 10MB")

    if subcategory not in MAX_UPLOADS:
        return HTTPException(status_code=400, detail="Categoria inválida.")

    uploads = crud.get_images_by_user(db=db, user_id=user_id,subcategory=subcategory)
    if len(uploads) >= MAX_UPLOADS[subcategory]:
        return HTTPException(
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
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar a imagem")

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
        return HTTPException(status_code=404, detail="Imagem não encontrada")

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
        return HTTPException(status_code=404, detail="Nenhuma imagem encontrada para este usuário")

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

@router.post("/api/images/{image_id}/rate/")
async def rate_image(rate_request: RateRequest,db: Session = Depends(get_db)):

    db_rating = crud.set_image_rating(db=db,image_id=rate_request.image_id,rating=rate_request.rating,user_id=rate_request.user_id)
    if not db_rating:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atribuir a nota para a Imagem")

    return {"message": "Nota atribuída com sucesso."}

@router.post("/api/images/rate/")
def get_image_rate_by_category(rate_request: getRateRequest, db: Session = Depends(get_db)):

    rating = crud.get_image_rating(db=db, user_id=rate_request.user_id, subcategory=rate_request.subcategory)
    return {"rating": rating}

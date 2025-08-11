import io

from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from database import get_db

# Configurando o contexto do hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "CHAVESECRETEAGERADORDECHAVES"
ALGORITHM = "HS256"

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_UPLOADS = {"A": 1, "B": 3}
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Função para verificar se a senha está correta
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=5)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    current_time = datetime.utcnow()
    to_encode.update({"exp": expire, "iat": current_time})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
      Esta função é o seu "portão". Ela bloqueia a execução se o token for inválido.
      """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            # Token válido, mas sem o campo 'sub'
            raise HTTPException(status_code=401, detail="Could not validate credentials")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    return username

def criar_pdf_medias(data: list):
    """
    Cria um arquivo PDF em memória com os dados das médias e endereços dos usuários.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)

    elements = []
    styles = getSampleStyleSheet()

    titulo_texto = "Relatório de Média de Avaliações por Usuário"
    titulo = Paragraph(titulo_texto, styles['h1'])
    elements.append(titulo)
    elements.append(Spacer(1, 24))

    # --- CABEÇALHO DA TABELA ATUALIZADO ---
    table_data = [
        ['Nome', 'Categoria', 'Média Cat. A', 'Média Cat. B', 'Endereço Completo']
    ]

    # --- PREENCHIMENTO DAS LINHAS ATUALIZADO ---
    for item in data:
        nome = item.get('name', 'N/A')
        user_cat = item.get('user_category', 'N/A')
        media_a = str(item.get('categoria_a_media', '-'))
        media_b = str(item.get('categoria_b_media', '-'))
        # Pega o endereço do campo "complete_address"
        endereco = item.get('complete_address', 'Não informado')

        # Usar Paragraph permite que o texto quebre a linha automaticamente
        endereco_paragraph = Paragraph(endereco, styles['Normal'])

        table_data.append([nome, user_cat, media_a, media_b, endereco_paragraph])

    # --- LARGURA DAS COLUNAS AJUSTADA ---
    # A soma deve ser menor que a largura da página (aprox. 550 para letter)
    t = Table(table_data, colWidths=[120, 60, 70, 70, 230])

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.aliceblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Alinha o texto do endereço à esquerda para melhor leitura
        ('ALIGN', (4, 1), (4, -1), 'LEFT'),
    ])
    t.setStyle(style)

    elements.append(t)
    doc.build(elements)

    buffer.seek(0)
    return buffer

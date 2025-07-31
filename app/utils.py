from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
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

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=1)):
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

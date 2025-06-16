from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status

# Configurando o contexto do hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "CHAVESECRETEAGERADORDECHAVES"
ALGORITHM = "HS256"

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_UPLOADS = {"A": 1, "B": 3}


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

def verify_token_expiration(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], leeway=10)
        expiration_date = datetime.fromtimestamp(payload["exp"])
        if expiration_date < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token expirado")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

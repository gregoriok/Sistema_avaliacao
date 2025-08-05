from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
load_dotenv()
USUARIO_BANCO = os.getenv("USUARIO_BANCO")
SENHA_BANCO = os.getenv("SENHA_BANCO")
DATABASE_URL = f'postgresql://{USUARIO_BANCO}:{SENHA_BANCO}@localhost/evaluation_systems'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Função para obter a sessão de banco de dados
def get_db():
    db = SessionLocal()  # Criar a sessão
    try:
        yield db  # Passar a sessão para as dependências
    finally:
        db.close()  # Fechar a sessão após o uso

from fastapi import FastAPI, Depends
from app.routers import users, items
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(debug=True)

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}

app.include_router(users.router)
app.include_router(items.router)

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# Configuração do Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Permitir apenas as origens listadas
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos os métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos os headers
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0", port=8000)
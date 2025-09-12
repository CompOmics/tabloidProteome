from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1 import api_v1_router
import uvicorn

app = FastAPI()
port = 5600

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return "Hello, World!"
app.include_router(api_v1_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app, host='127.0.0.1', port=port)
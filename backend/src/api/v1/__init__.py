from fastapi import APIRouter

from src.api.v1.routes import *

api_v1_router = APIRouter()
api_v1_router.include_router(router)
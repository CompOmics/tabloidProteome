from fastapi import APIRouter

from api.v1.routes import *

api_v1_router = APIRouter()
api_v1_router.include_router(router)
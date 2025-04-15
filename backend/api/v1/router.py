from fastapi import APIRouter
from api.v1.routes import datasets, sse

api_router = APIRouter()
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(sse.router, prefix="/sse", tags=["sse"])

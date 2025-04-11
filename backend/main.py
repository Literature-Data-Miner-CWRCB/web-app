import logging
import logging.config
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from api.v1.router import api_router

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Load logging configuration
logging.config.fileConfig("config/logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI app.
    """
    # Initialize the vector space
    logger.info("Application starting up ...")

    yield
    # Perform shutdown tasks here
    logger.info("Application shutting down ...")


app = FastAPI(
    title="Literature Data Miner API",
    description="Backend API for Literature Data Miner",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=settings.FASTAPI_API_V1_STR + "/openapi.json",
    docs_url=settings.FASTAPI_API_V1_STR + "/docs",
)

# Allow CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.FASTAPI_API_V1_STR)


@app.get("/")
async def root():
    return {"message": "Welcome to the Web App API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

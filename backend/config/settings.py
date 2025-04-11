from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Literature Data Miner"
    FASTAPI_API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_PROJECT_URL: str
    SUPABASE_ANON_KEY: str

    # Groq
    GROQ_API_KEY: str

    # Google GenAI
    GOOGLE_GEMINI_API_KEY: str

    # Qdrant
    QDRANT_HOST_URL: str
    QDRANT_API_KEY: str

    # Redis Broker
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    class Config:
        env_file = ".env"


settings = Settings()

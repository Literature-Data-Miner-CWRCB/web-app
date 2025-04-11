from fastapi import HTTPException, status
from supabase.client import (
    Client,
    ClientOptions,
    create_client,
    AsyncClient,
    create_async_client,
    AsyncClientOptions,
)
from backend.settings.base import settings


def get_supabase_client() -> Client:
    supabase_client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
        options=ClientOptions(
            auto_refresh_token=True,
        ),
    )

    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase client not initialized",
        )

    return supabase_client


# https://supabase.com/docs/reference/python/select
async def get_supabase_async_client() -> AsyncClient:
    """for validation access_token init at life span event"""
    supabase_client = await create_async_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
        options=AsyncClientOptions(
            auto_refresh_token=True,
        ),
    )

    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase client not initialized",
        )

    return supabase_client

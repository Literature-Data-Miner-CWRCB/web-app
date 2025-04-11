# web-app/backend/api/dependencies.py
import logging
from pydantic import BaseModel, ConfigDict
from typing import Annotated, ClassVar
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from gotrue.types import User
from supabase.client import AsyncClient
from utils.supabase_utils import get_supabase_async_client

logger = logging.getLogger(__name__)

# security dependency injection
security_scheme = HTTPBearer(
    auto_error=False,
)
AuthCredDep = Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]

# Supabase dependency injection
SupabaseAsyncClientDep = Annotated[AsyncClient, Depends(get_supabase_async_client)]


class AuthContext(BaseModel):
    user: User
    access_token: str

    model_config: ClassVar[ConfigDict] = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
    )


async def get_auth_context(
    authorization: AuthCredDep,
    supabase_client: SupabaseAsyncClientDep,
) -> AuthContext:
    """Get current user from access_token and validate it with supabase"""
    # Verify jwt using supabase
    try:
        user_auth_response = await supabase_client.auth.get_user(
            jwt=authorization.credentials
        )
    except Exception as e:
        logger.error(f"Error verifying JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if not user_auth_response:
        logger.error("User not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return AuthContext(
        user=user_auth_response.user,
        access_token=authorization.credentials,
    )


CurrentAuthContext = Annotated[AuthContext, Depends(get_auth_context)]

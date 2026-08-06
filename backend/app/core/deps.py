import uuid
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)] = None,
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and validate the current authenticated user from JWT.
    Accepts token from Authorization header OR httpOnly cookie.
    """
    from app.modules.auth.models import Role, User  # avoid circular import

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": "Could not validate credentials", "details": None},
        headers={"WWW-Authenticate": "Bearer"},
    )

    raw_token = (token.credentials if token else None) or access_token
    if not raw_token:
        raise credentials_exception

    try:
        payload = decode_token(raw_token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id, User.is_active)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception

    return user



async def get_current_tenant(
    restaurant_id: str | None = Query(
        None, description="Super-admin only: override tenant context"
    ),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    """
    Get the restaurant (tenant) context for the current user.
    Enforces tenant isolation by always using the user's assigned restaurant_id.
    Super admins can override via the ?restaurant_id= query param.
    """
    from app.modules.tenancy.models import Restaurant

    user_roles = {r.name for r in current_user.roles}
    is_super_admin = "super_admin" in user_roles

    # Determine the target restaurant ID
    target_restaurant_id = current_user.restaurant_id

    # Allow super_admin to override the restaurant context
    if is_super_admin and restaurant_id:
        target_restaurant_id = restaurant_id

    if not target_restaurant_id:
        if is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "TENANT_REQUIRED", "message": "Super-admin must specify restaurant_id override parameter", "details": None},
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NO_TENANT", "message": "User does not belong to any restaurant", "details": None},
        )

    result = await db.execute(
        select(Restaurant).where(
            Restaurant.id == target_restaurant_id,
            Restaurant.is_active,
        )
    )
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Restaurant not found", "details": None},
        )
    return restaurant


async def get_tenant_public(
    restaurant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the restaurant (tenant) context for public endpoints.
    Loads and returns the Restaurant if it exists and is_active, else 404.
    Does not require authentication.
    """
    from app.modules.tenancy.models import Restaurant
    result = await db.execute(
        select(Restaurant).where(
            Restaurant.id == restaurant_id,
            Restaurant.is_active,
        )
    )
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Restaurant not found", "details": None},
        )
    return restaurant



def require_role(*roles: str):
    """Dependency factory: ensure current user has one of the specified roles."""
    async def role_checker(current_user=Depends(get_current_user)):
        user_role_names = {r.name for r in current_user.roles}
        if not user_role_names.intersection(set(roles)) and "super_admin" not in user_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Required role(s): {', '.join(roles)}",
                    "details": None,
                },
            )
        return current_user
    return role_checker


# Convenient type aliases
CurrentUser = Annotated[object, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]

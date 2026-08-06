import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.core.limiter import limiter
from app.modules.auth.schemas import (
    EmailVerifyRequest,
    EmailVerifyVerify,
    MFASetupResponse,
    MFAVerify,
    PasswordReset,
    PasswordResetRequest,
    PhoneOTPRequest,
    PhoneOTPVerify,
    RegisterAndSetup,
    SessionResponse,
    StaffRegister,
    Token,
    TokenRefreshRequest,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix='/auth', tags=['Authentication'])


def _set_auth_cookies(response: Response, token_data: Token) -> None:
    is_secure = settings.APP_ENV == "production"
    response.set_cookie('access_token', token_data.access_token, httponly=True, samesite='lax', secure=is_secure, max_age=15*60)
    response.set_cookie('refresh_token', token_data.refresh_token, httponly=True, samesite='lax', secure=is_secure, max_age=7*24*60*60)


# ── Registration & Login ──────────────────────────────────────────────────────
@router.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(request: Request, schema: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user (becomes Owner by default)."""
    return await AuthService.register_user(db, schema)


@router.post('/register-and-setup', response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register_and_setup(
    request: Request,
    schema: 'RegisterAndSetup',
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    One-shot onboarding: registers the owner, creates their restaurant + default branch,
    and returns a full Token (with auth cookies) so the user is immediately logged in.
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get('user-agent')
    token_data = await AuthService.register_and_setup(db, schema, ip=ip, user_agent=ua)
    _set_auth_cookies(response, token_data)
    return token_data


@router.post('/register-staff', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register_staff(
    request: Request,
    schema: StaffRegister,
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new staff member (Manager, Cashier, Waiter, Kitchen) under the current restaurant.
    Requires owner, manager, or super_admin permissions.
    """
    user_roles = {r.name for r in current_user.roles}
    is_super_admin = "super_admin" in user_roles

    if not is_super_admin:
        if not current_user.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": "Creator must belong to a restaurant to add staff", "details": None}
            )
        schema.restaurant_id = current_user.restaurant_id
    else:
        if not schema.restaurant_id:
            if current_user.restaurant_id:
                schema.restaurant_id = current_user.restaurant_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "BAD_REQUEST", "message": "restaurant_id is required for super_admin without a restaurant context", "details": None}
                )

    return await AuthService.register_staff(db, schema)


@router.post('/login', response_model=Token)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    schema: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user. Supports optional TOTP for MFA-enabled accounts."""
    ip = request.client.host if request.client else None
    ua = request.headers.get('user-agent')
    token_data = await AuthService.login_user(db, schema, ip=ip, user_agent=ua)
    _set_auth_cookies(response, token_data)
    return token_data


@router.post('/token', response_model=Token, include_in_schema=True)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def token_for_swagger(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2-compatible token endpoint for Swagger UI / Postman.
    Use your **email** in the `username` field.
    """
    from app.modules.auth.schemas import UserLogin
    schema = UserLogin(email=form_data.username, password=form_data.password)
    ip = request.client.host if request.client else None
    ua = request.headers.get('user-agent')
    token_data = await AuthService.login_user(db, schema, ip=ip, user_agent=ua)
    _set_auth_cookies(response, token_data)
    return token_data


@router.post('/refresh', response_model=Token)
async def refresh(
    response: Response,
    schema: TokenRefreshRequest | None = None,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Rotate access + refresh tokens."""
    token_str = (schema.refresh_token if schema else None) or refresh_token
    if not token_str:
        raise HTTPException(status_code=401, detail={'code': 'UNAUTHORIZED', 'message': 'Refresh token missing', 'details': None})
    token_data = await AuthService.refresh_tokens(db, token_str)
    _set_auth_cookies(response, token_data)
    return token_data


@router.post('/logout', status_code=200)
async def logout(response: Response, refresh_token: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    """Revoke current session and clear cookies."""
    if refresh_token:
        try:
            from sqlalchemy import select

            from app.modules.auth.models import UserSession
            result = await db.execute(select(UserSession).where(UserSession.session_token == refresh_token))
            session = result.scalar_one_or_none()
            if session:
                session.is_active = False
                await db.commit()
        except Exception:
            pass
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return {'message': 'Logged out successfully'}


@router.get('/me', response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


# ── Sessions ──────────────────────────────────────────────────────────────────
@router.get('/sessions', response_model=list[SessionResponse])
async def list_sessions(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all active sessions for the current user."""
    return await AuthService.list_sessions(db, current_user.id)


@router.delete('/sessions/{session_id}', status_code=204)
async def revoke_session(
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session (remote logout)."""
    await AuthService.revoke_session(db, current_user.id, session_id)


@router.delete('/sessions', status_code=204)
async def revoke_all_sessions(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Revoke ALL sessions except the current one (force logout everywhere)."""
    await AuthService.revoke_all_sessions(db, current_user.id)


# ── Phone OTP ─────────────────────────────────────────────────────────────────
@router.post('/otp/send', status_code=200)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def send_otp(request: Request, schema: PhoneOTPRequest, db: AsyncSession = Depends(get_db)):
    """Send a 6-digit OTP to the given phone number (stored in Redis for 5 min)."""
    otp = await AuthService.send_phone_otp(db, schema.phone)
    if settings.APP_ENV == "development":
        return {'message': 'OTP sent', 'dev_otp': otp}
    return {'message': 'OTP sent'}


@router.post('/otp/verify', response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def verify_otp(request: Request, schema: PhoneOTPVerify, db: AsyncSession = Depends(get_db)):
    """Verify OTP and mark user phone as verified."""
    user = await AuthService.verify_phone_otp(db, schema.phone, schema.otp)
    return user


# ── Email Verification ────────────────────────────────────────────────────────
@router.post('/verify-email/request', status_code=200)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def request_email_verification(
    request: Request,
    schema: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate and send an email verification token using Brevo."""
    try:
        user = await AuthService.get_user_by_email(db, schema.email)
        token = await AuthService.send_email_verification(db, user.id)
        if settings.APP_ENV == "development":
            return {'message': 'Verification email sent', 'dev_token': token}
        return {'message': 'Verification email sent'}
    except Exception:
        # If user not found, just return success to avoid email enumeration
        return {'message': 'Verification email sent'}


@router.post("/verify-email/verify", summary="Verify Email", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def verify_email(
    request: Request,
    schema: EmailVerifyVerify,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify the email OTP and mark the user email as verified (is_verified = true).
    """
    return await AuthService.verify_email_token(db, schema.email, schema.otp)



# ── Password Reset ────────────────────────────────────────────────────────────
@router.post('/password-reset/request', status_code=200)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def request_password_reset(request: Request, schema: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request a password reset token (emailed in production)."""
    token = await AuthService.request_password_reset(db, schema.email)
    if settings.APP_ENV == "development":
        return {'message': 'Reset token generated', 'dev_token': token}
    return {'message': 'Reset token generated'}


@router.post('/password-reset/reset', status_code=200)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def reset_password(request: Request, schema: PasswordReset, db: AsyncSession = Depends(get_db)):
    """Submit a new password using the reset token."""
    await AuthService.reset_password(db, schema.email, schema.otp, schema.new_password)
    return {'message': 'Password reset successfully'}


# ── MFA (TOTP) ────────────────────────────────────────────────────────────────
@router.post('/mfa/setup', response_model=MFASetupResponse)
async def mfa_setup(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a TOTP secret and QR URI for the current user."""
    return await AuthService.setup_mfa(db, current_user.id)


@router.post('/mfa/enable', status_code=200)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def mfa_enable(request: Request, schema: MFAVerify, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Enable MFA after verifying the TOTP code from the authenticator app."""
    await AuthService.enable_mfa(db, current_user.id, schema.totp_code)
    return {'message': 'MFA enabled successfully'}


@router.post('/mfa/disable', status_code=200)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def mfa_disable(request: Request, schema: MFAVerify, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Disable MFA after re-verifying the TOTP code."""
    await AuthService.disable_mfa(db, current_user.id, schema.totp_code)
    return {'message': 'MFA disabled successfully'}


# ── Dev seed ──────────────────────────────────────────────────────────────────
@router.post('/seed', status_code=200)
async def seed_roles(
    current_user=Depends(require_role('super_admin')),
    db: AsyncSession = Depends(get_db)
):
    await AuthService.seed_roles_and_permissions(db)
    return {'message': 'Roles and permissions seeded'}


# ── Staff Management ──────────────────────────────────────────────────────────
@router.get('/staff', response_model=list[UserResponse])
async def list_staff(
    restaurant_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    """
    List staff members belonging to a specific restaurant tenant with pagination.
    Filters strictly by target restaurant_id to prevent multi-tenant data leakage.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.auth.models import Role, User

    user_roles = {r.name for r in current_user.roles}
    is_super_admin = 'super_admin' in user_roles

    target_restaurant_id = current_user.restaurant_id
    if is_super_admin and restaurant_id:
        target_restaurant_id = restaurant_id

    if not target_restaurant_id:
        return []

    offset = (page - 1) * page_size
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.is_active)
    )
    if target_restaurant_id:
        stmt = stmt.where(User.restaurant_id == target_restaurant_id)

    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all())



@router.delete('/staff/{user_id}', status_code=204)
async def deactivate_staff(
    user_id: uuid.UUID,
    current_user=Depends(require_role('owner', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate (soft-delete) a staff member. Owners can only deactivate
    members of their own restaurant. Super admins can deactivate anyone.
    """
    from sqlalchemy import select

    from app.modules.auth.models import User

    user_roles = {r.name for r in current_user.roles}
    is_super_admin = 'super_admin' in user_roles

    stmt = select(User).where(User.id == user_id)
    if not is_super_admin:
        stmt = stmt.where(User.restaurant_id == current_user.restaurant_id)

    result = await db.execute(stmt)
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail={'code': 'NOT_FOUND', 'message': 'User not found', 'details': None})

    if not is_super_admin:
        # Owners cannot deactivate themselves
        if target.id == current_user.id:
            raise HTTPException(status_code=400, detail={'code': 'BAD_REQUEST', 'message': 'Cannot deactivate yourself', 'details': None})

    target.is_active = False
    await db.commit()

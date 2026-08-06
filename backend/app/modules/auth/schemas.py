import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Role and Permission schemas ──────────────────────────────────────────────

class PermissionBase(BaseModel):
    name: str
    description: str | None = None


class PermissionResponse(PermissionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleResponse(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    permissions: list[PermissionResponse] = []


# ── User schemas ─────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: str | None = None


class StaffRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: str | None = None
    role: str = Field(..., pattern="^(manager|cashier|waiter|kitchen)$")
    restaurant_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None  # for MFA


class RegisterAndSetup(BaseModel):
    """One-shot onboarding payload: user + restaurant details."""
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str | None = None
    password: str = Field(..., min_length=6)
    restaurant_name: str = Field(..., min_length=2)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None = None
    phone_verified: bool = False
    mfa_enabled: bool = False
    is_active: bool
    is_verified: bool
    restaurant_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    created_at: datetime
    roles: list[RoleResponse] = []


# ── Token schemas ─────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ── OTP & Password Reset & MFA & Session schemas ────────────────────────────────

class PhoneOTPRequest(BaseModel):
    phone: str


class PhoneOTPVerify(BaseModel):
    phone: str
    otp: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(..., min_length=6)


class EmailVerifyRequest(BaseModel):
    email: EmailStr


class EmailVerifyVerify(BaseModel):
    email: EmailStr
    otp: str



class MFASetupResponse(BaseModel):
    secret: str
    qr_uri: str


class MFAVerify(BaseModel):
    totp_code: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ip_address: str | None = None
    user_agent: str | None = None
    is_active: bool
    created_at: datetime
    last_active: datetime

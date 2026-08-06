import secrets
import uuid

import jwt
import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import AppException, ConflictError, NotFoundError, UnauthorizedError
from app.core.notifications import NotificationService
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import Permission, Role, User, UserSession
from app.modules.auth.schemas import (
    MFASetupResponse,
    StaffRegister,
    Token,
    UserLogin,
    UserRegister,
)

OTP_TTL = 300        # 5 minutes
RESET_TTL = 900      # 15 minutes


class AuthService:
    # ── Helpers ──────────────────────────────────────────────────────────
    @staticmethod
    async def _get_redis():
        try:
            from app.core.redis import get_redis
            return await get_redis()
        except Exception:
            return None

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id) -> User | None:
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id, User.is_active)
        )
        return result.scalar_one_or_none()

    # ── Register ─────────────────────────────────────────────────────────
    @staticmethod
    async def register_user(db: AsyncSession, schema: UserRegister) -> User:
        existing = await AuthService.get_user_by_email(db, schema.email)
        if existing:
            raise ConflictError('Email is already registered')

        hashed_pwd = hash_password(schema.password)

        result = await db.execute(select(Role).where(Role.name == 'owner'))
        owner_role = result.scalar_one_or_none()
        if not owner_role:
            await AuthService.seed_roles_and_permissions(db)
            result = await db.execute(select(Role).where(Role.name == 'owner'))
            owner_role = result.scalar_one_or_none()

        new_user = User(
            email=schema.email,
            hashed_password=hashed_pwd,
            full_name=schema.full_name,
            phone=schema.phone,
            is_active=True,
            is_verified=False,
            roles=[owner_role] if owner_role else [],
        )
        db.add(new_user)
        await db.commit()

        # Generate and send 6-digit OTP via email using the shared function
        try:
            await AuthService.send_email_verification(db, new_user.id)
        except Exception:
            # We don't want to fail registration just because email sending failed
            pass


        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == new_user.id)
        )
        return result.scalar_one()

    @staticmethod
    async def register_and_setup(
        db: AsyncSession,
        schema,  # RegisterAndSetup
        ip: str = None,
        user_agent: str = None,
    ) -> 'Token':
        """
        One-shot registration: create owner user + restaurant + default branch,
        then immediately issue auth tokens so the user is logged in.
        """
        existing = await AuthService.get_user_by_email(db, schema.email)
        if existing:
            raise ConflictError('Email is already registered')

        hashed_pwd = hash_password(schema.password)

        # Ensure owner role exists
        result = await db.execute(select(Role).where(Role.name == 'owner'))
        owner_role = result.scalar_one_or_none()
        if not owner_role:
            await AuthService.seed_roles_and_permissions(db)
            result = await db.execute(select(Role).where(Role.name == 'owner'))
            owner_role = result.scalar_one_or_none()

        new_user = User(
            email=schema.email,
            hashed_password=hashed_pwd,
            full_name=schema.full_name,
            phone=schema.phone,
            is_active=True,
            is_verified=False,
            roles=[owner_role] if owner_role else [],
        )
        db.add(new_user)
        await db.flush()  # get new_user.id without full commit

        # Create restaurant + link to user
        import re

        from app.modules.tenancy.models import Branch, Restaurant, RestaurantSettings
        slug_base = re.sub(r'[^a-z0-9]+', '-', schema.restaurant_name.lower()).strip('-')
        slug = slug_base
        # Ensure slug uniqueness
        counter = 1
        while True:
            existing_slug = await db.execute(
                select(Restaurant).where(Restaurant.slug == slug)
            )
            if not existing_slug.scalar_one_or_none():
                break
            slug = f'{slug_base}-{counter}'
            counter += 1

        restaurant = Restaurant(name=schema.restaurant_name, slug=slug)
        db.add(restaurant)
        await db.flush()

        # Link user → restaurant
        new_user.restaurant_id = restaurant.id

        # Create default settings + branch
        db.add(RestaurantSettings(restaurant_id=restaurant.id))
        db.add(Branch(restaurant_id=restaurant.id, name=f'{schema.restaurant_name} — Main Branch'))
        await db.commit()

        # Send verification email (non-blocking)
        try:
            await AuthService.send_email_verification(db, new_user.id)
        except Exception:
            pass

        # Create session and return token
        access_token  = create_access_token(data={'sub': str(new_user.id)})
        refresh_token = create_refresh_token(data={'sub': str(new_user.id)})

        session = UserSession(
            user_id=new_user.id,
            session_token=refresh_token,
            ip_address=ip,
            user_agent=user_agent,
            is_active=True,
        )
        db.add(session)
        await db.commit()

        # Reload with roles for schema serialisation
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == new_user.id)
        )
        user = result.scalar_one()
        return Token(access_token=access_token, refresh_token=refresh_token, user=user)

    @staticmethod
    async def register_staff(db: AsyncSession, schema: StaffRegister) -> User:
        existing = await AuthService.get_user_by_email(db, schema.email)
        if existing:
            raise ConflictError('Email is already registered')

        hashed_pwd = hash_password(schema.password)

        result = await db.execute(select(Role).where(Role.name == schema.role))
        staff_role = result.scalar_one_or_none()
        if not staff_role:
            await AuthService.seed_roles_and_permissions(db)
            result = await db.execute(select(Role).where(Role.name == schema.role))
            staff_role = result.scalar_one_or_none()
            if not staff_role:
                raise NotFoundError(f'Role {schema.role} not found')

        new_user = User(
            email=schema.email,
            hashed_password=hashed_pwd,
            full_name=schema.full_name,
            phone=schema.phone,
            is_active=True,
            is_verified=False,
            restaurant_id=schema.restaurant_id,
            branch_id=schema.branch_id,
            roles=[staff_role] if staff_role else [],
        )
        db.add(new_user)
        await db.commit()

        try:
            await AuthService.send_email_verification(db, new_user.id)
        except Exception:
            pass

        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == new_user.id)
        )
        return result.scalar_one()

    # ── Login ─────────────────────────────────────────────────────────────
    @staticmethod
    async def login_user(
        db: AsyncSession,
        schema: UserLogin,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Token:
        user = await AuthService.get_user_by_email(db, schema.email)
        if not user or not verify_password(schema.password, user.hashed_password):
            raise UnauthorizedError('Incorrect email or password')
        if not user.is_active:
            raise UnauthorizedError('User account is inactive')

        # MFA check
        if user.mfa_enabled:
            if not schema.totp_code:
                raise UnauthorizedError('TOTP code required for MFA-enabled account')
            totp = pyotp.TOTP(user.mfa_secret)
            if not totp.verify(schema.totp_code, valid_window=1):
                raise UnauthorizedError('Invalid TOTP code')

        access_token  = create_access_token(data={'sub': str(user.id)})
        refresh_token = create_refresh_token(data={'sub': str(user.id)})

        # Record session
        session = UserSession(
            user_id=user.id,
            session_token=refresh_token,
            ip_address=ip,
            user_agent=user_agent,
            is_active=True,
        )
        db.add(session)
        await db.commit()

        # Reload user roles for schema
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user.id)
        )
        user = result.scalar_one()

        return Token(access_token=access_token, refresh_token=refresh_token, user=user)

    # ── Refresh ───────────────────────────────────────────────────────────
    @staticmethod
    async def refresh_tokens(db: AsyncSession, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
            if payload.get('type') != 'refresh':
                raise UnauthorizedError('Invalid token type')
            user_id = payload.get('sub')
        except jwt.PyJWTError:
            raise UnauthorizedError('Invalid or expired refresh token')

        # Verify session is still active
        session_result = await db.execute(
            select(UserSession).where(
                UserSession.session_token == refresh_token,
                UserSession.is_active,
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise UnauthorizedError('Session revoked or not found')

        user = await AuthService.get_user_by_id(db, user_id)
        if not user:
            raise UnauthorizedError('User not found')

        new_access  = create_access_token(data={'sub': str(user.id)})
        new_refresh = create_refresh_token(data={'sub': str(user.id)})

        # Rotate session token
        session.session_token = new_refresh
        await db.commit()

        return Token(access_token=new_access, refresh_token=new_refresh, user=user)

    # ── Sessions ──────────────────────────────────────────────────────────
    @staticmethod
    async def list_sessions(db: AsyncSession, user_id) -> list:
        result = await db.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_active)
            .order_by(UserSession.last_active.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke_session(db: AsyncSession, user_id, session_id) -> None:
        result = await db.execute(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError('Session not found')
        session.is_active = False
        await db.commit()

    @staticmethod
    async def revoke_all_sessions(db: AsyncSession, user_id) -> None:
        result = await db.execute(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.is_active)
        )
        for s in result.scalars().all():
            s.is_active = False
        await db.commit()

    # ── Phone OTP ─────────────────────────────────────────────────────────
    @staticmethod
    async def send_phone_otp(db: AsyncSession, phone: str) -> str:
        redis = await AuthService._get_redis()
        otp = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP
        key = f'otp:phone:{phone}'
        if redis:
            await redis.set(key, otp, ex=OTP_TTL)

        # Trigger real SMS dispatcher (2Factor / Twilio)
        await NotificationService.send_sms_otp(phone, otp)

        return otp

    @staticmethod
    async def verify_phone_otp(db: AsyncSession, phone: str, otp: str) -> User:
        redis = await AuthService._get_redis()
        key = f'otp:phone:{phone}'
        stored = None
        if redis:
            stored = await redis.get(key)
            if stored:
                stored = stored.decode() if isinstance(stored, bytes) else stored

        if not stored or stored != otp:
            raise UnauthorizedError('Invalid or expired OTP')

        # Mark phone as verified
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.phone == phone)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError('No user found with this phone number')

        user.phone_verified = True
        if redis:
            await redis.delete(key)
        await db.commit()
        return user

    # ── Password Reset ────────────────────────────────────────────────────
    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> str:
        user = await AuthService.get_user_by_email(db, email)
        if not user:
            # Don't leak user existence — silently return empty
            return ''

        # Generate 6-digit numeric OTP
        otp = str(secrets.randbelow(900000) + 100000)  # 100000–999999
        redis = await AuthService._get_redis()
        if redis:
            await redis.set(f'pwd_reset:{email}:{otp}', str(user.id), ex=RESET_TTL)

        # Send password reset email using Brevo
        reset_subject = "DineOS - Password Reset OTP"
        reset_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
          <h3>Hello {user.full_name},</h3>
          <p>We received a request to reset your DineOS password.</p>
          <p>Use the 6-digit OTP below to reset your password:</p>
          <div style="font-size: 36px; font-weight: bold; letter-spacing: 12px; background: #f3f4f6;
                      padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">{otp}</div>
          <p style="color: #888;">This OTP is valid for <strong>15 minutes</strong>. Do not share it with anyone.</p>
          <p>If you did not request this, please ignore this email.</p>
          <br/>
          <p>Best Regards,<br/><strong>DineOS Support Team</strong></p>
        </div>
        """
        await NotificationService.send_email(email, reset_subject, reset_html)
        return otp

    @staticmethod
    async def reset_password(db: AsyncSession, email: str, otp: str, new_password: str) -> None:
        redis = await AuthService._get_redis()
        user_id = None
        if redis:
            val = await redis.get(f'pwd_reset:{email}:{otp}')
            if val:
                user_id = val.decode() if isinstance(val, bytes) else val

        if not user_id:
            raise UnauthorizedError('Invalid or expired OTP')

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError('User not found')

        user.hashed_password = hash_password(new_password)
        if redis:
            await redis.delete(f'pwd_reset:{email}:{otp}')
        # Revoke all sessions for security
        await AuthService.revoke_all_sessions(db, user.id)
        await db.commit()

    # ── MFA (TOTP) ────────────────────────────────────────────────────────
    @staticmethod
    async def setup_mfa(db: AsyncSession, user_id) -> MFASetupResponse:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError('User not found')
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        await db.commit()
        totp = pyotp.TOTP(secret)
        qr_uri = totp.provisioning_uri(name=user.email, issuer_name='DineOS')
        return MFASetupResponse(secret=secret, qr_uri=qr_uri)

    @staticmethod
    async def enable_mfa(db: AsyncSession, user_id, totp_code: str) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.mfa_secret:
            raise AppException(400, 'MFA_NOT_SETUP', 'Call /auth/mfa/setup first')
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise UnauthorizedError('Invalid TOTP code')
        user.mfa_enabled = True
        await db.commit()

    @staticmethod
    async def disable_mfa(db: AsyncSession, user_id, totp_code: str) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.mfa_enabled:
            raise AppException(400, 'MFA_NOT_ENABLED', 'MFA is not enabled')
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise UnauthorizedError('Invalid TOTP code')
        user.mfa_enabled = False
        user.mfa_secret = None
        await db.commit()

    # ── Seed ─────────────────────────────────────────────────────────────
    @staticmethod
    async def seed_roles_and_permissions(db: AsyncSession) -> None:
        permissions_list = [
            ('manage_restaurant', 'Full management of restaurant and branch configurations'),
            ('manage_menu', 'Manage menu categories, items and pricing'),
            ('place_order', 'Create and modify orders'),
            ('view_kds', 'View and update KDS screen'),
            ('manage_billing', 'Generate invoices and process payments'),
            ('manage_inventory', 'Manage stock, ingredients and recipes'),
            ('view_reports', 'View sales and business analytics reports'),
            ('manage_crm', 'Manage customer profiles and loyalty'),
        ]
        roles_permissions_map = {
            'super_admin': ['manage_restaurant', 'manage_menu', 'place_order', 'view_kds', 'manage_billing', 'manage_inventory', 'view_reports', 'manage_crm'],
            'owner':       ['manage_restaurant', 'manage_menu', 'place_order', 'view_kds', 'manage_billing', 'manage_inventory', 'view_reports', 'manage_crm'],
            'manager':     ['manage_menu', 'place_order', 'view_kds', 'manage_billing', 'manage_inventory', 'view_reports'],
            'cashier':     ['place_order', 'view_kds', 'manage_billing'],
            'waiter':      ['place_order'],
            'kitchen':     ['view_kds'],
            'customer':    ['place_order'],
        }

        db_permissions = {}
        for name, desc in permissions_list:
            result = await db.execute(select(Permission).where(Permission.name == name))
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(name=name, description=desc)
                db.add(perm)
            db_permissions[name] = perm
        await db.flush()

        for role_name, perm_names in roles_permissions_map.items():
            result = await db.execute(
                select(Role).options(selectinload(Role.permissions)).where(Role.name == role_name)
            )
            role = result.scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=f'Default {role_name} role')
                db.add(role)
            role.permissions = [db_permissions[p] for p in perm_names if p in db_permissions]
        await db.commit()

    # ── Email Verification ────────────────────────────────────────────────
    @staticmethod
    async def send_email_verification(db: AsyncSession, user_id: uuid.UUID) -> str:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError('User not found')

        # Generate 6-digit numeric OTP
        otp = str(secrets.randbelow(900000) + 100000)  # 100000–999999
        redis = await AuthService._get_redis()
        if redis:
            # OTP expires in 10 minutes (600 seconds)
            await redis.set(f'email_verify:{user.email}:{otp}', str(user.id), ex=600)

        # Send email using Brevo
        subject = "DineOS - Your Email Verification OTP"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
          <h3>Hello {user.full_name},</h3>
          <p>Use the 6-digit OTP below to verify your email address:</p>
          <div style="font-size: 36px; font-weight: bold; letter-spacing: 12px; background: #f3f4f6;
                      padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">{otp}</div>
          <p style="color: #888;">This OTP is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
          <br/>
          <p>Best Regards,<br/><strong>DineOS Support Team</strong></p>
        </div>
        """
        await NotificationService.send_email(user.email, subject, html)
        return otp

    @staticmethod
    async def verify_email_token(db: AsyncSession, email: str, otp: str) -> User:
        redis = await AuthService._get_redis()
        user_id = None
        if redis:
            val = await redis.get(f'email_verify:{email}:{otp}')
            if val:
                user_id = val.decode() if isinstance(val, bytes) else val

        if not user_id:
            raise UnauthorizedError('Invalid or expired verification token')

        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError('User not found')

        user.is_verified = True
        if redis:
            await redis.delete(f'email_verify:{email}:{otp}')
        await db.commit()
        return user


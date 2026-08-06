
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # gracefully ignore unknown env vars
    )

    # App
    APP_NAME: str = "Restaurant SaaS"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:5173"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres@127.0.0.1:5433/restaurant_saas"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres@127.0.0.1:5433/restaurant_saas"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("SYNC_DATABASE_URL", mode="before")
    @classmethod
    def validate_sync_database_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        return v

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "supersecretjwtkey-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    _INSECURE_JWT_DEFAULT: str = "supersecretjwtkey-change-in-production"

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> "Settings":
        """Fail-fast: refuse to start in production with default secrets."""
        if self.APP_ENV == "production":
            if self.JWT_SECRET_KEY == self._INSECURE_JWT_DEFAULT:
                raise ValueError(
                    "FATAL: JWT_SECRET_KEY must be set to a strong random secret in production. "
                    "Set the JWT_SECRET_KEY environment variable before starting the server."
                )
            if self.RAZORPAY_KEY_SECRET == "placeholder_secret":
                raise ValueError("FATAL: RAZORPAY_KEY_SECRET cannot be placeholder in production.")
            if self.RAZORPAY_WEBHOOK_SECRET == "placeholder_webhook_secret":
                raise ValueError("FATAL: RAZORPAY_WEBHOOK_SECRET cannot be placeholder in production.")
        return self

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # Celery
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/2"

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder"
    RAZORPAY_KEY_SECRET: str = "placeholder_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "placeholder_webhook_secret"

    # Rate limiting
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # Email (Brevo / SendGrid / SMTP)
    EMAIL_PROVIDER: str = "brevo"
    BREVO_API_KEY: str | None = None
    BREVO_SENDER_EMAIL: str | None = None
    EMAIL_FROM: str | None = None
    EMAIL_SEND_TIMEOUT: int = 60

    # Cloudinary (image uploads)
    CLOUDINARY_URL: str | None = None
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None

    # AWS S3 (storage)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str | None = None
    AWS_STORAGE_BUCKET_NAME: str | None = None

    # Twilio (SMS)
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_PHONE_NUMBER: str | None = None

    # 2Factor OTP (India)
    TWO_FACTOR_API_KEY: str | None = None

    # WhatsApp (Meta Business API)
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_TOKEN: str | None = None

    # Sentry (Observability)
    SENTRY_DSN: str | None = None


settings = Settings()

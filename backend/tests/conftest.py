"""
Pytest fixtures and configuration for the DineOS backend test suite.
"""
import os
import pytest

# Override env vars before any app import so settings pick them up.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "testsecretkey-not-for-production-use")
os.environ.setdefault("REFRESH_SECRET_KEY", "testrefreshsecret-not-for-production-use")

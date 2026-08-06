import pytest
from app.core.config import Settings

def test_production_jwt_secret_validation():
    # Should not raise exception in development
    Settings(APP_ENV="development", JWT_SECRET_KEY="supersecretjwtkey-change-in-production")
    
    # Should raise ValueError in production if using default key
    with pytest.raises(ValueError, match="FATAL: JWT_SECRET_KEY must be set to a strong random secret"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="supersecretjwtkey-change-in-production", RAZORPAY_KEY_SECRET="valid", RAZORPAY_WEBHOOK_SECRET="valid")

    # Should pass in production if using a secure key
    Settings(APP_ENV="production", JWT_SECRET_KEY="a-very-long-secure-random-key-32-chars", RAZORPAY_KEY_SECRET="valid", RAZORPAY_WEBHOOK_SECRET="valid")

def test_production_razorpay_secret_validation():
    # Should raise ValueError in production if using default razorpay key secret
    with pytest.raises(ValueError, match="FATAL: RAZORPAY_KEY_SECRET cannot be placeholder in production."):
        Settings(APP_ENV="production", JWT_SECRET_KEY="valid-jwt", RAZORPAY_KEY_SECRET="placeholder_secret", RAZORPAY_WEBHOOK_SECRET="valid")

    # Should raise ValueError in production if using default razorpay webhook secret
    with pytest.raises(ValueError, match="FATAL: RAZORPAY_WEBHOOK_SECRET cannot be placeholder in production."):
        Settings(APP_ENV="production", JWT_SECRET_KEY="valid-jwt", RAZORPAY_KEY_SECRET="valid", RAZORPAY_WEBHOOK_SECRET="placeholder_webhook_secret")

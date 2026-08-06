import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email using Brevo transactional email API.
        """
        if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
            logger.warning("[EMAIL] Brevo API Key or Sender Email not configured. Skipping email send.")
            return False

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "sender": {"email": settings.BREVO_SENDER_EMAIL, "name": "DineOS Admin"},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content
        }

        try:
            async with httpx.AsyncClient(timeout=settings.EMAIL_SEND_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code in (200, 201, 202):
                    logger.info(f"[EMAIL] Email sent successfully to {to_email}")
                    return True
                else:
                    logger.error(f"[EMAIL] Failed to send email: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.exception(f"[EMAIL] Error dispatching email to {to_email}: {e}")
            return False

    @staticmethod
    async def send_sms_otp(phone: str, otp_code: str) -> bool:
        """
        Dispatch SMS OTP to the recipient's phone number.
        Tries 2Factor API first (if TWO_FACTOR_API_KEY is configured),
        then falls back to Twilio (if TWILIO_ACCOUNT_SID is configured).
        """
        # --- 1. Try 2Factor SMS Gateway ---
        if settings.TWO_FACTOR_API_KEY:
            # 2Factor OTP template URL format:
            # https://2factor.in/API/V1/{api_key}/SMS/{phone}/{otp_code}
            url = f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/{phone}/{otp_code}"
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"[SMS] OTP sent via 2Factor to {phone}")
                        return True
                    else:
                        logger.error(f"[SMS] 2Factor failure: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"[SMS] 2Factor exception: {e}")

        # --- 2. Fallback to Twilio ---
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
            auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            data = {
                "To": phone,
                "From": settings.TWILIO_PHONE_NUMBER,
                "Body": f"Your DineOS verification code is: {otp_code}. Valid for 5 minutes."
            }
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(url, data=data, auth=auth)
                    if response.status_code in (200, 201):
                        logger.info(f"[SMS] OTP sent via Twilio to {phone}")
                        return True
                    else:
                        logger.error(f"[SMS] Twilio failure: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"[SMS] Twilio exception: {e}")

        logger.warning(f"[SMS] No SMS provider configured or all failed. Dev OTP was: {otp_code}")
        return False

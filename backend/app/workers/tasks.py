import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(name='notify_low_stock', bind=True, max_retries=3)
def notify_low_stock(self, ingredient_id: str, restaurant_id: str):
    """Alert restaurant owner when an ingredient falls below low-stock threshold."""
    try:
        from sqlalchemy import create_engine, text

        from app.core.config import settings

        # Use the synchronous engine for Celery worker context
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            # Fetch ingredient details
            ing_row = conn.execute(
                text("SELECT name, current_stock, low_stock_threshold FROM ingredients WHERE id = :id"),
                {"id": ingredient_id},
            ).fetchone()

            if not ing_row:
                logger.warning(f"[LOW STOCK] Ingredient {ingredient_id} not found.")
                return

            # Fetch restaurant owner email
            owner_row = conn.execute(
                text("""
                    SELECT u.email, u.full_name
                    FROM users u
                    JOIN user_roles ur ON ur.user_id = u.id
                    JOIN roles r ON r.id = ur.role_id
                    WHERE u.restaurant_id = :rid AND r.name = 'owner'
                    LIMIT 1
                """),
                {"rid": restaurant_id},
            ).fetchone()

        if not owner_row:
            logger.warning(f"[LOW STOCK] No owner found for restaurant {restaurant_id}")
            return

        subject = f"⚠️ Low Stock Alert: {ing_row.name}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
          <h3>Hello {owner_row.full_name},</h3>
          <p>This is an automated low-stock alert from <strong>DineOS</strong>.</p>
          <table style="width:100%; border-collapse:collapse; margin:16px 0;">
            <tr style="background:#f3f4f6;">
              <td style="padding:8px; font-weight:bold;">Ingredient</td>
              <td style="padding:8px;">{ing_row.name}</td>
            </tr>
            <tr>
              <td style="padding:8px; font-weight:bold;">Current Stock</td>
              <td style="padding:8px; color:#dc2626;">{ing_row.current_stock}</td>
            </tr>
            <tr style="background:#f3f4f6;">
              <td style="padding:8px; font-weight:bold;">Low Stock Threshold</td>
              <td style="padding:8px;">{ing_row.low_stock_threshold}</td>
            </tr>
          </table>
          <p>Please restock this ingredient as soon as possible to avoid order disruptions.</p>
          <br/>
          <p>Best Regards,<br/><strong>DineOS System</strong></p>
        </div>
        """

        from app.core.notifications import NotificationService
        _run_async(NotificationService.send_email(owner_row.email, subject, html))
        logger.info(f"[LOW STOCK] Alert sent for '{ing_row.name}' to {owner_row.email}")

    except Exception as exc:
        logger.error(f'notify_low_stock failed: {exc}')
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name='send_daily_digest')
def send_daily_digest():
    """
    Celery beat periodic task: send daily sales digest to all restaurant owners.
    Queries yesterday's orders aggregated by restaurant and emails each owner.
    """
    from datetime import date, timedelta

    from sqlalchemy import create_engine, text

    from app.core.config import settings
    from app.core.notifications import NotificationService

    yesterday = date.today() - timedelta(days=1)
    logger.info(f'[DIGEST] Sending daily digest for {yesterday}...')

    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT
                        r.id AS restaurant_id,
                        r.name AS restaurant_name,
                        u.email AS owner_email,
                        u.full_name AS owner_name,
                        COUNT(o.id) AS total_orders,
                        COALESCE(SUM(o.total_amount), 0) AS total_revenue
                    FROM restaurants r
                    JOIN users u ON u.restaurant_id = r.id
                    JOIN user_roles ur ON ur.user_id = u.id
                    JOIN roles ro ON ro.id = ur.role_id AND ro.name = 'owner'
                    LEFT JOIN orders o ON o.restaurant_id = r.id
                        AND DATE(o.created_at) = :d
                    WHERE r.is_active = TRUE
                    GROUP BY r.id, r.name, u.email, u.full_name
                """),
                {"d": yesterday},
            ).fetchall()

        for row in rows:
            subject = f"📊 DineOS Daily Digest — {yesterday}"
            html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
              <h3>Good morning, {row.owner_name}!</h3>
              <p>Here is your sales summary for <strong>{yesterday}</strong>:</p>
              <table style="width:100%; border-collapse:collapse; margin:16px 0;">
                <tr style="background:#1E3A5F; color:white;">
                  <th style="padding:10px; text-align:left;">Restaurant</th>
                  <th style="padding:10px;">Orders</th>
                  <th style="padding:10px;">Revenue (INR)</th>
                </tr>
                <tr>
                  <td style="padding:10px;">{row.restaurant_name}</td>
                  <td style="padding:10px; text-align:center;">{row.total_orders}</td>
                  <td style="padding:10px; text-align:right;">₹{row.total_revenue:,.2f}</td>
                </tr>
              </table>
              <p style="color:#888;">Log in to your DineOS dashboard for detailed reports.</p>
              <br/>
              <p>Best Regards,<br/><strong>DineOS Platform</strong></p>
            </div>
            """
            _run_async(NotificationService.send_email(row.owner_email, subject, html))
            logger.info(f"[DIGEST] Sent to {row.owner_email} ({row.restaurant_name})")

        logger.info(f'[DIGEST] Done. Processed {len(rows)} restaurant(s).')

    except Exception as exc:
        logger.error(f'send_daily_digest failed: {exc}')


import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import decode_token

router = APIRouter(prefix="/kds", tags=["Kitchen Display System"])

@router.post("/ws-token")
async def get_ws_token(current_user=Depends(get_current_user)):
    """Generate a short-lived (60s) token exclusively for KDS WebSocket auth."""
    expire = datetime.now(UTC) + timedelta(seconds=60)
    to_encode = {
        "sub": str(current_user.id),
        "type": "kds_ws",
        "exp": expire,
        "jti": uuid.uuid4().hex
    }
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"ws_token": token}


@router.websocket("/ws/{restaurant_id}")
async def kds_websocket(
    websocket: WebSocket,
    restaurant_id: str,
    token: str | None = Query(None),
):
    """
    WebSocket endpoint for the Kitchen Display System.
    Requires a valid JWT passed as ?token=... query param (browsers can't send
    Authorization headers during the WebSocket handshake).
    Verifies user belongs to the requested restaurant before accepting.
    """
    # ── 1. Validate JWT ──────────────────────────────────────────────────────
    if not token:
        await websocket.close(code=4401, reason="Missing auth token")
        return

    try:
        payload = decode_token(token)
        if payload.get("type") != "kds_ws":
            await websocket.close(code=4401, reason="Invalid token type, expected KDS WS token")
            return
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4401, reason="Invalid token payload")
            return
    except jwt.PyJWTError:
        await websocket.close(code=4401, reason="Token validation failed")
        return

    # ── 2. Load user and verify restaurant membership ─────────────────────
    try:
        async for db in get_db():
            from sqlalchemy.orm import selectinload

            from app.modules.auth.models import User
            result = await db.execute(
                select(User)
                .options(selectinload(User.roles))
                .where(User.id == user_id, User.is_active)
            )
            user = result.scalar_one_or_none()
            if not user:
                await websocket.close(code=4401, reason="User not found")
                return

            # Super admins can connect to any restaurant; others must own that restaurant
            user_roles = {r.name for r in user.roles} if user.roles else set()
            is_super_admin = "super_admin" in user_roles
            if not is_super_admin and str(user.restaurant_id) != restaurant_id:
                await websocket.close(code=4401, reason="Forbidden: wrong tenant")
                return
    except Exception:
        await websocket.close(code=4401, reason="Auth check failed")
        return

    # ── 3. Accept and stream KDS events ───────────────────────────────────
    await websocket.accept()
    try:
        from app.core.redis import get_redis
        redis = None
        try:
            redis = await get_redis()
        except Exception:
            pass

        if not redis:
            # Redis unavailable: keep WS alive with heartbeats so UI shows "Connected"
            # but real-time order pushes won't work until Redis is running.
            await websocket.send_text(json.dumps({
                'type': 'connected',
                'restaurant_id': restaurant_id,
                'warning': 'Redis unavailable — real-time events disabled. Start Redis for live order updates.',
            }))
            while True:
                try:
                    # Send heartbeat every 30 s to keep connection alive
                    await asyncio.sleep(30)
                    await websocket.send_text(json.dumps({'type': 'heartbeat'}))
                except Exception:
                    break
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(f"kds:{restaurant_id}")

        await websocket.send_text(json.dumps({'type': 'connected', 'restaurant_id': restaurant_id}))

        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True), timeout=30.0
                )
                if message and message.get('type') == 'message':
                    await websocket.send_text(message['data'])
                else:
                    await websocket.send_text(json.dumps({'type': 'heartbeat'}))
            except TimeoutError:
                await websocket.send_text(json.dumps({'type': 'heartbeat'}))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            if redis:
                await pubsub.unsubscribe(f"kds:{restaurant_id}")
        except Exception:
            pass

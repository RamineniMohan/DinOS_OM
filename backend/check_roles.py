import asyncio
from app.db.session import SessionLocal
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check():
    async with SessionLocal() as db:
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.email.in_(['kitchen@spiceroute.demo', 'owner@spiceroute.demo'])))
        users = result.scalars().all()
        for u in users:
            print(f"{u.email} -> roles: {[r.name for r in u.roles]}")

asyncio.run(check())

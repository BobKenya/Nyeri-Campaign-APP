import asyncio
from sqlalchemy import select, func
from app.database import async_session
from app.models.voters import Ward, Constituency

async def check():
    async with async_session() as db:
        total = await db.execute(select(func.count()).select_from(Ward))
        print(f"Total wards in DB: {total.scalar()}")
        
        wards = await db.execute(select(Ward).limit(5))
        for w in wards.scalars():
            print(f"  - {w.ward_name} (constituency_id: {w.constituency_id})")

asyncio.run(check())

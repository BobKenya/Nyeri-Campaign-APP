"""Seed Nyeri County wards"""
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.voters import Constituency, Ward
import uuid

WARDS_DATA = {
    "Kieni": ["Mweiga", "Naromoru/Kiamathaga", "Mwiyogo/Endarasha", "Mountain Lodge", "Gakawa", "Thegu River", "Kabaru"],
    "Mathira": ["Iriaini", "Konyu", "Kirimukuyu", "Magutu", "Mathira West", "Karatina Town"],
    "Mukurweini": ["Gikondi", "Rugi", "Mukurweini Central", "Mukurweini West"],
    "Nyeri Town": ["Kiganjo/Mathari", "Rware", "Gatitu/Muruguru", "Kamakwa/Mukaro", "Ruring'u"],
    "Othaya": ["Mahiga", "Iria-ini", "Chinga", "Karima"],
    "Tetu": ["Dedan Kimathi", "Wamagana", "Aguthi-Gaaki"],
}

async def seed_wards():
    async with async_session() as db:
        result = await db.execute(select(Constituency))
        constituencies = result.scalars().all()
        
        total_added = 0
        for c in constituencies:
            if c.constituency_name in WARDS_DATA:
                # Check existing
                existing = await db.execute(select(Ward).where(Ward.constituency_id == c.constituency_id))
                if existing.scalars().first():
                    print(f"? {c.constituency_name} already has wards, skipping")
                    continue
                
                for ward_name in WARDS_DATA[c.constituency_name]:
                    ward = Ward(
                        ward_id=str(uuid.uuid4()),
                        ward_name=ward_name,
                        constituency_id=c.constituency_id,
                    )
                    db.add(ward)
                    total_added += 1
                    print(f"? Added {ward_name} to {c.constituency_name}")
        
        await db.commit()
        print(f"\n?? Total wards added: {total_added}")

if __name__ == "__main__":
    asyncio.run(seed_wards())

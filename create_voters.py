import asyncio
from app.database import get_db
from app.models.voters import Voter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def create_test_voters():
    async for db in get_db():
        try:
            # Check if voters exist
            result = await db.execute(select(Voter))
            existing = result.scalars().all()
            print(f"Found {len(existing)} existing voters")
            
            if len(existing) == 0:
                # Create test voters
                voters = [
                    Voter(full_name="John Kamau", id_number="12345678", ward_id="Rware", constituency_id="nyeri_town", support_level="strong"),
                    Voter(full_name="Mary Wanjiru", id_number="23456789", ward_id="Wamagana", constituency_id="tetu", support_level="leaning"),
                ]
                for v in voters:
                    db.add(v)
                await db.commit()
                print("✅ Created 2 test voters!")
            else:
                print("Voters already exist")
        except Exception as e:
            print(f"Error: {e}")
        break

asyncio.run(create_test_voters())

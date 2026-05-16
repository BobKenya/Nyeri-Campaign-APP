import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Agent, Opponent, Flag
from datetime import datetime, timedelta

DATABASE_URL = "sqlite:///./nyeri_campaign.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def seed_tracking_data():
    db = SessionLocal()
    
    try:
        # Add 5 test agents
        agents = [
            Agent(
                full_name="John Kamau",
                phone_number="+254720000001",
                ward_id=None,
                ward_name="Mukurwe-ini West",
                trust_score=85,
                is_active=True,
                last_check_in=datetime.now() - timedelta(hours=2)
            ),
            Agent(
                full_name="Mary Wanjiru",
                phone_number="+254720000002",
                ward_id=None,
                ward_name="Mukurwe-ini Central",
                trust_score=92,
                is_active=True,
                last_check_in=datetime.now() - timedelta(minutes=30)
            ),
            Agent(
                full_name="Peter Mwangi",
                phone_number="+254720000003",
                ward_id=None,
                ward_name="Tetu",
                trust_score=78,
                is_active=True,
                last_check_in=datetime.now() - timedelta(hours=5)
            ),
            Agent(
                full_name="Grace Njeri",
                phone_number="+254720000004",
                ward_id=None,
                ward_name="Mathira West",
                trust_score=88,
                is_active=True,
                last_check_in=datetime.now() - timedelta(hours=1)
            ),
            Agent(
                full_name="David Kariuki",
                phone_number="+254720000005",
                ward_id=None,
                ward_name="Kieni West",
                trust_score=45,
                is_active=False,
                last_check_in=datetime.now() - timedelta(days=3)
            ),
        ]
        
        db.add_all(agents)
        db.commit()
        print("✅ Added 5 test agents")
        
        # Add 3 test opponents
        opponents = [
            Opponent(
                full_name="James Opponent",
                party="Opposition Party A",
                constituency_id=None,
                constituency_name="Mukurwe-ini",
                threat_level="high",
                notes="Strong presence in Mukurwe-ini West. Active ground campaign."
            ),
            Opponent(
                full_name="Sarah Rival",
                party="Opposition Party B",
                constituency_id=None,
                constituency_name="Tetu",
                threat_level="medium",
                notes="Moderate support base. Focusing on youth vote."
            ),
            Opponent(
                full_name="Robert Contender",
                party="Independent",
                constituency_id=None,
                constituency_name="Mathira",
                threat_level="low",
                notes="Limited resources. Minimal ground activity."
            ),
        ]
        
        db.add_all(opponents)
        db.commit()
        print("✅ Added 3 test opponents")
        
        # Add 4 test flags
        flags = [
            Flag(
                constituency_id=None,
                ward_id=None,
                description="Reports of voter intimidation in Mukurwe-ini West polling station",
                priority="critical",
                status="open",
                created_at=datetime.now() - timedelta(hours=3)
            ),
            Flag(
                constituency_id=None,
                ward_id=None,
                description="Agent David Kariuki hasn't checked in for 3 days",
                priority="high",
                status="investigating",
                created_at=datetime.now() - timedelta(hours=12)
            ),
            Flag(
                constituency_id=None,
                ward_id=None,
                description="Low turnout reported in Kieni West ward",
                priority="medium",
                status="open",
                created_at=datetime.now() - timedelta(hours=6)
            ),
            Flag(
                constituency_id=None,
                ward_id=None,
                description="Opponent rally planned for Saturday in Tetu",
                priority="low",
                status="resolved",
                created_at=datetime.now() - timedelta(days=2)
            ),
        ]
        
        db.add_all(flags)
        db.commit()
        print("✅ Added 4 test flags")
        
        print("\n🎉 Test data seeded successfully!")
        print("Refresh the tracking screen to see the data.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_tracking_data()

"""Seed Nyeri County data into SQLite: roles, admin user, constituencies, wards."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, async_session, Base
from app.models.auth import Role, User
from app.models.voters import Constituency, Ward
from app.models import operations, messaging_finance, intel_election  # register all tables
from app.utils.security import hash_password


NYERI_CONSTITUENCIES = {
    "Tetu": ["Dedan Kimathi", "Wamagana", "Aguthi-Gaaki"],
    "Kieni": ["Mugunda", "Kabaru", "Gakawa", "Narumoru/Kiamathaga", "Thegu River", "Mweiga", "Mwiyogo/Endarasha", "Gatarakwa"],
    "Mathira": ["Ruguru", "Magutu", "Iriaini", "Konyu", "Kirimukuyu", "Karatina Town"],
    "Othaya": ["Mahiga", "Iria-ini", "Chinga", "Karima"],
    "Mukurweini": ["Gikondi", "Rugi", "Mukurweini West", "Mukurweini Central"],
    "Nyeri Town": ["Kamakwa/Mukaro", "Kiganjo/Mathari", "Rware", "Gatitu/Muruguru", "Ruring'u"],
}


async def seed():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        count = (await db.execute(select(func.count()).select_from(Role))).scalar()
        if count and count > 0:
            print("Database already seeded. Delete nyeri_campaign.db to re-seed.")
            return

        # ── Roles ──────────────────────────────────────────────
        print("Creating roles...")
        roles_data = {
            "super_admin":    "Full system access — manage all users, settings, and data",
            "admin":          "Administrative access — manage most resources",
            "coordinator":    "Constituency/ward coordinator — manages field teams and events",
            "field_agent":    "Canvassing agent — data collection and voter contact",
            "finance_officer":"Manages donations, expenses, and budget allocations",
            "comms_officer":  "Manages messaging campaigns, templates, and media tracking",
            "observer":       "Read-only access for monitoring and reporting",
        }
        role_map = {}
        for name, desc in roles_data.items():
            role = Role(role_name=name, role_description=desc)
            db.add(role)
            role_map[name] = role

        await db.flush()

        # ── Admin User ─────────────────────────────────────────
        print("Creating admin user...")
        admin = User(
            email="admin@nyericampaign.co.ke",
            full_name="System Administrator",
            password_hash=hash_password("ChangeMe2026!"),
            role_id=role_map["super_admin"].role_id,
            phone_number="+254700000000",
        )
        db.add(admin)

        # ── Demo Coordinator ───────────────────────────────────
        coordinator = User(
            email="coordinator@nyericampaign.co.ke",
            full_name="Demo Coordinator",
            password_hash=hash_password("Demo2026!"),
            role_id=role_map["coordinator"].role_id,
            phone_number="+254711111111",
        )
        db.add(coordinator)

        # ── Field Agent ────────────────────────────────────────
        agent = User(
            email="agent@nyericampaign.co.ke",
            full_name="Demo Field Agent",
            password_hash=hash_password("Demo2026!"),
            role_id=role_map["field_agent"].role_id,
            phone_number="+254722222222",
        )
        db.add(agent)

        # ── Constituencies & Wards ─────────────────────────────
        print("Creating constituencies and wards...")
        total_wards = 0
        for const_name, ward_names in NYERI_CONSTITUENCIES.items():
            constituency = Constituency(
                constituency_name=const_name,
                county_name="Nyeri",
            )
            db.add(constituency)
            await db.flush()

            for ward_name in ward_names:
                ward = Ward(
                    ward_name=ward_name,
                    constituency_id=constituency.constituency_id,
                )
                db.add(ward)
                total_wards += 1

        await db.commit()

        print()
        print("=" * 50)
        print("  DATABASE SEEDED SUCCESSFULLY")
        print("=" * 50)
        print(f"  Roles:          {len(roles_data)}")
        print(f"  Users:          3 (admin + coordinator + agent)")
        print(f"  Constituencies: {len(NYERI_CONSTITUENCIES)}")
        print(f"  Wards:          {total_wards}")
        print()
        print("  Login credentials:")
        print("  ┌─────────────────────────────────────────────┐")
        print("  │ Admin:       admin@nyericampaign.co.ke      │")
        print("  │              ChangeMe2026!                   │")
        print("  │ Coordinator: coordinator@nyericampaign.co.ke │")
        print("  │              Demo2026!                       │")
        print("  │ Agent:       agent@nyericampaign.co.ke       │")
        print("  │              Demo2026!                       │")
        print("  └─────────────────────────────────────────────┘")
        print()


if __name__ == "__main__":
    asyncio.run(seed())

"""Nyeri County Gubernatorial Campaign App — SQLite local dev version."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Import ALL models so tables are registered
from app.models import auth, voters, operations, messaging_finance, intel_election, tracking, benefits, meetings as meetings_models, donors as donors_models  # noqa

from app.routers import (
    budgets as budgets_router,
    suppliers as suppliers_router,
    auth as auth_router,
    voters as voters_router,
    field_ops, volunteers, events,
    messaging, finance, compliance, intelligence,
    election_day, analytics, tracking, benefits, meetings, donors,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Auto-create admin user if none exists
    try:
        from app.database import async_session
        from app.models.auth import User, Role
        from app.utils.security import hash_password
        from sqlalchemy import select, func
        import uuid
        async with async_session() as db:
            count = (await db.execute(select(func.count()).select_from(User))).scalar()
            if count == 0:
                # Create admin role
                admin_role = Role(
                    role_id=str(uuid.uuid4()),
                    role_name="admin",
                    role_description="System Administrator",
                    permissions_json={"all": True},
                )
                db.add(admin_role)
                await db.flush()
                # Create admin user
                admin = User(
                    user_id=str(uuid.uuid4()),
                    email="admin@nyericampaign.co.ke",
                    full_name="System Administrator",
                    password_hash=hash_password("ChangeMe2026!"),
                    role_id=admin_role.role_id,
                    is_active=True,
                )
                db.add(admin)
                await db.commit()
                print("Admin user auto-created")
    except Exception as e:
        print(f"Admin seed failed: {e}")
    print(f"  {settings.APP_NAME} running at http://127.0.0.1:8000")
    print(f"  Swagger docs at http://127.0.0.1:8000/docs")
    print(f"  Database: nyeri_campaign.db (SQLite)")
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="Campaign management platform for the Nyeri County gubernatorial race — 44 tables, 11 domains, 78 endpoints",
    version="2.0.0-lite",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router,    prefix="/api/v1/auth",         tags=["Authentication"])
app.include_router(voters_router.router,  prefix="/api/v1/voters",       tags=["Voters"])
app.include_router(field_ops.router,      prefix="/api/v1/field-ops",    tags=["Field Operations"])
app.include_router(volunteers.router,     prefix="/api/v1/volunteers",   tags=["Volunteers"])
app.include_router(events.router,         prefix="/api/v1/events",       tags=["Events"])
app.include_router(messaging.router,      prefix="/api/v1/messaging",    tags=["Messaging"])
app.include_router(finance.router,        prefix="/api/v1/finance",      tags=["Finance"])
app.include_router(budgets_router.router,  prefix="/api/v1/budgets",      tags=["Budgets"])
app.include_router(suppliers_router.router, prefix="/api/v1/suppliers",    tags=["Suppliers"])
app.include_router(compliance.router,     prefix="/api/v1/compliance",   tags=["Compliance"])
app.include_router(intelligence.router,   prefix="/api/v1/intelligence", tags=["Intelligence"])
app.include_router(election_day.router,   prefix="/api/v1/election-day", tags=["Election Day"])
app.include_router(analytics.router,      prefix="/api/v1/analytics",    tags=["Analytics"])
app.include_router(tracking.router,       prefix="/api/v1/tracking",     tags=["Tracking & Intelligence"])
app.include_router(benefits.router,       prefix="/api/v1/benefits",     tags=["Benefits Distribution"])
app.include_router(meetings.router,       prefix="/api/v1/meetings",     tags=["Meetings & Scheduling"])
app.include_router(donors.router,         prefix="/api/v1/donors",       tags=["Donors & Fundraising"])


@app.get("/", tags=["Health"])
async def root():
    return {"app": settings.APP_NAME, "version": "2.0.0-lite", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "database": "SQLite (nyeri_campaign.db)"}


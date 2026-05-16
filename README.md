# Nyeri County Campaign App (Local Edition)

Campaign management platform for the Nyeri County gubernatorial race.
**No Docker required** — runs on SQLite with a single command.

## Quick Start (Windows)

### 1. Install Python (if you don't have it)
Download from https://www.python.org/downloads/  
**Check "Add Python to PATH"** during installation.

### 2. Setup
Open PowerShell, navigate to this folder, and run:

```powershell
cd path\to\nyeri-campaign-app

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Seed the database
python scripts/seed.py
```

### 3. Run
```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Open
- **Swagger UI**: http://localhost:8000/docs  (interactive API testing)
- **Health check**: http://localhost:8000/health

### 5. Login
Use the Swagger UI to test the `/api/v1/auth/login` endpoint:
```json
{
  "email": "admin@nyericampaign.co.ke",
  "password": "ChangeMe2026!"
}
```
Copy the `access_token` from the response, click **Authorize** at the top of Swagger,
paste `Bearer <your_token>`, and you can test all 78 endpoints.

---

## Alternative: Double-click setup (Windows)
Just double-click `setup.bat`, then `run.bat`.

---

## Project Structure

```
app/
├── main.py                    # FastAPI app entry point
├── config.py                  # Settings (SQLite by default)
├── database.py                # Async SQLAlchemy for SQLite
├── dependencies.py            # Auth guards (JWT + RBAC)
├── models/
│   ├── auth.py                # User, Role, Session, Notification
│   ├── voters.py              # Voter, Constituency, Ward, PollingStation
│   ├── operations.py          # Canvassing, Volunteers, Events
│   ├── messaging_finance.py   # Messages, Donations, Expenses, Compliance
│   └── intel_election.py      # Opponents, Candidates, Results, Analytics
├── schemas/                   # Pydantic request/response models
├── routers/                   # API endpoints (11 route files)
└── utils/
    └── security.py            # JWT, bcrypt, TOTP 2FA

scripts/
└── seed.py                    # Seeds Nyeri constituencies, wards, demo users

nyeri_campaign.db              # SQLite database (created on first run)
```

## API Domains (78 endpoints)

| Domain | Prefix | Key Endpoints |
|--------|--------|---------------|
| Auth | `/api/v1/auth` | Login, register, refresh, 2FA, notifications |
| Voters | `/api/v1/voters` | CRUD, search, stats, interaction history |
| Field Ops | `/api/v1/field-ops` | Canvassing routes, contact logging |
| Volunteers | `/api/v1/volunteers` | CRUD, shifts, assignments |
| Events | `/api/v1/events` | CRUD, attendees, check-in, stats |
| Messaging | `/api/v1/messaging` | Campaigns, templates, groups, delivery |
| Finance | `/api/v1/finance` | Donations, expenses, budgets, summaries |
| Compliance | `/api/v1/compliance` | IEBC reports, permits, audit logs |
| Intelligence | `/api/v1/intelligence` | Opponents, dossiers, media, endorsements |
| Election Day | `/api/v1/election-day` | Candidates, agents, incidents, tallying |
| Analytics | `/api/v1/analytics` | Snapshots, live dashboard |

## Upgrading to PostgreSQL

When ready for production, change one line in `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/nyeri_campaign
```
And add `asyncpg` to requirements. The ORM models work identically.

## Nyeri County Structure
- 6 Constituencies: Tetu, Kieni, Mathira, Othaya, Mukurweini, Nyeri Town
- 28 Wards
- ~400 Polling Stations
- 250K–400K Registered Voters

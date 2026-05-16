import asyncio
from app.database import get_db
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def reset_password():
    async for db in get_db():
        user = db.query(User).filter(User.email == 'admin@nyericampaign.co.ke').first()
        if user:
            # Set password to ChangeMe2026!
            user.password_hash = pwd_context.hash('ChangeMe2026!')
            db.commit()
            print(f'✅ Password reset for {user.email}')
        else:
            print('❌ User not found')
        break

asyncio.run(reset_password())

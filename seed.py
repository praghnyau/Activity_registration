"""
seed.py — creates test accounts for development.
Run: python seed.py

Admin:   dantubhavyasree@gmail.com / admin123
Student: 25wh1a0001@bvrithyderabad.edu.in / student123
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import hash_password, student_id_from_email

SEED_USERS = [
    {"name": "Bhavyasree Dantu",  "email": "dantubhavyasree@gmail.com",           "password": "admin123",   "role": UserRole.administrator},
    {"name": "Alice Johnson",     "email": "25wh1a0001@bvrithyderabad.edu.in",     "password": "student123", "role": UserRole.student},
    {"name": "Bob Smith",         "email": "25wh1a0002@bvrithyderabad.edu.in",     "password": "student123", "role": UserRole.student},
    {"name": "Carol Davis",       "email": "25wh1a0003@bvrithyderabad.edu.in",     "password": "student123", "role": UserRole.student},
]


async def seed():
    async with AsyncSessionLocal() as db:
        created = skipped = 0
        for data in SEED_USERS:
            result = await db.execute(select(User).where(User.email == data["email"]))
            if result.scalar_one_or_none():
                print(f"  SKIP  {data['email']}")
                skipped += 1
                continue
            user = User(
                name=data["name"],
                email=data["email"],
                password_hash=hash_password(data["password"]),
                role=data["role"],
                student_id=student_id_from_email(data["email"]) if data["role"] == UserRole.student else None,
            )
            db.add(user)
            print(f"  CREATE {data['email']} ({data['role'].value})")
            created += 1
        await db.commit()
        print(f"\nDone — {created} created, {skipped} skipped.")
        print("  Admin:   dantubhavyasree@gmail.com              / admin123")
        print("  Student: 25wh1a0001@bvrithyderabad.edu.in       / student123")


if __name__ == "__main__":
    asyncio.run(seed())

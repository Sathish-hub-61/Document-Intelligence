"""
Database seeding script.
Creates seeded user accounts for all roles (admin, student, faculty, staff).
"""
import sys
from pathlib import Path

# Ensure backend root on path
backend_path = Path(__file__).resolve().parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.adapters.persistence.database import SessionLocal, Base, engine
from app.adapters.persistence.repositories import SqlAlchemyUserRepo
from app.adapters.security.password import hash_password
from app.domain.entities import Role, User

SEED_USERS = [
    {
        "name": "System Administrator",
        "email": "admin@university.edu",
        "password": "AdminPass123!",
        "role": Role.ADMIN,
    },
    {
        "name": "Alice Student",
        "email": "student@university.edu",
        "password": "StudentPass123!",
        "role": Role.STUDENT,
    },
    {
        "name": "Prof. Robert Faculty",
        "email": "faculty@university.edu",
        "password": "FacultyPass123!",
        "role": Role.FACULTY,
    },
    {
        "name": "Sarah Staff",
        "email": "staff@university.edu",
        "password": "StaffPass123!",
        "role": Role.STAFF,
    },
]


def seed_database() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        repo = SqlAlchemyUserRepo(db)
        for user_data in SEED_USERS:
            existing = repo.get_user_by_email(user_data["email"])
            if not existing:
                hashed = hash_password(user_data["password"])
                user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password_hash=hashed,
                    role=user_data["role"],
                )
                repo.create_user(user)
                print(f"✓ Seeded user: {user.email} ({user.role.value})")
            else:
                print(f"- User already exists: {user_data['email']}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database accounts...")
    seed_database()
    print("Seeding complete.")


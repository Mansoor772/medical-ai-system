"""
Run this ONCE after the first `docker compose up` to create your Creator Admin account.

Usage (from the project root):
    docker compose exec fastapi python scripts/create_creator_admin.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from core.database import _global_engine, init_global_db
from core.security import hash_password
from models.global_models import CreatorAdmin

def main():
    print("=== Creator Admin Setup ===")
    name = input("Your name: ").strip()
    email = input("Email: ").strip().lower()
    password = input("Password (min 8 chars): ").strip()

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    init_global_db()

    from sqlalchemy.orm import sessionmaker
    Session_ = sessionmaker(bind=_global_engine)
    db: Session = Session_()

    try:
        existing = db.query(CreatorAdmin).filter(CreatorAdmin.email == email).first()
        if existing:
            print(f"Creator admin with email '{email}' already exists.")
            sys.exit(0)

        admin = CreatorAdmin(
            name=name,
            email=email,
            password_hash=hash_password(password),
        )
        db.add(admin)
        db.commit()
        print(f"\nCreator admin '{name}' created successfully.")
        print("You can now log in at POST /auth/login")
    finally:
        db.close()


if __name__ == "__main__":
    main()

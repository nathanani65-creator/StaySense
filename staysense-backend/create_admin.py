"""
Creates (or promotes an existing user to) an admin account — there is no
seed data for this because /api/auth/register always sets role='user' by
design (no privilege escalation via public signup).

Usage:
    python create_admin.py <email> <password> [name]

If the email already exists, its password is left alone and it is just
promoted to role='admin'. Otherwise a new admin user is created.
"""
import sys

from app.database import SessionLocal
from app import models
from app.auth import hash_password


def run(email: str, password: str, name: str = "Admin") -> None:
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        if user:
            user.role = "admin"
            db.commit()
            print(f"Promoted existing user '{email}' (id={user.id}) to admin.")
        else:
            user = models.User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created admin user '{email}' (id={user.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Admin")

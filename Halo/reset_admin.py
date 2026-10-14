"""Reset the local administrator login to the project's documented defaults.

Run from this folder with: python reset_admin.py
The temporary password is intentionally changed on first successful login.
"""
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import get_db

ADMIN_USERNAME = "admin"
ADMIN_TEMP_PASSWORD = "ChangeMe_123"


def main():
    app = create_app()
    with app.app_context():
        db = get_db()
        try:
            conflict = db.execute(
                "SELECT id, role FROM users WHERE username=?", (ADMIN_USERNAME,)
            ).fetchone()
            if conflict and conflict["role"] != "admin":
                raise RuntimeError(
                    "The username 'admin' is already assigned to a non-admin account. "
                    "Rename that account before resetting the administrator."
                )

            admin = db.execute(
                "SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1"
            ).fetchone()
            password_hash = generate_password_hash(ADMIN_TEMP_PASSWORD)
            if admin:
                db.execute(
                    "UPDATE users SET username=?, password_hash=?, must_change_password=1, active=1 "
                    "WHERE id=?",
                    (ADMIN_USERNAME, password_hash, admin["id"]),
                )
            else:
                db.execute(
                    "INSERT INTO users(username,password_hash,role,full_name,must_change_password,active) "
                    "VALUES(?,?,'admin','System Administrator',1,1)",
                    (ADMIN_USERNAME, password_hash),
                )
            db.commit()
        finally:
            db.close()

    print("Admin login reset successfully.")
    print("Username: admin")
    print("Temporary password: ChangeMe_123")
    print("You will be asked to change the password after logging in.")


if __name__ == "__main__":
    main()

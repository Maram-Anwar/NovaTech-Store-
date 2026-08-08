import getpass
import hashlib
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ADMINS_FILE = BASE_DIR / "admins.json"


def main():
    print("\nNova Tech Store - Admin Setup")
    print("-" * 34)
    user_name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password (8+ characters): ")
    confirm = getpass.getpass("Confirm password: ")

    if len(user_name) < 3:
        raise SystemExit("Admin name must be at least 3 characters.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise SystemExit("Enter a valid email address.")
    if len(password) < 8:
        raise SystemExit("Admin password must be at least 8 characters.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    try:
        admins = json.loads(ADMINS_FILE.read_text(encoding="utf-8"))
        if not isinstance(admins, list):
            admins = []
    except (FileNotFoundError, json.JSONDecodeError):
        admins = []

    if any(str(a.get("email", "")).lower() == email for a in admins):
        raise SystemExit("An admin with this email already exists.")

    admins.append({
        "user_name": user_name,
        "email": email,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
    })
    ADMINS_FILE.write_text(json.dumps(admins, indent=4), encoding="utf-8")
    print("\nAdmin account created successfully.")


if __name__ == "__main__":
    main()

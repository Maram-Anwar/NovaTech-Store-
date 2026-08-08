import hashlib
import json
import re


class AdminManager:
    def __init__(self, file_name="admins.json"):
        self.file_name = file_name
        self.database = self.load_admins()

    def load_admins(self):
        try:
            with open(self.file_name, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def _password_matches(admin, password):
        password_hash = hashlib.sha256(str(password or "").encode()).hexdigest()
        stored_hash = str(admin.get("password_hash", "")).strip().lower()
        if stored_hash:
            return stored_hash == password_hash

        # Backward compatibility with older project data. Some versions stored
        # either plain text OR an SHA-256 value under the `password` key.
        legacy = str(admin.get("password", ""))
        if re.fullmatch(r"[0-9a-fA-F]{64}", legacy):
            return legacy.lower() == password_hash
        return legacy == str(password or "")

    def login(self, email, password):
        email = str(email or "").strip().lower()
        password = str(password or "")

        if not email:
            return {"status": "error", "message": "Email Is Required"}
        if not password:
            return {"status": "error", "message": "Password Is Required"}

        for admin in self.database:
            if str(admin.get("email", "")).strip().lower() == email:
                if self._password_matches(admin, password):
                    return {
                        "status": "success",
                        "message": "Welcome Admin",
                        "admin": {
                            "user_name": admin.get("user_name", "admin"),
                            "email": admin.get("email", email),
                        },
                    }
                return {"status": "error", "message": "Wrong Password"}

        return {"status": "error", "message": "Admin Email Not Found"}

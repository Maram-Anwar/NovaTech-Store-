import hashlib
import json
import random
import smtplib
import time
from email.message import EmailMessage

from config import my_email, my_password


class UserManager:
    OTP_TTL_SECONDS = 10 * 60
    MAX_OTP_ATTEMPTS = 5

    def __init__(self, file_name="users.json"):
        self.file_name = file_name
        self.database = self.load_users()
        self.pending_users = {}

    def load_users(self):
        try:
            with open(self.file_name, "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def login(self, email, password):
        email = str(email or "").strip().lower()
        password = str(password or "")

        if not email:
            return {"status": "error", "message": "Email Is Required"}
        if not password:
            return {"status": "error", "message": "Password Is Required"}

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        for user in self.database:
            if user.get("email", "").lower() == email:
                if user.get("password") == hashed_password:
                    return {
                        "status": "success",
                        "message": "Welcome Back",
                        "user": {
                            "user_name": user["user_name"],
                            "email": user["email"],
                            "balance": user.get("balance", 0),
                        },
                    }
                return {"status": "error", "message": "Wrong Password"}
        return {"status": "error", "message": "Email Not Found"}

    def _validate_registration(self, user_name, password, email):
        user_name = str(user_name or "").strip()
        email = str(email or "").strip().lower()
        password = str(password or "")

        if not email:
            return None, {"status": "error", "message": "Email Is Required"}
        if "@" not in email or "." not in email.split("@")[-1]:
            return None, {"status": "error", "message": "Invalid Email Address"}
        if len(user_name) < 3:
            return None, {"status": "error", "message": "User Name Must Be At Least 3 Characters"}
        if len(password) < 6 or len(password) > 12:
            return None, {"status": "error", "message": "Password Must Be Between 6 And 12 Characters"}

        for user in self.database:
            if user_name.lower() == user.get("user_name", "").lower():
                return None, {"status": "error", "message": "User Name Already Exists"}
            if user.get("email", "").lower() == email:
                return None, {"status": "error", "message": "Email Already Exists"}

        return (user_name, password, email), None

    def register(self, user_name, password, email):
        values, error = self._validate_registration(user_name, password, email)
        if error:
            return error

        user_name, password, email = values
        otp = self.generate_otp()
        send_result = self.send_otp(email, otp)
        if send_result["status"] != "success":
            return send_result

        self.pending_users[email] = {
            "user_name": user_name,
            "email": email,
            "password": password,
            "otp": otp,
            "expires_at": time.time() + self.OTP_TTL_SECONDS,
            "attempts": 0,
        }
        return {
            "status": "pending",
            "message": send_result.get("message", "OTP Sent Successfully"),
            "delivery": send_result.get("delivery", "email"),
        }

    def resend_otp(self, email):
        email = str(email or "").strip().lower()
        pending_user = self.pending_users.get(email)
        if pending_user is None:
            return {"status": "error", "message": "No Pending Registration Found"}

        otp = self.generate_otp()
        send_result = self.send_otp(email, otp)
        if send_result["status"] != "success":
            return send_result

        pending_user["otp"] = otp
        pending_user["expires_at"] = time.time() + self.OTP_TTL_SECONDS
        pending_user["attempts"] = 0
        return {
            "status": "pending",
            "message": send_result.get("message", "OTP Sent Successfully"),
            "delivery": send_result.get("delivery", "email"),
        }

    def verify_otp(self, email, user_otp):
        email = str(email or "").strip().lower()
        user_otp = str(user_otp or "").strip()
        pending_user = self.pending_users.get(email)

        if pending_user is None:
            return {"status": "error", "message": "No Pending Registration Found"}

        if time.time() > pending_user.get("expires_at", 0):
            self.pending_users.pop(email, None)
            return {"status": "error", "message": "OTP Expired. Register Again"}

        pending_user["attempts"] = int(pending_user.get("attempts", 0)) + 1
        if pending_user["attempts"] > self.MAX_OTP_ATTEMPTS:
            self.pending_users.pop(email, None)
            return {"status": "error", "message": "Too Many OTP Attempts. Register Again"}

        if pending_user["otp"] != user_otp:
            return {"status": "error", "message": "Wrong OTP"}

        result = self.add_user(
            pending_user["user_name"],
            pending_user["email"],
            pending_user["password"],
        )
        if result["status"] == "success":
            self.pending_users.pop(email, None)
        return result

    def generate_otp(self):
        return str(random.SystemRandom().randint(100000, 999999))

    def send_otp(self, email, otp):
        email_sender = str(my_email or "").strip()
        email_password = str(my_password or "").strip().replace(" ", "")
        placeholders = {"youraccount@gmail.com", "your-email@gmail.com", "your-16-character-app-password", "app-password"}
        if (not email_sender or not email_password or
                email_sender.lower() in placeholders or email_password.lower() in placeholders):
            # Local fallback for the course/project build: the account is still
            # created through the real backend and saved to users.json, but the
            # verification code is printed only in the Python server window.
            # Configure Gmail environment variables to send the code by email.
            print("\n" + "=" * 58)
            print(" NOVA TECH STORE - LOCAL VERIFICATION CODE")
            print(f" Email: {email}")
            print(f" OTP:   {otp}")
            print(" Gmail is not configured, so use this code in the website.")
            print("=" * 58 + "\n")
            return {
                "status": "success",
                "message": "Verification code generated. Check the Nova server window.",
                "delivery": "server_console",
            }

        try:
            message = EmailMessage()
            message["Subject"] = "Nova Tech Store verification code"
            message["From"] = email_sender
            message["To"] = email
            message.set_content(
                "Welcome to Nova Tech Store.\n\n"
                f"Your verification code is: {otp}\n"
                "This code expires in 10 minutes.\n\n"
                "If you did not create this account, you can ignore this email."
            )

            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as connection:
                connection.ehlo()
                connection.starttls()
                connection.ehlo()
                connection.login(email_sender, email_password)
                connection.send_message(message)

            return {"status": "success", "message": "OTP Sent Successfully", "delivery": "email"}
        except smtplib.SMTPAuthenticationError:
            return {"status": "error", "message": "Email Authentication Failed"}
        except smtplib.SMTPConnectError:
            return {"status": "error", "message": "Unable To Connect To Email Server"}
        except smtplib.SMTPRecipientsRefused:
            return {"status": "error", "message": "Invalid Email Address"}
        except smtplib.SMTPException:
            return {"status": "error", "message": "Failed To Send OTP"}
        except Exception:
            return {"status": "error", "message": "Unexpected Email Error"}

    def add_user(self, user_name, email, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        new_user = {
            "user_name": user_name.strip(),
            "email": email.strip().lower(),
            "password": hashed_password,
            "balance": 0,
        }
        self.database.append(new_user)
        self._save_users()
        return {
            "status": "success",
            "message": "Account Created Successfully",
            "user": {
                "user_name": new_user["user_name"],
                "email": new_user["email"],
                "balance": new_user["balance"],
            },
        }

    def get_all_users(self):
        return {
            "status": "success",
            "message": "Users Retrieved Successfully",
            "users": [
                {
                    "user_name": user["user_name"],
                    "email": user["email"],
                    "balance": user.get("balance", 0),
                }
                for user in self.database
            ],
        }

    def delete_user(self, user_name):
        user_name = str(user_name or "").strip().lower()
        for user in self.database:
            if user["user_name"].lower() == user_name:
                self.database.remove(user)
                self._save_users()
                return {"status": "success", "message": "User Deleted Successfully"}
        return {"status": "error", "message": "User Not Found"}

    def _save_users(self):
        with open(self.file_name, "w", encoding="utf-8") as file:
            json.dump(self.database, file, indent=4)

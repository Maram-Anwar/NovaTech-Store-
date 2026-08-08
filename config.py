import os

# Nova Tech Store uses real SMTP for registration verification.
# For Gmail, use a Gmail App Password (not the normal account password).
my_email = os.getenv("NOVA_STORE_EMAIL", os.getenv("STORE_EMAIL", "")).strip()
my_password = os.getenv(
    "NOVA_STORE_EMAIL_PASSWORD",
    os.getenv("STORE_EMAIL_PASSWORD", ""),
).strip()

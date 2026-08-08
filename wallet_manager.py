class WalletManager:
    def __init__(self, user_manager):
        self.user_manager = user_manager

    def get_user(self, user_name):
        """
        Return user dictionary if found, otherwise None
        """
        user_name = user_name.strip().lower()

        for user in self.user_manager.database:
            if user["user_name"].lower() == user_name:
                return user

        return None

    def get_balance(self, user_name):
        """
        Return current user balance
        """
        user = self.get_user(user_name)

        if user is None:
            return {
                "status": "error",
                "message": "User Not Found"
            }

        return {
            "status": "success",
            "balance": user.get("balance", 0)
        }

    def add_balance(self, user_name, amount):
        """
        Charge user wallet (Admin)
        """
        try:
            amount = float(amount)
            if amount <= 0:
                return {
                    "status": "error",
                    "message": "Amount Must Be Greater Than Zero"
                }
        except (ValueError, TypeError):
            return {
                "status": "error",
                "message": "Invalid Amount"
            }

        user = self.get_user(user_name)

        if user is None:
            return {
                "status": "error",
                "message": "User Not Found"
            }

        user["balance"] = user.get("balance", 0) + amount
        self.user_manager._save_users()

        return {
            "status": "success",
            "message": "Balance Added Successfully",
            "balance": user["balance"]
        }

    def deduct_balance(self, user_name, amount):
        """
        Deduct money when checkout
        """
        try:
            amount = float(amount)
            if amount <= 0:
                return {
                    "status": "error",
                    "message": "Amount Must Be Greater Than Zero"
                }
        except (ValueError, TypeError):
            return {
                "status": "error",
                "message": "Invalid Amount"
            }

        user = self.get_user(user_name)

        if user is None:
            return {
                "status": "error",
                "message": "User Not Found"
            }

        current_balance = user.get("balance", 0)

        if current_balance < amount:
            return {
                "status": "error",
                "message": "Insufficient Balance",
                "balance": current_balance
            }

        user["balance"] = current_balance - amount
        self.user_manager._save_users()

        return {
            "status": "success",
            "message": "Payment Completed",
            "balance": user["balance"]
        }

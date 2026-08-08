import hashlib

class ProfileManager():
    def __init__(self, user_manager):
        self.user_manager = user_manager

    def get_profile(self, user_name):
        user_name = user_name.strip().lower()
        for user in self.user_manager.database:
            if user["user_name"].lower() == user_name:
                return {
                    "status": "success",
                    "Account Name": user["user_name"],
                    "Email": user["email"],
                    "Balance": user.get("balance", 0)
                }
        return {"status": "error", "message": "User Not Found"}
    
    def update_username(self, current_name, new_name):
        current_name = current_name.strip().lower()
        clean_new_name = new_name.strip()

        if not clean_new_name:
            return {"status": "error", "message": "New username cannot be empty"}

        for user in self.user_manager.database:
            if user["user_name"].lower() == clean_new_name.lower():
                return {"status": "error", "message": "Username Already Exists"} 
        
        for user in self.user_manager.database:
            if user["user_name"].lower() == current_name:
                user["user_name"] = clean_new_name
                self.user_manager._save_users()
                return {"status": "success", "message": "Username Updated Successfully"}
                
        return {"status": "error", "message": "User Not Found"}
    
    def change_password(self, user_name, old_password, new_password):
        user_name = user_name.strip().lower()
        
        if len(new_password) <= 6:
            return {"status": "error", "message": "New password must be greater than 6 characters"}
            
        hashed_old_password = hashlib.sha256(old_password.encode()).hexdigest()

        for user in self.user_manager.database:
            if user["user_name"].lower() == user_name:
                if user["password"] != hashed_old_password:
                    return {"status": "error", "message": "Incorrect Old Password"}

                user["password"] = hashlib.sha256(new_password.encode()).hexdigest()
                self.user_manager._save_users()
                return {"status": "success", "message": "Password Changed Successfully"}
                
        return {"status": "error", "message": "User Not Found"}

    def delete_my_account(self, user_name, password):
        user_name = user_name.strip().lower()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        for user in self.user_manager.database:
            if user["user_name"].lower() == user_name:
                if user["password"] != hashed_password:
                    return {"status": "error", "message": "Incorrect Password"}

                delete_result = self.user_manager.delete_user(user_name)
                return {"status": "success", "message": delete_result} 
                
        return {"status": "error", "message": "User Not Found"}
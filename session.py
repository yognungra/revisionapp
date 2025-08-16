from datetime import datetime

class Session:
    def __init__(self, user_id):
        self.user_id = user_id
        self.start_time = datetime.now()
        self.role = None

    def login(self, user_id, role):
        self.user_id = user_id
        self.role = role
        self.start_time = datetime.now()
        print(f"User ID {self.user_id} logged in as {self.role}.")

    
    def logout(self):
        self.user_id = None
        self.role = None
        print("User logged out.")


    def is_logged_in(self):
        return self.user_id is not None

    def require_role(self, required_role):
        if not self.is_logged_in():
            print("You must be logged in to perform this action.")
            return False
        
        if self.role.lower() != required_role.lower():
            print(f"Entry denied! Only {required_role}s can perform this action.")
            return False
        return True
    
    def get_user_id(self):
        return self.user_id


session = Session(None)
import re
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta

# Database connection
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Alejandro's_Labor_Camp"
SECRET_KEY = "your_secret_key_change_this_in_production"  # Change this!

class UserManager:
    def __init__(self):
        try:
            self.client = MongoClient(URI, server_api=ServerApi('1'))
            self.db = self.client[DB_NAME]
            self.users_collection = self.db['users']
            
            # Create indexes for better query performance
            self.users_collection.create_index('email', unique=True)
            print("✅ UserManager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize UserManager: {e}")
            raise

    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_password(self, password):
        """Validate password (minimum 6 characters)"""
        return len(password) >= 6

    def register_user(self, email, password):
        """
        Register a new user
        Returns: (success: bool, message: str, user_id: str or None)
        """
        try:
            # Validate inputs
            email = email.strip().lower()
            
            if not self.validate_email(email):
                return False, "Invalid email format", None
            
            if not self.validate_password(password):
                return False, "Password must be at least 6 characters", None
            
            # Check if user already exists
            existing_user = self.users_collection.find_one({'email': email})
            if existing_user:
                return False, "User already exists", None
            
            # Hash password
            hashed_password = generate_password_hash(password)
            
            # Create user document
            user_doc = {
                'email': email,
                'password': hashed_password,
                'created_at': datetime.utcnow(),
                'is_active': True,
                'role': 'user'  # Can be 'user', 'admin', etc.
            }
            
            # Insert user
            result = self.users_collection.insert_one(user_doc)
            
            return True, "User registered successfully", str(result.inserted_id)
        
        except Exception as e:
            return False, f"Registration error: {str(e)}", None

    def login_user(self, email, password):
        """
        Authenticate user and generate token
        Returns: (success: bool, message: str, token: str or None, user_data: dict or None)
        """
        try:
            email = email.strip().lower()
            
            # Find user
            user = self.users_collection.find_one({'email': email})
            if not user:
                return False, "Invalid email or password", None, None
            
            # Check password
            if not check_password_hash(user['password'], password):
                return False, "Invalid email or password", None, None
            
            # Generate JWT token (expires in 7 days)
            token_payload = {
                'user_id': str(user['_id']),
                'email': user['email'],
                'role': user.get('role', 'user'),
                'exp': datetime.utcnow() + timedelta(days=7),
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(token_payload, SECRET_KEY, algorithm='HS256')
            
            # User data to return (exclude password)
            user_data = {
                'user_id': str(user['_id']),
                'email': user['email'],
                'role': user.get('role', 'user')
            }
            
            return True, "Login successful", token, user_data
        
        except Exception as e:
            return False, f"Login error: {str(e)}", None, None

    def verify_token(self, token):
        """
        Verify JWT token
        Returns: (success: bool, payload: dict or None, message: str)
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return True, payload, "Token valid"
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError:
            return False, None, "Invalid token"
        except Exception as e:
            return False, None, f"Token error: {str(e)}"

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            from bson import ObjectId
            user = self.users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                user['_id'] = str(user['_id'])
                user.pop('password', None)  # Remove password
                return user
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def update_user_profile(self, user_id, update_data):
        """Update user profile (name, phone, etc.)"""
        try:
            from bson import ObjectId
            
            # Don't allow updating sensitive fields
            update_data.pop('password', None)
            update_data.pop('email', None)
            update_data.pop('_id', None)
            
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def change_password(self, user_id, old_password, new_password):
        """Change user password"""
        try:
            from bson import ObjectId
            
            if not self.validate_password(new_password):
                return False, "Password must be at least 6 characters"
            
            user = self.users_collection.find_one({'_id': ObjectId(user_id)})
            if not user:
                return False, "User not found"
            
            # Verify old password
            if not check_password_hash(user['password'], old_password):
                return False, "Current password is incorrect"
            
            # Hash new password
            hashed_password = generate_password_hash(new_password)
            
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'password': hashed_password}}
            )
            
            return True, "Password changed successfully" if result.modified_count > 0 else "Password not changed"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def logout_user(self, token):
        """
        Logout user (optional - can add token blacklist later)
        For now, client-side logout by removing localStorage token is sufficient
        """
        return True

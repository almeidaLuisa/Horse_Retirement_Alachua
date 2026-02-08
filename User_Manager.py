import re
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from bson import ObjectId

# Database connection using API Key authentication
MONGODB_API_KEY = "8ab265da-7d60-41e3-a416-ce58a4b1eb93"
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"
SECRET_KEY = "your_secret_key_change_this_in_production"  # Change this!

class UserManager:
    def __init__(self):
        try:
            self.client = MongoClient(URI, server_api=ServerApi('1'))
            self.db = self.client[DB_NAME]
            self.users_collection = self.db['User_Logins']
            self.logins_collection = self.db['User_Tables']
            self.audit_collection = self.db['Audit_Logs']
            self.horses_collection = self.db['Horse_Tables']
            
            # Create indexes for better query performance
            try:
                self.users_collection.create_index('email', unique=True)
            except:
                pass  # Index may already exist
            self.users_collection.create_index('created_at')
            try:
                self.logins_collection.create_index('user_id')
                self.logins_collection.create_index('timestamp')
            except:
                pass  # Indexes may already exist
            try:
                self.audit_collection.create_index('user_id')
                self.audit_collection.create_index('timestamp')
                self.audit_collection.create_index('action')
            except:
                pass  # Indexes may already exist
            self.horses_collection.create_index('name')
            self.horses_collection.create_index('manager_id')
            
            print("✅ UserManager initialized successfully")
            print(f"✅ Connected to database: {DB_NAME}")
            print(f"✅ Collections available: User_Tables, User_Logins, Horse_Tables")
        except Exception as e:
            print(f"❌ Failed to initialize UserManager: {e}")
            raise

    def _log_audit(self, user_id, action, details=None):
        """Log user actions for audit trail"""
        try:
            audit_doc = {
                'user_id': str(user_id) if user_id else None,
                'action': action,
                'details': details,
                'timestamp': datetime.utcnow(),
                'ip_address': None  # Can be added later with request context
            }
            self.audit_collection.insert_one(audit_doc)
        except Exception as e:
            print(f"⚠️ Audit log error: {e}")

    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_password(self, password):
        """Validate password (minimum 6 characters)"""
        return len(password) >= 6

    def register_user(self, email, password, first_name=None, last_name=None):
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
                self._log_audit(None, 'register_failed', {'email': email, 'reason': 'duplicate'})
                return False, "User already exists", None
            
            # Hash password
            hashed_password = generate_password_hash(password)
            
            # Create user document
            user_doc = {
                'email': email,
                'password': hashed_password,
                'first_name': first_name.strip() if first_name else None,
                'last_name': last_name.strip() if last_name else None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'role': 'user',  # Can be 'user', 'admin', 'manager'
                'managed_horses': [],  # Array of horse IDs this user manages
                'permissions': ['view_horses', 'view_profile'],  # User permissions
                'last_login': None
            }
            
            # Insert user
            result = self.users_collection.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            # Log registration
            self._log_audit(user_id, 'user_registered', {'email': email})
            
            return True, "User registered successfully", user_id
        
        except DuplicateKeyError:
            self._log_audit(None, 'register_failed', {'email': email, 'reason': 'duplicate'})
            return False, "User already exists", None
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
                # Log failed login attempt to both User_Logins and Audit_Logs
                login_record = {
                    'email': email,
                    'timestamp': datetime.utcnow(),
                    'success': False,
                    'reason': 'user_not_found'
                }
                self.logins_collection.insert_one(login_record)
                self._log_audit(None, 'login_failed', {'email': email, 'reason': 'user_not_found'})
                return False, "Invalid email or password", None, None
            
            # Check password
            if not check_password_hash(user['password'], password):
                # Log failed login attempt to both User_Logins and Audit_Logs
                login_record = {
                    'user_id': str(user['_id']),
                    'email': email,
                    'timestamp': datetime.utcnow(),
                    'success': False,
                    'reason': 'wrong_password'
                }
                self.logins_collection.insert_one(login_record)
                self._log_audit(str(user['_id']), 'login_failed', {'email': email, 'reason': 'wrong_password'})
                return False, "Invalid email or password", None, None
            
            # Update last login
            self.users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
            
            # Generate JWT token (expires in 7 days)
            token_payload = {
                'user_id': str(user['_id']),
                'email': user['email'],
                'role': user.get('role', 'user'),
                'permissions': user.get('permissions', []),
                'exp': datetime.utcnow() + timedelta(days=7),
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(token_payload, SECRET_KEY, algorithm='HS256')
            
            # User data to return (exclude password)
            user_data = {
                'user_id': str(user['_id']),
                'email': user['email'],
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name'),
                'role': user.get('role', 'user'),
                'managed_horses': user.get('managed_horses', [])
            }
            
            # Log successful login to User_Logins collection
            login_record = {
                'user_id': str(user['_id']),
                'email': email,
                'timestamp': datetime.utcnow(),
                'success': True
            }
            self.logins_collection.insert_one(login_record)
            
            # Also log all activity (including successful logins) to audit trail
            self._log_audit(str(user['_id']), 'user_login', {'email': email, 'success': True})
            
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
            # Don't allow updating sensitive fields
            update_data.pop('password', None)
            update_data.pop('email', None)
            update_data.pop('_id', None)
            update_data.pop('role', None)
            update_data.pop('created_at', None)
            
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self._log_audit(user_id, 'profile_updated', update_data)
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def change_password(self, user_id, old_password, new_password):
        """Change user password"""
        try:
            if not self.validate_password(new_password):
                return False, "Password must be at least 6 characters"
            
            user = self.users_collection.find_one({'_id': ObjectId(user_id)})
            if not user:
                return False, "User not found"
            
            # Verify old password
            if not check_password_hash(user['password'], old_password):
                self._log_audit(user_id, 'password_change_failed', {'reason': 'wrong_current_password'})
                return False, "Current password is incorrect"
            
            # Hash new password
            hashed_password = generate_password_hash(new_password)
            
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'password': hashed_password, 'updated_at': datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                self._log_audit(user_id, 'password_changed', {})
            
            return True, "Password changed successfully" if result.modified_count > 0 else "Password not changed"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def logout_user(self, token):
        """
        Logout user (optional - can add token blacklist later)
        For now, client-side logout by removing localStorage token is sufficient
        """
        try:
            success, payload, message = self.verify_token(token)
            if success:
                self._log_audit(payload['user_id'], 'user_logout', {})
            return True
        except:
            return True

    # ========== HORSE MANAGEMENT METHODS ==========

    def get_user_horses(self, user_id):
        """Get all horses managed by a user"""
        try:
            user = self.users_collection.find_one({'_id': ObjectId(user_id)})
            if not user:
                return None, "User not found"
            
            # Get horse IDs
            horse_ids = user.get('managed_horses', [])
            
            if not horse_ids:
                return [], "No horses assigned to this user"
            
            # Convert string IDs to ObjectId if needed
            object_ids = [ObjectId(h_id) if isinstance(h_id, str) else h_id for h_id in horse_ids]
            
            # Get horse data
            horses = list(self.horses_collection.find({'_id': {'$in': object_ids}}))
            
            # Convert ObjectIds to strings
            for horse in horses:
                horse['_id'] = str(horse['_id'])
            
            return horses, "Horses retrieved successfully"
        
        except Exception as e:
            print(f"Error getting user horses: {e}")
            return None, f"Error: {str(e)}"

    def assign_horse_to_user(self, user_id, horse_id):
        """Assign a horse to a user for management"""
        try:
            user = self.users_collection.find_one({'_id': ObjectId(user_id)})
            horse = self.horses_collection.find_one({'_id': ObjectId(horse_id)})
            
            if not user:
                return False, "User not found"
            if not horse:
                return False, "Horse not found"
            
            # Check if already assigned
            if str(horse_id) in user.get('managed_horses', []):
                return False, "Horse already assigned to this user"
            
            # Update user's managed horses
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$push': {'managed_horses': str(horse_id)}}
            )
            
            # Update horse's manager
            self.horses_collection.update_one(
                {'_id': ObjectId(horse_id)},
                {'$set': {'manager_id': str(user_id), 'assigned_date': datetime.utcnow()}}
            )
            
            self._log_audit(user_id, 'horse_assigned', {'horse_id': str(horse_id)})
            
            return True, "Horse assigned successfully"
        
        except Exception as e:
            print(f"Error assigning horse: {e}")
            return False, f"Error: {str(e)}"

    def unassign_horse_from_user(self, user_id, horse_id):
        """Remove a horse from a user's management"""
        try:
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$pull': {'managed_horses': str(horse_id)}}
            )
            
            # Clear horse's manager
            self.horses_collection.update_one(
                {'_id': ObjectId(horse_id)},
                {'$unset': {'manager_id': 1, 'assigned_date': 1}}
            )
            
            self._log_audit(user_id, 'horse_unassigned', {'horse_id': str(horse_id)})
            
            return True, "Horse unassigned successfully"
        
        except Exception as e:
            print(f"Error unassigning horse: {e}")
            return False, f"Error: {str(e)}"

    def get_audit_logs(self, limit=100):
        """Get audit logs (admin function)"""
        try:
            logs = list(self.audit_collection.find().sort('timestamp', -1).limit(limit))
            for log in logs:
                log['_id'] = str(log['_id'])
                log['timestamp'] = log['timestamp'].isoformat()
            return logs
        except Exception as e:
            return []

    def get_database_stats(self):
        """Get database statistics"""
        try:
            stats = {
                'users_count': self.users_collection.count_documents({}),
                'horses_count': self.horses_collection.count_documents({}),
                'audit_logs_count': self.audit_collection.count_documents({}),
                'database_name': self.db.name,
                'connected': True
            }
            return stats
        except Exception as e:
            return {'error': str(e), 'connected': False}


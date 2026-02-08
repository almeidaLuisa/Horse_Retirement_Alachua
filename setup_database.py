"""
MongoDB Database Setup Script
Initializes collections, indexes, and verifies the database is properly configured
"""

from User_Manager import UserManager
from Data_Base import main as import_horse_data
import json
from datetime import datetime

def setup_database():
    """Initialize and setup the MongoDB database"""
    
    print("\n" + "="*60)
    print("SETTING UP MONGODB DATABASE")
    print("="*60 + "\n")
    
    # Initialize UserManager (creates collections and indexes)
    manager = UserManager()
    
    print("\n✅ Database initialized successfully!")
    
    # Show database statistics
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60 + "\n")
    
    stats = manager.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show collections
    print("\n" + "="*60)
    print("AVAILABLE COLLECTIONS")
    print("="*60 + "\n")
    
    collections = manager.db.list_collection_names()
    for i, collection in enumerate(collections, 1):
        count = manager.db[collection].count_documents({})
        print(f"  {i}. {collection} - {count} documents")
    
    # Show indexes
    print("\n" + "="*60)
    print("DATABASE INDEXES")
    print("="*60 + "\n")
    
    for collection_name in ['User_Tables', 'Horse_Tables', 'Audit_Logs', 'User_Logins']:
        collection = manager.db[collection_name]
        indexes = collection.list_indexes()
        print(f"\n  {collection_name}:")
        for index in indexes:
            print(f"    - {index['name']}: {index['key']}")
    
    # Test create a user (optional)
    print("\n" + "="*60)
    print("DATABASE CONNECTION TEST")
    print("="*60 + "\n")
    
    try:
        # Test write operation
        test_user = {
            'email': f'test_setup_{datetime.utcnow().timestamp()}@example.com',
            'password': 'test_hashed_password',
            'created_at': datetime.utcnow(),
            'is_active': True,
            'role': 'test'
        }
        
        result = manager.users_collection.insert_one(test_user)
        print(f"✅ Write Test: SUCCESS (inserted ID: {result.inserted_id})")
        
        # Test read operation
        read_user = manager.users_collection.find_one({'_id': result.inserted_id})
        print(f"✅ Read Test: SUCCESS (retrieved user: {read_user['email']})")
        
        # Clean up test
        manager.users_collection.delete_one({'_id': result.inserted_id})
        print(f"✅ Delete Test: SUCCESS (cleaned up test user)")
        
    except Exception as e:
        print(f"❌ Database Test Failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ DATABASE SETUP COMPLETE!")
    print("="*60 + "\n")
    
    print("Next steps:")
    print("1. Run: python app.py (to start the Flask server)")
    print("2. Optionally import horse data with: python setup_database.py --import-horses")
    print("\n")
    
    return True

def show_user_schema():
    """Display the user document schema"""
    schema = {
        "_id": "ObjectId",
        "email": "string (unique)",
        "password": "string (hashed)",
        "first_name": "string (optional)",
        "last_name": "string (optional)",
        "created_at": "datetime",
        "updated_at": "datetime",
        "is_active": "boolean",
        "role": "string (user, admin, manager)",
        "managed_horses": "array of horse IDs",
        "permissions": "array of permission strings",
        "last_login": "datetime"
    }
    
    print("\n" + "="*60)
    print("USER DOCUMENT SCHEMA")
    print("="*60 + "\n")
    
    print(json.dumps(schema, indent=2))
    print("\n")

def show_horse_schema():
    """Display the horse document schema"""
    schema = {
        "_id": "ObjectId",
        "name": "string",
        "breed": "string",
        "gender": "string",
        "location": "string",
        "age_text": "string",
        "medical_conditions": "string",
        "arrival_date": "datetime",
        "is_deceased": "boolean",
        "deceased_date": "datetime",
        "last_farrier_date": "datetime",
        "farrier_notes": "string",
        "general_notes": "string",
        "manager_id": "string (user ID)",
        "assigned_date": "datetime",
        "profile_picture": "string (URL or base64)",
        "documents": "array"
    }
    
    print("\n" + "="*60)
    print("HORSE DOCUMENT SCHEMA")
    print("="*60 + "\n")
    
    print(json.dumps(schema, indent=2))
    print("\n")

def show_audit_schema():
    """Display the audit log schema"""
    schema = {
        "_id": "ObjectId",
        "user_id": "string (user ID)",
        "action": "string (action name)",
        "details": "object (action details)",
        "timestamp": "datetime",
        "ip_address": "string (optional)"
    }
    
    print("\n" + "="*60)
    print("AUDIT LOG DOCUMENT SCHEMA")
    print("="*60 + "\n")
    
    print(json.dumps(schema, indent=2))
    print("\n")

if __name__ == "__main__":
    import sys
    
    # Run setup
    setup_database()
    
    # Show schemas
    show_user_schema()
    show_horse_schema()
    show_audit_schema()
    
    # Check for command line arguments
    if '--import-horses' in sys.argv:
        print("\n" + "="*60)
        print("IMPORTING HORSE DATA")
        print("="*60 + "\n")
        try:
            # Uncomment the line below to use the import function from Data_Base.py
            # import_horse_data()
            print("⚠️ Please run: python Csv_Magodb_transfer.py")
            print("to import horse data from the CSV file.")
        except Exception as e:
            print(f"❌ Error importing data: {e}")

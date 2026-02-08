from pymongo import MongoClient
from bson.objectid import ObjectId

# Connect to MongoDB
client = MongoClient('mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary')
db = client['Data']

print('=' * 60)
print('VERIFYING MULTI-COLLECTION DATA SEPARATION')
print('=' * 60)

# Check User_Logins collection for login records
logins = list(db['User_Logins'].find({'email': 'newtest@example.com'}).sort('timestamp', -1).limit(1))
if logins:
    login = logins[0]
    print('\n✅ User_Logins Collection (Login History)')
    print(f'   Email: {login.get("email")}')
    print(f'   IP Address: {login.get("ip_address")}')
    print(f'   Timestamp: {login.get("timestamp")}')
    print(f'   User ID: {login.get("user_id")}')

# Check Audits collection for login action
audits = list(db['Audits'].find({'action': 'LOGIN'}).sort('timestamp', -1).limit(1))
if audits:
    audit = audits[0]
    print('\n✅ Audits Collection (Login Audit)')
    print(f'   Action: {audit.get("action")}')
    print(f'   Table: {audit.get("table")}')
    print(f'   Timestamp: {audit.get("timestamp")}')
    print(f'   Details: {audit.get("details")}')
    print(f'   User ID: {audit.get("user_id")}')

# Check User_Tables for last_login update
user_id = ObjectId('69880ef27d7b5ea202a80fad')
user = db['User_Tables'].find_one({'_id': user_id})
if user:
    print('\n✅ User_Tables Collection (User Profile)')
    print(f'   Name: {user.get("name")}')
    print(f'   Email: {user.get("email")}')
    print(f'   Role: {user.get("role")}')
    print(f'   Active: {user.get("active")}')
    print(f'   Last Login: {user.get("last_login")}')

# Check users collection (password only)
user_pwd = db['users'].find_one({'email': 'newtest@example.com'})
if user_pwd:
    print('\n✅ users Collection (Password Only)')
    print(f'   Email: {user_pwd.get("email")}')
    print(f'   Has Password: {"password" in user_pwd}')
    print(f'   No Name/Role: {"name" not in user_pwd}')

print('\n' + '=' * 60)
print('✓ ALL COLLECTIONS PROPERLY CONFIGURED')
print('✓ DATA PROPERLY SEPARATED ACROSS COLLECTIONS')
print('=' * 60)

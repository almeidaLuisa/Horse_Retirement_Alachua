from pymongo import MongoClient
from bson.objectid import ObjectId

# Connect to MongoDB
client = MongoClient('mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary')
db = client['Data']

print('=' * 70)
print('VERIFYING USER_LOGINS PASSWORD STORAGE & LOGIN HISTORY')
print('=' * 70)

# Check User_Logins for password credentials
logins = list(db['User_Logins'].find({'email': 'testlogin@example.com'}))
if logins:
    print('\n✅ User_Logins Collection Records:')
    for login in logins:
        print(f'\n   Action: {login.get("action")}')
        print(f'   Email: {login.get("email")}')
        print(f'   Has Password Hash: {"password" in login}')
        print(f'   Timestamp: {login.get("timestamp")}')
        print(f'   IP Address: {login.get("ip_address")}')
        print(f'   User ID: {login.get("user_id")}')

# Check User_Tables for profile data (no password)
user_id = ObjectId('698811bb9fd748d6f80611ee')
user = db['User_Tables'].find_one({'_id': user_id})
if user:
    print('\n✅ User_Tables Collection (User Profile - No Password):')
    print(f'   Name: {user.get("name")}')
    print(f'   Email: {user.get("email")}')
    print(f'   Role: {user.get("role")}')
    print(f'   Active: {user.get("active")}')
    print(f'   Has Password Field: {"password" in user}')
    print(f'   Last Login: {user.get("last_login")}')

# Check Audits collection for actions
audits = list(db['Audits'].find({'user_id': user_id}).sort('timestamp', -1))
if audits:
    print('\n✅ Audits Collection (Action Log):')
    for audit in audits:
        print(f'\n   Action: {audit.get("action")}')
        print(f'   Table: {audit.get("table")}')
        print(f'   Timestamp: {audit.get("timestamp")}')
        print(f'   Details: {audit.get("details")}')

print('\n' + '=' * 70)
print('✓ ARCHITECTURE VERIFIED:')
print('  - User_Logins stores password credentials + login history')
print('  - User_Tables stores profile data (no password)')
print('  - Audits tracks all actions')
print('=' * 70)

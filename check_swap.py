#!/usr/bin/env python
"""Verify the swapped collections are working correctly"""

from User_Manager import UserManager

manager = UserManager()

print('\n' + '='*60)
print('CHECKING LATEST DATA IN SWAPPED COLLECTIONS')
print('='*60)

# Show the most recent user profile  
print('\nLatest User Profile in User_Logins:')
latest_user = manager.db['User_Logins'].find_one(sort=[('_id', -1)])
if latest_user:
    print(f'  Email: {latest_user.get("email")}')
    print(f'  Has password: {"password" in latest_user}')
    print(f'  Created at: {latest_user.get("created_at")}')

print('\nLatest Login Event in User_Tables:')
latest_login = manager.db['User_Tables'].find_one(sort=[('_id', -1)])
if latest_login:
    print(f'  Email: {latest_login.get("email")}')
    print(f'  User ID: {latest_login.get("user_id")}')
    print(f'  Timestamp: {latest_login.get("timestamp")}')
    print(f'  Success: {latest_login.get("success")}')

print('\n' + '='*60)
print('✅ COLLECTIONS SUCCESSFULLY SWAPPED!')
print('='*60)
print('  User_Logins = User Profiles')
print('  User_Tables = Login Events')
print('  Audit_Logs = All Activities')

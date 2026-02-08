#!/usr/bin/env python
"""Verify data is stored in the correct collections after swap"""

from User_Manager import UserManager
import json

manager = UserManager()

print('\n' + '='*60)
print('VERIFYING COLLECTION CONTENTS')
print('='*60)

# Check User_Logins (should now contain user profiles)
print('\n' + '='*60)
print('USER_LOGINS Collection (User Profiles)')
print('='*60)
user_logins_count = manager.db['User_Logins'].count_documents({})
print(f'Total documents: {user_logins_count}')

if user_logins_count > 0:
    sample = manager.db['User_Logins'].find_one({})
    if sample:
        print(f'\nSample user document:')
        print(f"  Email: {sample.get('email')}")
        print(f"  Has password: {'password' in sample}")
        print(f"  Created at: {sample.get('created_at')}")

# Check User_Tables (should now contain login events)
print('\n' + '='*60)
print('USER_TABLES Collection (Login Events)')
print('='*60)
user_tables_count = manager.db['User_Tables'].count_documents({})
print(f'Total documents: {user_tables_count}')

if user_tables_count > 0:
    sample = manager.db['User_Tables'].find_one({})
    if sample:
        print(f'\nSample login record:')
        print(f"  Email/User_ID: {sample.get('email') or sample.get('user_id')}")
        print(f"  Timestamp: {sample.get('timestamp')}")
        print(f"  Success: {sample.get('success')}")

# Check Audit_Logs
print('\n' + '='*60)
print('AUDIT_LOGS Collection (All Activities)')
print('='*60)
audit_count = manager.db['Audit_Logs'].count_documents({})
print(f'Total documents: {audit_count}')

if audit_count > 0:
    sample = manager.db['Audit_Logs'].find_one({})
    if sample:
        print(f'\nSample audit log:')
        print(f"  Action: {sample.get('action')}")
        print(f"  User ID: {sample.get('user_id')}")
        print(f"  Timestamp: {sample.get('timestamp')}")

print('\n' + '='*60)
print('✅ VERIFICATION COMPLETE')
print('='*60)
print(f'\nSummary:')
print(f'  • User_Logins (Profiles): {user_logins_count} documents')
print(f'  • User_Tables (Login Events): {user_tables_count} documents')
print(f'  • Audit_Logs (All Activities): {audit_count} documents')

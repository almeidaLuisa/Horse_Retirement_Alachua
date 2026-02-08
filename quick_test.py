#!/usr/bin/env python
"""Quick test of the Flask API with MongoDB"""

import requests
import json
import sys
import time

BASE_URL = 'http://localhost:5000'

def test_registration():
    print('\n' + '='*60)
    print('TEST 1: User Registration')
    print('='*60)
    
    email = f'test_user_{int(time.time())}@example.com'
    password = 'TestPassword123'
    
    response = requests.post(
        f'{BASE_URL}/api/auth/register',
        json={'email': email, 'password': password},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f'Email: {email}')
    print(f'Status Code: {response.status_code}')
    print(f'Response: {json.dumps(response.json(), indent=2)}')
    
    return response.status_code == 201, email, password

def test_login(email, password):
    print('\n' + '='*60)
    print('TEST 2: User Login')
    print('='*60)
    
    response = requests.post(
        f'{BASE_URL}/api/auth/login',
        json={'email': email, 'password': password},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f'Email: {email}')
    print(f'Status Code: {response.status_code}')
    print(f'Response: {json.dumps(response.json(), indent=2)}')
    
    return response.status_code == 200, response.json().get('token')

if __name__ == '__main__':
    try:
        # Test registration
        reg_success, test_email, test_password = test_registration()
        
        if reg_success:
            print('\n✅ Registration successful!')
            
            # Test login
            login_success, token = test_login(test_email, test_password)
            
            if login_success:
                print('\n✅ Login successful!')
                print(f'\n✅ Token received: {token[:50]}...')
            else:
                print('\n❌ Login failed!')
                sys.exit(1)
        else:
            print('\n❌ Registration failed!')
            sys.exit(1)
            
    except Exception as e:
        print(f'\n❌ Error: {e}')
        sys.exit(1)

    print('\n' + '='*60)
    print('✅ ALL TESTS PASSED!')
    print('='*60)

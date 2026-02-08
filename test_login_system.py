"""
Quick test script to verify the login system is working
Run this after starting the Flask server to test basic functionality
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")

def test_health_check():
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register(email, password):
    print_section(f"TEST 2: User Registration")
    print(f"Email: {email}\nPassword: {password}\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 201, response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def test_login(email, password):
    print_section("TEST 3: User Login")
    print(f"Email: {email}\nPassword: {password}\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            return True, data.get('token'), data.get('user')
        return False, None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None, None

def test_get_profile(token):
    print_section("TEST 4: Get User Profile")
    print(f"Token: {token[:20]}...\n")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/user/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_update_profile(token):
    print_section("TEST 5: Update User Profile")
    print(f"Token: {token[:20]}...\n")
    
    update_data = {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "555-1234"
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/user/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_change_password(token, old_password, new_password):
    print_section("TEST 6: Change Password")
    print(f"Token: {token[:20]}...")
    print(f"Old Password: {old_password}")
    print(f"New Password: {new_password}\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/user/change-password",
            json={"old_password": old_password, "new_password": new_password},
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_logout(token):
    print_section("TEST 7: Logout")
    print(f"Token: {token[:20]}...\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("HORSE RETIREMENT ALACHUA - LOGIN SYSTEM TEST")
    print("="*60)
    print("\nMake sure the Flask server is running: python app.py")
    print("Server should be accessible at: http://localhost:5000\n")
    
    input("Press Enter to start testing...")
    
    # Test data
    test_email = "testuser@example.com"
    test_password = "testpassword123"
    new_password = "newpassword456"
    
    results = []
    
    # Test 1: Health Check
    if not test_health_check():
        print("\n❌ FAILED: Cannot connect to server. Is it running?")
        return
    results.append(("Health Check", True))
    
    # Test 2: Register
    success, response = test_register(test_email, test_password)
    results.append(("Registration", success))
    
    if not success:
        # Try logging in with existing user
        print("\n⚠️  Registration failed (user may already exist). Testing with existing user...\n")
    
    # Test 3: Login
    success, token, user = test_login(test_email, test_password)
    results.append(("Login", success))
    
    if not success:
        print("\n❌ FAILED: Cannot login. Stopping tests.")
        print_summary(results)
        return
    
    # Test 4: Get Profile
    success = test_get_profile(token)
    results.append(("Get Profile", success))
    
    # Test 5: Update Profile
    success = test_update_profile(token)
    results.append(("Update Profile", success))
    
    # Test 6: Change Password
    success = test_change_password(token, test_password, new_password)
    results.append(("Change Password", success))
    
    # Test 7: Logout
    success = test_logout(token)
    results.append(("Logout", success))
    
    # Print summary
    print_summary(results)

def print_summary(results):
    print_section("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Your login system is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check the errors above.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

# Quick Start Guide - Login System

## Step 1: Install Dependencies (One Time)

Open PowerShell in your project directory and run:

```powershell
pip install -r requirements.txt
```

This installs all required packages:
- Flask (web framework)
- PyJWT (token authentication)
- PyMongo (MongoDB driver)
- And more...

## Step 2: Start the Flask Server

In PowerShell, run:

```powershell
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

**Leave this terminal open!** The server must be running for the login system to work.

## Step 3: Test the System

### Option A: Quick Test with Test Script (Recommended)

Open a **NEW** PowerShell window and run:

```powershell
python test_login_system.py
```

This will automatically test all the login functionality.

### Option B: Manual Testing

1. Open your web browser
2. Navigate to: `file:///C:/Users/ricar/OneDrive/Documents/Code/C++/COP3503c/Horse_Retirement_Alachua/frontend/register_page.html`
3. Create an account with:
   - Email: `testuser@example.com`
   - Password: `password123`
4. Go to login page and login with those credentials
5. You should be redirected to home page with a token stored

## Common Issues & Solutions

### "Network error. Is the server running?"
**Solution:** Make sure you have `python app.py` running in another terminal

### "Connection refused"
**Solution:** Flask server isn't running on port 5000. Start it with `python app.py`

### "ModuleNotFoundError"
**Solution:** Run `pip install -r requirements.txt` to install dependencies

### "MongoDB connection error"
**Solution:** Check your internet connection - MongoDB Atlas requires internet access

## Project Structure

```
Horse_Retirement_Alachua/
├── app.py                          # Flask server (START THIS)
├── User_Manager.py                 # Authentication logic
├── test_login_system.py            # Test script
├── requirements.txt                # Dependencies
├── LOGIN_SYSTEM_README.md          # Full documentation
├── QUICK_START.md                  # This file
└── frontend/
    ├── auth.js                     # Frontend auth helper
    ├── login_page.html             # Login page
    ├── register_page.html          # Registration page
    ├── home_page.html              # Home page (protected)
    └── ...
```

## API Endpoints at a Glance

```
POST   /api/auth/register          → Register new user
POST   /api/auth/login             → Login (get token)
POST   /api/auth/logout            → Logout
GET    /api/user/profile           → Get profile (protected)
PUT    /api/user/profile           → Update profile (protected)
POST   /api/user/change-password   → Change password (protected)
```

## What's Included

✅ User registration with email validation
✅ Secure password hashing
✅ JWT token authentication
✅ User profile management
✅ Password change functionality
✅ MongoDB database integration
✅ Error handling and validation
✅ Frontend authentication utilities
✅ Test suite

## Next Steps

### To use in other pages:

1. Include `auth.js` in your HTML:
```html
<script src="auth.js"></script>
```

2. Use the auth manager:
```javascript
// On page load, require authentication
document.addEventListener('DOMContentLoaded', () => {
    auth.requireAuth();  // Redirect to login if not authenticated
});

// Make API calls with token
const response = await auth.request('/api/user/profile', {
    method: 'GET'
});

// Logout user
logout();
```

3. Display user info:
```javascript
const user = auth.getUser();
console.log(`Logged in as: ${user.email}`);
```

## Important Security Notes

⚠️ **For Production:**
1. Change the `SECRET_KEY` in User_Manager.py
2. Use HTTPS instead of HTTP
3. Add email verification
4. Enable password reset functionality
5. Consider adding 2-factor authentication

## Support & Documentation

For detailed API documentation, see: `LOGIN_SYSTEM_README.md`

---

**Ready to go?** Run `python app.py` and test with `python test_login_system.py`!

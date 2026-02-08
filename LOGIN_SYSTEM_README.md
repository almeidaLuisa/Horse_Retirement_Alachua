# Horse Retirement Alachua - Login System Setup

## Overview

A complete authentication system has been implemented with:
- **User Registration & Login** via MongoDB
- **Password Hashing** with werkzeug
- **JWT Token Authentication** for API security
- **User Profile Management**
- **Password Change Functionality**

## Files Created/Modified

### Backend Files
1. **User_Manager.py** - Core authentication logic
   - User registration with validation
   - Login with password hashing
   - JWT token generation and verification
   - User profile management

2. **app.py** - Flask application with API routes
   - `/api/auth/register` - Register new user
   - `/api/auth/login` - Login and get token
   - `/api/auth/logout` - Logout
   - `/api/user/profile` - Get/Update user profile
   - `/api/user/change-password` - Change password

### Frontend Files
1. **frontend/auth.js** - Authentication utility class
   - `AuthManager` class for token/user management
   - Helper functions for authenticated requests

2. **frontend/login_page.html** - Updated with better error handling
3. **frontend/register_page.html** - Updated with validation and loading states

### Configuration
- **requirements.txt** - Updated with new dependencies (PyJWT, etc.)

## Getting Started

### 1. Install Dependencies

```bash
# Activate your virtual environment (if needed)
# .venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Run the Flask Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 3. Access the Application

Open your browser and navigate to:
- **Home Page**: `file:///path/to/frontend/home_page.html`
- **Login**: `file:///path/to/frontend/login_page.html`
- **Register**: `file:///path/to/frontend/register_page.html`

## API Endpoints

### Authentication Endpoints

#### POST `/api/auth/register`
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user_id": "64a5f3c9d1e2c3f4g5h6i7j8"
}
```

#### POST `/api/auth/login`
Login and receive JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "user_id": "64a5f3c9d1e2c3f4g5h6i7j8",
    "email": "user@example.com",
    "role": "user"
  }
}
```

#### POST `/api/auth/logout`
Logout user (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### User Profile Endpoints

#### GET `/api/user/profile`
Get current user's profile (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "user": {
    "_id": "64a5f3c9d1e2c3f4g5h6i7j8",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

#### PUT `/api/user/profile`
Update user profile (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "555-1234"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "user": { ... }
}
```

#### POST `/api/user/change-password`
Change user password (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "old_password": "oldpassword",
  "new_password": "newpassword"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

## Frontend Usage

### Using the AuthManager class

In your HTML pages, include the auth.js file:

```html
<script src="auth.js"></script>
```

Then use the auth manager:

```javascript
// Check if logged in
if (auth.isLoggedIn()) {
    console.log("User is logged in:", auth.getUser());
}

// Require authentication
auth.requireAuth();

// Make authenticated request
const response = await auth.request('/api/user/profile', {
    method: 'GET'
});

// Logout
logout();
```

## Security Considerations

### Current Implementation
1. ✅ Passwords are hashed with werkzeug.security
2. ✅ JWT tokens expire after 7 days
3. ✅ Token validation on protected endpoints
4. ✅ Email validation on registration

### Recommended Improvements for Production
1. **Change SECRET_KEY** - Update the SECRET_KEY in User_Manager.py to a strong random value
2. **HTTPS** - Always use HTTPS in production
3. **Token Blacklist** - Implement token blacklist for logout
4. **Rate Limiting** - Add rate limiting to prevent brute force attacks
5. **Two-Factor Authentication** - Consider adding 2FA
6. **Input Validation** - Add more comprehensive input validation
7. **CORS Configuration** - Configure CORS more restrictively for production

## Testing

### Register a New User
1. Go to `register_page.html`
2. Enter an email (e.g., `user@example.com`)
3. Enter a password (minimum 6 characters)
4. Click "Sign Up"

### Login
1. Go to `login_page.html`
2. Enter the email and password
3. Click "Login"
4. You should be redirected to `home_page.html` with a token stored

### Test API with curl

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Get Profile (replace TOKEN with actual token)
curl -X GET http://localhost:5000/api/user/profile \
  -H "Authorization: Bearer TOKEN"
```

## Troubleshooting

### "Network error. Is the server running?"
- Make sure Flask server is running with `python app.py`
- Check that the server is on port 5000
- Verify CORS is properly configured

### "Invalid email or password"
- Check that email and password are correct
- Ensure the user account exists (register first if needed)

### Token-related errors
- Tokens expire after 7 days
- Copy the token from localStorage if needed
- Ensure token is in correct format: `Bearer <token>`

### MongoDB Connection Issues
- Verify the MongoDB URI in User_Manager.py and Data_Base.py
- Check network connectivity
- Ensure credentials are correct

## Next Steps

1. **Update HOME_PAGE** - Add user info display and logout button
2. **Update USER_PROFILE_PAGE** - Implement profile editing
3. **Add Password Reset** - Implement "Forgot Password" functionality
4. **Add Email Verification** - Verify user email on registration
5. **Integrate with Horse Data** - Connect user authentication with horse database operations

## Database Schema

The `users` collection in MongoDB has the following structure:

```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "password": "hashed_password_string",
  "created_at": ISODate,
  "is_active": true,
  "role": "user",
  "first_name": "John",       // Optional
  "last_name": "Doe",         // Optional
  "phone": "555-1234"         // Optional
}
```

---

**Created:** February 7, 2026
**System:** Horse Retirement Alachua Authentication System

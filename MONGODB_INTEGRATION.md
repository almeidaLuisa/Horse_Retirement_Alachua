# MongoDB Integration Documentation

## Overview

The Horse Retirement Alachua system is now fully integrated with MongoDB. Users are authenticated and linked to the horses they manage.

## Database Structure

### Database Name
```
Alejandro's_Labor_Camp
```

### Collections

#### 1. **users** Collection
Stores user account information and authentication data.

**Document Structure:**
```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "password": "hashed_password",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": ISODate("2026-02-08T02:53:06Z"),
  "updated_at": ISODate("2026-02-08T02:53:06Z"),
  "is_active": true,
  "role": "user|admin|manager",
  "managed_horses": ["horse_id_1", "horse_id_2"],
  "permissions": ["view_horses", "view_profile"],
  "last_login": ISODate("2026-02-08T10:30:00Z")
}
```

**Indexes:**
- `email` (unique)
- `created_at`

**Roles:**
- `user` - Standard user
- `manager` - Can manage horses
- `admin` - Full system access

#### 2. **horses** Collection
Stores horse information (imported from CSV).

**Document Structure:**
```json
{
  "_id": ObjectId,
  "name": "Thunder",
  "breed": "Thoroughbred",
  "gender": "Male",
  "location": "Pasture A",
  "age_text": "15",
  "medical_conditions": "Arthritis",
  "arrival_date": ISODate("2023-01-15T00:00:00Z"),
  "is_deceased": false,
  "deceased_date": null,
  "last_farrier_date": ISODate("2026-01-20T00:00:00Z"),
  "farrier_notes": "Needs new shoes",
  "general_notes": "Friendly, good with handlers",
  "manager_id": "user_id_1",
  "assigned_date": ISODate("2026-02-08T03:00:00Z"),
  "profile_picture": null,
  "documents": []
}
```

**Indexes:**
- `name`
- `manager_id`

#### 3. **audit_logs** Collection
Maintains audit trail of user actions for security and compliance.

**Document Structure:**
```json
{
  "_id": ObjectId,
  "user_id": "user_id_1",
  "action": "user_login|password_changed|horse_assigned",
  "details": {
    "email": "user@example.com",
    "reason": "wrong_password"
  },
  "timestamp": ISODate("2026-02-08T10:30:00Z"),
  "ip_address": "192.168.1.1"
}
```

**Indexes:**
- `user_id`
- `timestamp`
- `action`

## API Endpoints - Authentication

### POST `/api/auth/register`
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user_id": "507f1f77bcf86cd799439011"
}
```

### POST `/api/auth/login`
Authenticate and get JWT token.

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
    "user_id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "user",
    "managed_horses": ["507f2f77bcf86cd799439012"]
  }
}
```

### POST `/api/auth/logout`
Logout current user (requires authentication).

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

## API Endpoints - User Profile

### GET `/api/user/profile`
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
    "_id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "user",
    "created_at": "Sun, 08 Feb 2026 02:53:06 GMT",
    "is_active": true
  }
}
```

### PUT `/api/user/profile`
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

### POST `/api/user/change-password`
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

## API Endpoints - Horse Management

### GET `/api/user/horses`
Get all horses managed by current user (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Horses retrieved successfully",
  "count": 5,
  "horses": [
    {
      "_id": "507f2f77bcf86cd799439012",
      "name": "Thunder",
      "breed": "Thoroughbred",
      "gender": "Male",
      "location": "Pasture A",
      "age_text": "15",
      "manager_id": "507f1f77bcf86cd799439011",
      "assigned_date": "Sun, 08 Feb 2026 03:00:00 GMT"
    }
  ]
}
```

### POST `/api/user/horses/<horse_id>`
Assign a horse to current user (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Response (200):**
```json
{
  "success": true,
  "message": "Horse assigned successfully",
  "horse_id": "507f2f77bcf86cd799439012"
}
```

### DELETE `/api/user/horses/<horse_id>`
Remove a horse from current user's management (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Horse unassigned successfully",
  "horse_id": "507f2f77bcf86cd799439012"
}
```

## API Endpoints - Admin

### GET `/api/admin/stats`
Get database statistics (admin only).

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response (200):**
```json
{
  "success": true,
  "stats": {
    "users_count": 5,
    "horses_count": 25,
    "audit_logs_count": 127,
    "database_name": "Alejandro's_Labor_Camp",
    "connected": true
  }
}
```

### GET `/api/admin/audit-logs`
Get audit logs (admin only).

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Query Parameters:**
- `limit` (optional, default: 100) - Number of logs to retrieve

**Response (200):**
```json
{
  "success": true,
  "count": 50,
  "logs": [
    {
      "_id": "507f3f77bcf86cd799439013",
      "user_id": "507f1f77bcf86cd799439011",
      "action": "user_login",
      "details": {
        "email": "user@example.com"
      },
      "timestamp": "2026-02-08T10:30:00"
    }
  ]
}
```

## Database Queries

### Find all horses assigned to a user
```python
user_id = "507f1f77bcf86cd799439011"
horses = collection.find({"manager_id": user_id})
```

### Find all users managing a specific horse
```python
horse_id = "507f2f77bcf86cd799439012"
users = users_collection.find({"managed_horses": horse_id})
```

### Get user's action history
```python
user_id = "507f1f77bcf86cd799439011"
logs = audit_collection.find({"user_id": user_id}).sort("timestamp", -1)
```

### Find all active users
```python
active_users = users_collection.find({"is_active": True})
```

## Security Features

### Password Security
- ✅ Passwords hashed with Werkzeug (pbkdf2)
- ✅ Minimum 6 characters required
- ✅ Can be changed via `/api/user/change-password`

### Authentication
- ✅ JWT tokens (expires in 7 days)
- ✅ Token validation on protected endpoints
- ✅ Automatic logout on expiration

### Authorization
- ✅ Role-based access control (user, admin, manager)
- ✅ Permission-based endpoint access
- ✅ User isolation (can't access other users' data)

### Audit Trail
- ✅ All critical actions logged
- ✅ Login/logout tracking
- ✅ Password change history
- ✅ Horse assignment history

## Maintenance

### View Database Statistics
```bash
python setup_database.py
```

This will show:
- Connection status
- Collection counts
- Available indexes
- Document schemas

### Import Horse Data from CSV
```bash
python Csv_Magodb_transfer.py
```

This will:
- Read `Horse_Table.csv`
- Create horse documents in MongoDB
- Create proper indexes

### Verify Database Connection
```bash
python test_login_system.py
```

This will:
- Test all authentication endpoints
- Verify database operations
- Create sample user data

## Troubleshooting

### "Invalid email or password" on login
**Solution:** Verify user exists with correct credentials. Check email is lowercase in database.

### "Token expired"
**Solution:** Tokens expire after 7 days. Users need to login again to get new token.

### "Admin access required"
**Solution:** User role must be set to 'admin' to access admin endpoints.

### MongoDB Connection Error
**Solution:** 
- Check internet connection
- Verify MongoDB URI credentials
- Ensure IP is whitelisted in MongoDB Atlas

### Horse assignment fails
**Solution:**
- Verify user_id exists in users collection
- Verify horse_id exists in horses collection
- Check user's role has 'horse_management' permission

## Best Practices

1. **Always include Authorization header** when accessing protected endpoints
2. **Store tokens securely** - Keep in localStorage only (not cookies)
3. **Handle token expiration** - Implement refresh logic in frontend
4. **Validate all inputs** - Client-side and server-side
5. **Use HTTPS in production** - Never send tokens over HTTP
6. **Rotate SECRET_KEY regularly** - Update in User_Manager.py
7. **Monitor audit logs** - Regularly review for suspicious activity

## Next Steps

1. Start Flask server: `python app.py`
2. Test frontend at: `http://localhost:5000/register_page.html`
3. Create test users and assign horses
4. View user information and managed horses
5. Monitor database activity via audit logs

---

**Last Updated:** February 8, 2026
**System:** Horse Retirement Alachua
**Database:** MongoDB Atlas

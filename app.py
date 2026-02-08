from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from User_Manager import UserManager
from functools import wraps
import os

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# Initialize User Manager
user_manager = UserManager()

# Middleware to verify token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Verify token
        success, payload, message = user_manager.verify_token(token)
        if not success:
            return jsonify({'error': message}), 401
        
        # Pass user data to route
        kwargs['current_user'] = payload
        return f(*args, **kwargs)
    
    return decorated

# ========== AUTHENTICATION ROUTES ==========

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].strip()
        password = data['password']
        
        # Register user
        success, message, user_id = user_manager.register_user(email, password)
        
        if not success:
            return jsonify({'error': message}), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'user_id': user_id
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].strip()
        password = data['password']
        
        # Authenticate user
        success, message, token, user_data = user_manager.login_user(email, password)
        
        if not success:
            return jsonify({'error': message}), 401
        
        return jsonify({
            'success': True,
            'message': message,
            'token': token,
            'user': user_data
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout user"""
    # Token is removed client-side, but we can perform cleanup here if needed
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200

# ========== USER PROFILE ROUTES ==========

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get current user profile"""
    try:
        user = user_manager.get_user_by_id(current_user['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/user/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update user profile (sensitive fields are protected in the manager)
        success = user_manager.update_user_profile(current_user['user_id'], data)
        
        if not success:
            return jsonify({'error': 'Failed to update profile'}), 400
        
        # Get updated user data
        user = user_manager.get_user_by_id(current_user['user_id'])
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/user/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change user password"""
    try:
        data = request.get_json()
        
        if not data or not data.get('old_password') or not data.get('new_password'):
            return jsonify({'error': 'Old password and new password are required'}), 400
        
        old_password = data['old_password']
        new_password = data['new_password']
        
        success, message = user_manager.change_password(
            current_user['user_id'],
            old_password,
            new_password
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# ========== HORSE MANAGEMENT ROUTES ==========

@app.route('/api/user/horses', methods=['GET'])
@token_required
def get_user_horses(current_user):
    """Get all horses managed by the current user"""
    try:
        horses, message = user_manager.get_user_horses(current_user['user_id'])
        
        if horses is None:
            return jsonify({'error': message}), 404
        
        return jsonify({
            'success': True,
            'message': message,
            'horses': horses,
            'count': len(horses) if isinstance(horses, list) else 0
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/user/horses/<horse_id>', methods=['POST'])
@token_required
def assign_horse(current_user, horse_id):
    """Assign a horse to the current user"""
    try:
        success, message = user_manager.assign_horse_to_user(current_user['user_id'], horse_id)
        
        if not success:
            return jsonify({'error': message}), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'horse_id': horse_id
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/user/horses/<horse_id>', methods=['DELETE'])
@token_required
def unassign_horse(current_user, horse_id):
    """Remove a horse from the current user's management"""
    try:
        success, message = user_manager.unassign_horse_from_user(current_user['user_id'], horse_id)
        
        if not success:
            return jsonify({'error': message}), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'horse_id': horse_id
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# ========== DATABASE STATISTICS ==========

@app.route('/api/admin/stats', methods=['GET'])
@token_required
def get_stats(current_user):
    """Get database statistics (admin only)"""
    try:
        # Check if user is admin
        if current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        stats = user_manager.get_database_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/admin/audit-logs', methods=['GET'])
@token_required
def get_audit_logs(current_user):
    """Get audit logs (admin only)"""
    try:
        # Check if user is admin
        if current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        limit = request.args.get('limit', 100, type=int)
        logs = user_manager.get_audit_logs(limit=limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500



@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running'
    }), 200

# ========== FRONTEND ROUTES ==========

@app.route('/')
def index():
    """Serve home page"""
    return send_from_directory('frontend', 'home_page.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    """Serve frontend files"""
    return send_from_directory('frontend', filename)

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Use debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5000)

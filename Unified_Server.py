from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import smtplib
import secrets
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

# --- CONFIGURATION ---
app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max upload
# Allow CORS for all domains
CORS(app)

# Email Configuration (use env vars in production, fallback to local defaults)
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'luisalmeida0106@gmail.com')
SMTP_APP_PASSWORD = os.environ.get('SMTP_APP_PASSWORD', 'oqrx kaip oppt pmtt')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5000')  # In production, set to your Render URL

# Database Connection
URI = os.environ.get('MONGODB_URI', 'mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary')
DB_NAME = "Data"

try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    
    # Collections
    user_logins = db['User_Logins']
    horse_collection = db['Horse_Tables']
    audit_collection = db['Audits']
    # RESTORED: Daily Obs Collection
    daily_obs_collection = db['DailyObs_Tables']
    docs_collection = db['Docs_Tables']
    treatment_collection = db['Horse_Treatment_Tables']
    actions_collection = db['Actions_Tables']
    
    print(f"✅ UNIFIED SERVER CONNECTED to {DB_NAME}")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")

# --- HELPERS ---
def format_doc(doc):
    if not doc: return None
    doc['_id'] = str(doc['_id'])
    return doc

def send_verification_email(to_email, first_name, token):
    """Send a verification email with a clickable link."""
    verify_url = f"{FRONTEND_URL}/verify_email.html?token={token}"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Verify your email — Retirement Home for Horses'
    msg['From'] = SMTP_EMAIL
    msg['To'] = to_email
    
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:2rem;">
        <div style="text-align:center;margin-bottom:1.5rem;">
            <h1 style="color:#388e3c;margin:0;">🐴 Retirement Home for Horses</h1>
        </div>
        <h2 style="color:#333;">Welcome, {first_name}!</h2>
        <p style="color:#555;font-size:1rem;line-height:1.6;">
            Thank you for registering. Please verify your email address by clicking the button below:
        </p>
        <div style="text-align:center;margin:2rem 0;">
            <a href="{verify_url}" style="background:linear-gradient(135deg,#9CD479,#79AED4);color:#fff;text-decoration:none;padding:14px 36px;border-radius:10px;font-weight:bold;font-size:1rem;display:inline-block;">Verify My Email</a>
        </div>
        <p style="color:#999;font-size:0.85rem;text-align:center;">If the button doesn't work, paste this link in your browser:<br>
            <a href="{verify_url}" style="color:#79AED4;">{verify_url}</a>
        </p>
        <hr style="border:none;border-top:1px solid #eee;margin:2rem 0;">
        <p style="color:#bbb;font-size:0.75rem;text-align:center;">Retirement Home for Horses, Inc. — Alachua, FL</p>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"✅ Verification email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


# --- CHANGE NOTIFICATION EMAILS ---

# Map actions to the notification preference key they belong to
ACTION_TO_PREF = {
    'ADD_HORSE': 'horse',
    'UPDATE_HORSE': 'horse',
    'DELETE_HORSE': 'horse',
    'UPDATE_PROFILE': 'security',
    'CHANGE_PASSWORD': 'security',
    'LOGIN': 'security',
    'ADD_DAILY_OBS': 'obs',
    'DELETE_DAILY_OBS': 'obs',
    'TODO_REMINDER': 'todo',
}

# Friendly labels for actions
ACTION_LABELS = {
    'ADD_HORSE': '🐴 New Horse Added',
    'UPDATE_HORSE': '✏️ Horse Updated',
    'DELETE_HORSE': '🗑️ Horse Deleted',
    'UPDATE_PROFILE': '👤 User Profile Updated',
    'CHANGE_PASSWORD': '🔑 Password Changed',
}

def _build_changes_html(details):
    """Build HTML for the changes list in a notification email."""
    changes = details.get('changes', [])
    if not changes:
        # Just show the details as key-value pairs
        items = ''.join(
            f'<tr><td style="padding:6px 12px;font-weight:600;color:#388e3c;">{k}</td>'
            f'<td style="padding:6px 12px;">{v}</td></tr>'
            for k, v in details.items() if k != 'changes'
        )
        return f'<table style="width:100%;border-collapse:collapse;margin:1rem 0;">{items}</table>'
    
    # Detailed changes (old → new)
    rows = ''
    for c in changes:
        rows += (
            f'<tr>'
            f'<td style="padding:6px 12px;font-weight:600;color:#388e3c;">{c.get("field","")}</td>'
            f'<td style="padding:6px 12px;color:#c62828;text-decoration:line-through;">{c.get("old","—")}</td>'
            f'<td style="padding:6px 12px;color:#2e7d32;font-weight:600;">{c.get("new","—")}</td>'
            f'</tr>'
        )
    horse_name = details.get('horse_name', '')
    header = f'<p style="font-weight:700;color:#263238;margin-bottom:0.5rem;">Horse: {horse_name}</p>' if horse_name else ''
    return (
        f'{header}'
        f'<table style="width:100%;border-collapse:collapse;margin:1rem 0;font-size:0.9rem;">'
        f'<tr style="background:#e8f5e9;"><th style="padding:8px 12px;text-align:left;">Field</th>'
        f'<th style="padding:8px 12px;text-align:left;">Old</th>'
        f'<th style="padding:8px 12px;text-align:left;">New</th></tr>'
        f'{rows}</table>'
    )

def _user_wants_notification(user_doc, action):
    """Check if a user's notification preferences allow this action type."""
    pref_key = ACTION_TO_PREF.get(action)
    if not pref_key:
        return False  # unknown action type, don't send
    
    # Default prefs: todo=True, obs=True, horse=False, security=True
    defaults = {'todo': True, 'obs': True, 'horse': False, 'security': True}
    prefs = user_doc.get('notification_prefs', defaults)
    
    return prefs.get(pref_key, defaults.get(pref_key, False))

def send_change_notification(action, user_id, details):
    """Send email notification to users who opted in. Runs in background thread."""
    if action not in ACTION_TO_PREF:
        return

    def _send():
        try:
            # Get all verified, active users (not just admins)
            users = list(user_logins.find(
                {'email_verified': True, 'is_active': True},
                {'email': 1, 'first_name': 1, 'notification_prefs': 1, 'role': 1}
            ))
            if not users:
                print("ℹ️ No users to notify.")
                return

            label = ACTION_LABELS.get(action, action)
            changes_html = _build_changes_html(details)
            timestamp = datetime.utcnow().strftime('%b %d, %Y at %I:%M %p UTC')

            for user in users:
                # Skip the user who made the change (don't notify yourself)
                if user.get('email', '').lower() == str(user_id).lower():
                    continue

                # Check this user's notification preferences
                if not _user_wants_notification(user, action):
                    print(f"⏭️ Skipping {user['email']} — {action} notifications disabled")
                    continue

                try:
                    first_name = user.get('first_name', 'there')
                    html = f"""
                    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:2rem;">
                        <div style="text-align:center;margin-bottom:1.5rem;">
                            <h1 style="color:#388e3c;margin:0;">🐴 Retirement Home for Horses</h1>
                            <p style="color:#546e7a;font-size:0.9rem;">Change Notification</p>
                        </div>
                        <p style="color:#333;font-size:1rem;">Hi {first_name},</p>
                        <div style="background:#f5faf6;border:2px solid #81c784;border-radius:12px;padding:1.5rem;">
                            <h2 style="color:#388e3c;margin-top:0;font-size:1.2rem;">{label}</h2>
                            <p style="color:#555;font-size:0.9rem;margin:0.3rem 0;">
                                <strong>By:</strong> {user_id}<br>
                                <strong>Time:</strong> {timestamp}
                            </p>
                            {changes_html}
                        </div>
                        <div style="margin-top:1.5rem;text-align:center;">
                            <a href="{FRONTEND_URL}/audit_trail.html" 
                               style="background:linear-gradient(135deg,#388e3c,#00796b);color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:bold;font-size:0.9rem;display:inline-block;">
                                View Full Audit Trail
                            </a>
                        </div>
                        <hr style="border:none;border-top:1px solid #eee;margin:2rem 0;">
                        <p style="color:#bbb;font-size:0.75rem;text-align:center;">
                            You can change your notification preferences in your 
                            <a href="{FRONTEND_URL}/user_profile_page.html" style="color:#79AED4;">profile settings</a>.<br>
                            Retirement Home for Horses, Inc. — Alachua, FL
                        </p>
                    </div>
                    """

                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = f'{label} — Retirement Home for Horses'
                    msg['From'] = SMTP_EMAIL
                    msg['To'] = user['email']
                    msg.attach(MIMEText(html, 'html'))

                    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
                        server.sendmail(SMTP_EMAIL, user['email'], msg.as_string())
                    print(f"📧 Notification sent to {user['email']} for {action}")
                except Exception as e:
                    print(f"❌ Failed to notify {user['email']}: {e}")

        except Exception as e:
            print(f"❌ Notification system error: {e}")

    # Run in background thread so the API response isn't delayed
    threading.Thread(target=_send, daemon=True).start()


# --- SERVE FRONTEND ---
@app.route('/')
def serve_home():
    return send_from_directory(app.static_folder, 'home_page.html')

@app.route('/<path:path>')
def serve_frontend(path):
    # Only serve if the file actually exists in the frontend folder
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    # Otherwise return 404
    return jsonify({"error": "Not found"}), 404


# ==========================================
#      SECTION 1: USER AUTHENTICATION
# ==========================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')

        if not email or not password or not first_name or not last_name:
            return jsonify({'error': 'All fields are required.'}), 400

        if user_logins.find_one({'email': email}):
            return jsonify({'error': 'This email is already registered.'}), 409

        new_user = {
            'email': email,
            'password': generate_password_hash(password),
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role': data.get('role', 'user'),
            'is_active': True,
            'email_verified': False,
            'verification_token': secrets.token_urlsafe(32),
            'created_at': datetime.utcnow(),
            'last_login': None
        }

        user_logins.insert_one(new_user)

        # Send verification email
        try:
            send_verification_email(email, first_name, new_user['verification_token'])
        except Exception as e:
            print("❌ Email send failed:", e)


        # Log to audit trail
        audit_collection.insert_one({
            'action': 'REGISTER',
            'table': 'User_Logins',
            'user_id': email,
            'details': {'email': email, 'name': first_name + ' ' + last_name},
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Account created! Check your email to verify.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required.'}), 400

        user = user_logins.find_one({'email': email})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Incorrect email or password.'}), 401

        # Check email verification
        if not user.get('email_verified', False):
            return jsonify({'error': 'Please verify your email before logging in. Check your inbox.'}), 403
            
        user_logins.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )

        # Log to audit trail
        audit_collection.insert_one({
            'action': 'LOGIN',
            'table': 'User_Logins',
            'user_id': email,
            'details': {'email': email, 'name': user['first_name'] + ' ' + user['last_name']},
            'timestamp': datetime.utcnow()
        })

        return jsonify({
            'message': 'Login successful',
            'user': {
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'email': user['email'], 
                'role': user['role']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/verify', methods=['POST'])
def verify_email():
    try:
        data = request.json
        token = data.get('token')
        if not token:
            return jsonify({'error': 'Verification token is required.'}), 400

        user = user_logins.find_one({'verification_token': token})
        if not user:
            return jsonify({'error': 'Invalid or expired verification link.'}), 404

        if user.get('email_verified'):
            return jsonify({'message': 'Email already verified! You can log in.'}), 200

        user_logins.update_one(
            {'_id': user['_id']},
            {'$set': {'email_verified': True}, '$unset': {'verification_token': ''}}
        )

        return jsonify({'message': 'Email verified successfully! You can now log in.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/resend-verification', methods=['POST'])
def resend_verification():
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required.'}), 400

        user = user_logins.find_one({'email': email})
        if not user:
            return jsonify({'error': 'No account found with this email.'}), 404

        if user.get('email_verified'):
            return jsonify({'message': 'Email is already verified.'}), 200

        new_token = secrets.token_urlsafe(32)
        user_logins.update_one(
            {'_id': user['_id']},
            {'$set': {'verification_token': new_token}}
        )

        send_verification_email(email, user.get('first_name', 'User'), new_token)
        return jsonify({'message': 'Verification email resent! Check your inbox.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/request-password-reset', methods=['POST'])
def request_password_reset():
    """Generate a reset token, store it, and email a reset link."""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        if not email:
            return jsonify({'error': 'Email is required.'}), 400

        user = user_logins.find_one({'email': email})
        if not user:
            # Don't reveal whether the email exists (security best practice)
            return jsonify({'message': 'If that email is registered, a reset link has been sent.'}), 200

        reset_token = secrets.token_urlsafe(32)
        user_logins.update_one(
            {'_id': user['_id']},
            {'$set': {
                'reset_token': reset_token,
                'reset_token_created': datetime.utcnow()
            }}
        )

        # Send the reset email
        reset_url = f"{FRONTEND_URL}/reset_password.html?token={reset_token}"
        first_name = user.get('first_name', 'there')

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Reset your password — Retirement Home for Horses'
        msg['From'] = SMTP_EMAIL
        msg['To'] = email

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:2rem;">
            <div style="text-align:center;margin-bottom:1.5rem;">
                <h1 style="color:#388e3c;margin:0;">🐴 Retirement Home for Horses</h1>
            </div>
            <h2 style="color:#333;">Hi {first_name},</h2>
            <p style="color:#555;font-size:1rem;line-height:1.6;">
                We received a request to reset your password. Click the button below to choose a new one:
            </p>
            <div style="text-align:center;margin:2rem 0;">
                <a href="{reset_url}" style="background:linear-gradient(135deg,#9CD479,#79AED4);color:#fff;text-decoration:none;padding:14px 36px;border-radius:10px;font-weight:bold;font-size:1rem;display:inline-block;">Reset My Password</a>
            </div>
            <p style="color:#999;font-size:0.85rem;text-align:center;">
                This link expires in 1 hour. If you didn't request this, you can safely ignore this email.<br>
                <a href="{reset_url}" style="color:#79AED4;">{reset_url}</a>
            </p>
            <hr style="border:none;border-top:1px solid #eee;margin:2rem 0;">
            <p style="color:#bbb;font-size:0.75rem;text-align:center;">Retirement Home for Horses, Inc. — Alachua, FL</p>
        </div>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())

        print(f"📧 Password reset email sent to {email}")
        return jsonify({'message': 'If that email is registered, a reset link has been sent.'}), 200
    except Exception as e:
        print(f"❌ Password reset request error: {e}")
        return jsonify({'error': 'Unable to send reset email. Please try again later.'}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Verify the reset token and set a new password."""
    try:
        data = request.json
        token = data.get('token')
        new_password = data.get('new_password')

        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required.'}), 400

        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters.'}), 400

        user = user_logins.find_one({'reset_token': token})
        if not user:
            return jsonify({'error': 'Invalid or expired reset link.'}), 404

        # Check if token is expired (1 hour)
        token_created = user.get('reset_token_created')
        if token_created:
            elapsed = (datetime.utcnow() - token_created).total_seconds()
            if elapsed > 3600:
                return jsonify({'error': 'This reset link has expired. Please request a new one.'}), 410

        # Update password and remove the reset token
        user_logins.update_one(
            {'_id': user['_id']},
            {
                '$set': {'password': generate_password_hash(new_password)},
                '$unset': {'reset_token': '', 'reset_token_created': ''}
            }
        )

        print(f"✅ Password reset successful for {user.get('email')}")
        return jsonify({'message': 'Password reset successful! You can now log in.'}), 200
    except Exception as e:
        print(f"❌ Password reset error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    try:
        email = request.args.get('email')
        if not email: return jsonify({'error': 'Email is required'}), 400

        user = user_logins.find_one({'email': email})
        if not user: return jsonify({'error': 'User not found'}), 404

        user_profile = {
            'first_name': user.get('first_name', ''),
            'last_name': user.get('last_name', ''),
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'role': user.get('role', 'user'),
            'is_active': user.get('is_active', False),
            'created_at': user.get('created_at', '')
        }
        return jsonify(user_profile), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = user_logins.find_one({'email': email})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        update_fields = {}
        if 'first_name' in data: update_fields['first_name'] = data['first_name']
        if 'last_name' in data: update_fields['last_name'] = data['last_name']
        if 'phone' in data: update_fields['phone'] = data['phone']

        if update_fields:
            user_logins.update_one({'email': email}, {'$set': update_fields})

        # Audit log
        audit_collection.insert_one({
            'action': 'UPDATE_PROFILE',
            'table': 'User_Logins',
            'user_id': email,
            'details': update_fields,
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/change-password', methods=['PUT'])
def change_password():
    try:
        data = request.json
        email = data.get('email')
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not email or not current_password or not new_password:
            return jsonify({'error': 'All fields are required.'}), 400

        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters.'}), 400

        user = user_logins.find_one({'email': email})
        if not user:
            return jsonify({'error': 'User not found.'}), 404

        if not check_password_hash(user['password'], current_password):
            return jsonify({'error': 'Current password is incorrect.'}), 401

        new_hash = generate_password_hash(new_password)
        user_logins.update_one(
            {'email': email},
            {'$set': {'password': new_hash}}
        )

        # Audit log
        audit_collection.insert_one({
            'action': 'CHANGE_PASSWORD',
            'table': 'User_Logins',
            'user_id': email,
            'details': {'email': email},
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Password changed successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- NOTIFICATION PREFERENCES ---

@app.route('/api/user/notification-prefs', methods=['GET'])
def get_notification_prefs():
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = user_logins.find_one({'email': email}, {'notification_prefs': 1})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Default prefs: todo=on, obs=on, horse=off, security=on
        defaults = {'todo': True, 'obs': True, 'horse': False, 'security': True}
        prefs = user.get('notification_prefs', defaults)
        return jsonify(prefs), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/notification-prefs', methods=['PUT'])
def update_notification_prefs():
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        prefs = {
            'todo': bool(data.get('todo', True)),
            'obs': bool(data.get('obs', True)),
            'horse': bool(data.get('horse', False)),
            'security': bool(data.get('security', True)),
        }

        result = user_logins.update_one(
            {'email': email},
            {'$set': {'notification_prefs': prefs}}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'Notification preferences saved'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
#      SECTION 2: HORSE MANAGEMENT
# ==========================================

@app.route('/horses', methods=['GET'])
def get_horses():
    try:
        # Sort by lowercase 'name' (primary schema) then fallback 'Name'
        cursor = horse_collection.find().sort("name", 1)
        horses = [format_doc(doc) for doc in cursor]
        return jsonify(horses), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/horses', methods=['POST'])
def add_horse():
    try:
        data = request.json
        print(f"📥 POST /horses received: {list(data.keys()) if data else 'NO DATA'}")
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        if not data.get('Name') and not data.get('name'):
            return jsonify({'error': 'Horse name is required'}), 400

        # Extract user_email before inserting (not horse data)
        user_email = data.pop('user_email', 'Unknown')
        
        # Normalize: if data has capitalized keys (old format), convert to lowercase schema
        if 'Name' in data and 'name' not in data:
            data['name'] = data.pop('Name')
        if 'Breed' in data and 'breed' not in data:
            data['breed'] = data.pop('Breed')
        if 'Gender' in data and 'gender' not in data:
            data['gender'] = data.pop('Gender')
        if 'Field Home' in data and 'pasture' not in data:
            data['pasture'] = data.pop('Field Home')
        if 'Notes' in data and 'general_notes' not in data:
            data['general_notes'] = data.pop('Notes')
        if 'Date of Birth' in data:
            data.pop('Date of Birth')  # birth_year is used instead
        
        horse_name = data.get('name') or data.get('Name') or 'Unknown'

        result = horse_collection.insert_one(data)
        print(f"✅ Horse '{horse_name}' inserted with _id: {result.inserted_id}")

        # Log to audit trail
        audit_details = {'horse_name': horse_name}
        audit_collection.insert_one({
            'action': 'ADD_HORSE',
            'table': 'Horse_Tables',
            'user_id': user_email,
            'details': audit_details,
            'timestamp': datetime.utcnow()
        })

        # Notify admins by email
        send_change_notification('ADD_HORSE', user_email, audit_details)

        return jsonify({'message': 'Horse added', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        print(f"❌ Error adding horse: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/horses/<id>', methods=['PUT'])
def update_horse(id):
    try:
        data = request.json
        user_email = data.pop('user_email', 'Unknown')

        # Get old document to compare changes
        old_doc = horse_collection.find_one({'_id': ObjectId(id)})
        if not old_doc:
            return jsonify({'error': 'Horse not found'}), 404

        horse_name = data.get('Name') or data.get('name') or old_doc.get('name') or old_doc.get('Name') or 'Unknown'

        # Build a list of actual changes (old → new)
        changes = []
        for key, new_val in data.items():
            if key in ('Name', '_id'):
                continue
            old_val = old_doc.get(key, '')
            # Normalize both to strings for comparison
            old_str = str(old_val).strip() if old_val else '—'
            new_str = str(new_val).strip() if new_val else '—'
            if old_str != new_str:
                changes.append({
                    'field': key,
                    'old': old_str,
                    'new': new_str
                })

        # Only update if something actually changed
        if not changes:
            return jsonify({'message': 'No changes detected'}), 200

        result = horse_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': data}
        )

        # Log to audit trail with detailed changes
        audit_details = {'horse_name': horse_name, 'changes': changes}
        audit_collection.insert_one({
            'action': 'UPDATE_HORSE',
            'table': 'Horse_Tables',
            'user_id': user_email,
            'details': audit_details,
            'timestamp': datetime.utcnow()
        })

        # Notify admins by email
        send_change_notification('UPDATE_HORSE', user_email, audit_details)

        return jsonify({'message': 'Horse updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/horses/<id>', methods=['DELETE'])
def delete_horse(id):
    try:
        user_email = request.args.get('user_email', 'Unknown')

        # Get horse name before deleting
        horse = horse_collection.find_one({'_id': ObjectId(id)})
        horse_name = 'Unknown'
        if horse:
            horse_name = horse.get('Name') or horse.get('name') or 'Unknown'

        result = horse_collection.delete_one({'_id': ObjectId(id)})

        if result.deleted_count == 0:
            return jsonify({'error': 'Horse not found'}), 404

        # Log to audit trail
        audit_details = {'horse_name': horse_name}
        audit_collection.insert_one({
            'action': 'DELETE_HORSE',
            'table': 'Horse_Tables',
            'user_id': user_email,
            'details': audit_details,
            'timestamp': datetime.utcnow()
        })

        # Notify admins by email
        send_change_notification('DELETE_HORSE', user_email, audit_details)

        return jsonify({'message': 'Horse deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
#      SECTION 2.6: HORSE DOCUMENTS
# ==========================================

@app.route('/api/docs/<horse_name>', methods=['GET'])
def get_horse_docs(horse_name):
    """Get all documents for a specific horse."""
    try:
        docs = list(docs_collection.find({'horse_name': horse_name}).sort('uploaded_at', -1))
        for d in docs:
            d['_id'] = str(d['_id'])
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/docs/<horse_name>', methods=['POST'])
def upload_horse_doc(horse_name):
    """Upload a document (image file as base64) for a horse."""
    try:
        data = request.json
        description = data.get('description', '').strip()
        file_data = data.get('file_data')       # base64 string
        file_name = data.get('file_name', '')
        user_email = data.get('user_email', 'Unknown')

        if not file_data:
            return jsonify({'error': 'No file data provided.'}), 400

        doc = {
            'horse_name': horse_name,
            'description': description or file_name,
            'file_name': file_name,
            'file_data': file_data,
            'uploaded_by': user_email,
            'uploaded_at': datetime.utcnow()
        }

        result = docs_collection.insert_one(doc)

        # Audit
        audit_collection.insert_one({
            'action': 'ADD_DOC',
            'table': 'Docs_Tables',
            'user_id': user_email,
            'details': f"Uploaded document '{description or file_name}' for {horse_name}",
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Document uploaded', '_id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/docs/<horse_name>/<doc_id>', methods=['DELETE'])
def delete_horse_doc(horse_name, doc_id):
    """Delete a document by its _id."""
    try:
        user_email = request.args.get('user_email', 'Unknown')
        doc = docs_collection.find_one({'_id': ObjectId(doc_id), 'horse_name': horse_name})
        if not doc:
            return jsonify({'error': 'Document not found.'}), 404

        docs_collection.delete_one({'_id': ObjectId(doc_id)})

        audit_collection.insert_one({
            'action': 'DELETE_DOC',
            'table': 'Docs_Tables',
            'user_id': user_email,
            'details': f"Deleted document '{doc.get('description', '')}' for {horse_name}",
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Document deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
#      SECTION 2.7: HORSE TREATMENTS
# ==========================================

@app.route('/api/treatments/<horse_name>', methods=['GET'])
def get_horse_treatments(horse_name):
    """Get all treatments for a specific horse."""
    try:
        treatments = list(treatment_collection.find({'horse_name': horse_name}).sort('datetime_last_updated', -1))
        for t in treatments:
            t['_id'] = str(t['_id'])
        return jsonify(treatments), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/treatments/<horse_name>', methods=['POST'])
def add_horse_treatment(horse_name):
    """Add a treatment record for a horse."""
    try:
        data = request.json
        treatment_type = data.get('treatment_type', '').strip()
        frequency = data.get('frequency', '').strip()
        user_email = data.get('user_email', 'Unknown')

        if not treatment_type:
            return jsonify({'error': 'Treatment type is required.'}), 400

        doc = {
            'horse_name': horse_name,
            'treatment_type': treatment_type,
            'frequency': frequency,
            'datetime_last_updated': datetime.utcnow(),
            'user_that_made_change': user_email
        }

        result = treatment_collection.insert_one(doc)

        audit_collection.insert_one({
            'action': 'ADD_TREATMENT',
            'table': 'Horse_Treatment_Tables',
            'user_id': user_email,
            'details': f"Added treatment '{treatment_type}' for {horse_name}",
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Treatment added', '_id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/treatments/<horse_name>/<treatment_id>', methods=['DELETE'])
def delete_horse_treatment(horse_name, treatment_id):
    """Delete a treatment record."""
    try:
        user_email = request.args.get('user_email', 'Unknown')
        rec = treatment_collection.find_one({'_id': ObjectId(treatment_id), 'horse_name': horse_name})
        if not rec:
            return jsonify({'error': 'Treatment not found.'}), 404

        treatment_collection.delete_one({'_id': ObjectId(treatment_id)})

        audit_collection.insert_one({
            'action': 'DELETE_TREATMENT',
            'table': 'Horse_Treatment_Tables',
            'user_id': user_email,
            'details': f"Deleted treatment '{rec.get('treatment_type', '')}' for {horse_name}",
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Treatment deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
#      SECTION 2.8: ACTIONS TAKEN
# ==========================================

@app.route('/api/actions/<horse_name>', methods=['GET'])
def get_horse_actions(horse_name):
    """Get all action-taken records for a specific horse."""
    try:
        actions = list(actions_collection.find({'horse_name': horse_name}).sort('datetime_last_updated', -1))
        for a in actions:
            a['_id'] = str(a['_id'])
        return jsonify(actions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/actions/<horse_name>', methods=['POST'])
def add_horse_action(horse_name):
    """Log an action taken (treatment administered) for a horse."""
    try:
        data = request.json
        treatment = data.get('treatment', '').strip()
        notes = data.get('notes', '').strip()
        user_email = data.get('user_email', 'Unknown')

        if not treatment:
            return jsonify({'error': 'Treatment is required.'}), 400

        doc = {
            'horse_name': horse_name,
            'treatment': treatment,
            'action_taken_notes': notes,
            'datetime_last_updated': datetime.utcnow(),
            'user_that_made_change': user_email
        }

        result = actions_collection.insert_one(doc)

        audit_collection.insert_one({
            'action': 'ADD_ACTION',
            'table': 'Actions_Tables',
            'user_id': user_email,
            'details': f"Logged action '{treatment}' for {horse_name}: {notes[:80] if notes else '(no notes)'}",
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Action logged', '_id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/actions/<horse_name>/<action_id>', methods=['DELETE'])
def delete_horse_action(horse_name, action_id):
    """Delete an action-taken record."""
    try:
        user_email = request.args.get('user_email', 'Unknown')
        rec = actions_collection.find_one({'_id': ObjectId(action_id), 'horse_name': horse_name})
        if not rec:
            return jsonify({'error': 'Action not found.'}), 404

        actions_collection.delete_one({'_id': ObjectId(action_id)})

        audit_collection.insert_one({
            'action': 'DELETE_ACTION',
            'table': 'Actions_Tables',
            'user_id': user_email,
            'details': f"Deleted action '{rec.get('treatment', '')}' for {horse_name}",
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Action deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
#      SECTION 2.5: AUDIT TRAIL
# ==========================================

@app.route('/api/audits', methods=['GET'])
def get_audits():
    try:
        limit = request.args.get('limit', 50, type=int)
        cursor = audit_collection.find().sort("timestamp", -1)
        if limit > 0:
            cursor = cursor.limit(limit)
        audits = [format_doc(doc) for doc in cursor]
        return jsonify(audits), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
#      SECTION 3: DAILY OBS / TO-DO (RESTORED!)
# ==========================================

@app.route('/api/daily-obs', methods=['GET'])
def get_daily_obs():
    try:
        # Sort by date descending (newest first)
        cursor = daily_obs_collection.find().sort("date", -1)
        items = [format_doc(doc) for doc in cursor]
        return jsonify(items), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-obs', methods=['POST'])
def add_daily_obs():
    try:
        data = request.json
        # Basic validation
        if not data.get('note'):
            return jsonify({'error': 'Note is required'}), 400

        # Prepare document
        new_item = {
            "note": data.get('note'),
            "is_observation": data.get('obs', False),
            "is_todo": data.get('todo', False),
            "status": data.get('status', 'pending'),
            "horse_id": data.get('horse_id', ''),
            "created_by": data.get('created_by', 'Anonymous'),
            "due_date": data.get('due_date', None),
            "date": datetime.utcnow()
        }
        
        result = daily_obs_collection.insert_one(new_item)
        return jsonify({'message': 'Item added', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-obs/<id>', methods=['DELETE'])
def delete_daily_obs(id):
    try:
        result = daily_obs_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Item not found"}), 404
        return jsonify({"message": "Item Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/daily-obs/<id>', methods=['PATCH'])
def toggle_daily_obs(id):
    try:
        data = request.json
        update_fields = {}
        for field in ['status', 'note', 'is_observation', 'is_todo', 'horse_id', 'due_date']:
            if field in data:
                update_fields[field] = data[field]
        if update_fields:
            daily_obs_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": update_fields}
            )
        return jsonify({"message": "Updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
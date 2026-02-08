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

# --- CONFIGURATION ---
app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max upload
# Allow CORS for all domains
CORS(app)

# Email Configuration (use env vars in production, fallback to local defaults)
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'luisalmeida0106@gmail.com')
SMTP_APP_PASSWORD = os.environ.get('SMTP_APP_PASSWORD', 'oqrx kaip oppt pmtt')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
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
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"✅ Verification email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

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
        audit_collection.insert_one({
            'action': 'ADD_HORSE',
            'table': 'Horse_Tables',
            'user_id': user_email,
            'details': {'horse_name': horse_name},
            'timestamp': datetime.utcnow()
        })

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
        audit_collection.insert_one({
            'action': 'UPDATE_HORSE',
            'table': 'Horse_Tables',
            'user_id': user_email,
            'details': {
                'horse_name': horse_name,
                'changes': changes
            },
            'timestamp': datetime.utcnow()
        })

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
        audit_collection.insert_one({
            'action': 'DELETE_HORSE',
            'table': 'Horse_Tables',
            'user_id': user_email,
            'details': {'horse_name': horse_name},
            'timestamp': datetime.utcnow()
        })

        return jsonify({'message': 'Horse deleted'}), 200
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
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timezone

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app)

URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"

# --- DB CONNECT ---
try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    user_logins = db["User_Logins"]
    horse_collection = db["Horse_Tables"]
    daily_obs_collection = db["DailyObs_Tables"]

    # indexes (safe)
    try:
        daily_obs_collection.create_index([("date", -1)])
        daily_obs_collection.create_index([("status", 1), ("date", -1)])
        daily_obs_collection.create_index([("horse_id", 1), ("date", -1)])
    except Exception as e:
        print(f"⚠️ Index create warning: {e}")

    print(f"✅ CONNECTED TO: {DB_NAME} (User_Logins, Horse_Tables, DailyObs_Tables)")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")


# --- HELPERS ---
def utcnow_naive() -> datetime:
    """Mongo-safe naive UTC datetime."""
    return datetime.utcnow()

def format_doc(doc):
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc

def to_bool(x):
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    if isinstance(x, str):
        return x.strip().lower() in ("y", "yes", "true", "1", "t")
    return bool(x)

def parse_iso_to_utc_naive(s: str) -> datetime:
    """
    Accepts ISO strings like:
      2026-02-08T12:34:56
      2026-02-08T12:34:56Z
      2026-02-08T12:34:56+00:00
    Returns naive UTC datetime (Mongo-safe).
    """
    s = (s or "").strip()
    if not s:
        raise ValueError("empty date string")

    # handle Z suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)

    # convert aware -> utc naive
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt

def oid_or_400(id_str: str):
    try:
        return ObjectId(id_str)
    except Exception:
        return None


# --- ROOT ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "message": "Unified Server Running"})


# --- AUTH ---
@app.route("/api/auth/register", methods=["POST"])
def register():
    try:
        data = request.json or {}
        email = data.get("email")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        phone = data.get("phone")

        if not email or not password or not first_name or not last_name:
            return jsonify({"error": "All fields are required."}), 400

        if user_logins.find_one({"email": email}):
            return jsonify({"error": "This email is already registered."}), 409

        new_user = {
            "email": email,
            "password": generate_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "role": "user",
            "is_active": True,
            "created_at": utcnow_naive(),
            "last_login": None,
        }

        result = user_logins.insert_one(new_user)
        return jsonify({"message": "Account created successfully!", "id": str(result.inserted_id)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data = request.json or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password required."}), 400

        user = user_logins.find_one({"email": email})
        if not user:
            return jsonify({"error": "Incorrect email or password."}), 401

        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Incorrect email or password."}), 401

        user_logins.update_one({"_id": user["_id"]}, {"$set": {"last_login": utcnow_naive()}})

        return jsonify(
            {
                "message": "Login successful",
                "user": {"first_name": user["first_name"], "role": user["role"], "email": user.get("email")},
            }
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- HORSES ---
@app.route("/horses", methods=["GET"])
def get_horses():
    try:
        cursor = horse_collection.find().sort("Name", 1)
        horses = [format_doc(doc) for doc in cursor]
        return jsonify(horses), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/horses", methods=["POST"])
def add_horse():
    try:
        data = request.json or {}
        if not data.get("Name"):
            return jsonify({"error": "Horse Name is required"}), 400

        data["created_at"] = utcnow_naive()
        data["active_status"] = True

        result = horse_collection.insert_one(data)
        return jsonify({"message": "Horse Added", "id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/horses/<id>", methods=["PUT"])
def update_horse(id):
    try:
        data = request.json or {}
        if "_id" in data:
            del data["_id"]
        data["last_updated"] = utcnow_naive()

        oid = oid_or_400(id)
        if oid is None:
            return jsonify({"error": "Invalid horse ObjectId"}), 400

        result = horse_collection.update_one({"_id": oid}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Horse not found"}), 404
        return jsonify({"message": "Horse Updated Successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/horses/<id>", methods=["DELETE"])
def delete_horse(id):
    try:
        oid = oid_or_400(id)
        if oid is None:
            return jsonify({"error": "Invalid horse ObjectId"}), 400

        result = horse_collection.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "Horse not found"}), 404
        return jsonify({"message": "Horse Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- DAILY OBS / TODO ---
@app.route("/api/daily-obs", methods=["POST"])
def create_daily_obs():
    try:
        data = request.json or {}

        note = (data.get("note") or "").strip()
        if not note:
            return jsonify({"error": "note is required"}), 400

        is_obs = to_bool(data.get("obs"))
        is_todo = to_bool(data.get("todo"))
        if not (is_obs or is_todo):
            return jsonify({"error": "At least one of obs or todo must be true (or 'y')."}), 400

        status = data.get("status", "pending")
        if status not in ("pending", "complete"):
            return jsonify({"error": "status must be 'pending' or 'complete'"}), 400

        date_val = data.get("date")
        if date_val:
            try:
                date_dt = parse_iso_to_utc_naive(date_val)
            except Exception:
                return jsonify({"error": "date must be ISO format (e.g. 2026-02-08T12:34:56Z)"}), 400
        else:
            date_dt = utcnow_naive()

        doc = {
            "date": date_dt,
            "is_observation": is_obs,
            "is_todo": is_todo,
            "note": note,
            "status": status,
            "horse_id": data.get("horse_id"),     # optional (can be your 4-digit horse id)
            "created_by": data.get("created_by"), # optional (email/username)
            "created_at": utcnow_naive(),
            "updated_at": None,
        }

        result = daily_obs_collection.insert_one(doc)
        return jsonify({"message": "Daily obs item created", "id": str(result.inserted_id)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/daily-obs", methods=["GET"])
def get_daily_obs():
    try:
        status = request.args.get("status")
        horse_id = request.args.get("horse_id")
        created_by = request.args.get("created_by")
        limit = int(request.args.get("limit", 50))

        q = {}
        if status:
            q["status"] = status
        if horse_id:
            q["horse_id"] = horse_id
        if created_by:
            q["created_by"] = created_by

        cursor = daily_obs_collection.find(q).sort("date", -1).limit(limit)
        items = [format_doc(d) for d in cursor]
        return jsonify(items), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/daily-obs/<id>/status", methods=["PUT"])
def update_daily_obs_status(id):
    try:
        data = request.json or {}
        status = data.get("status")

        if status not in ("pending", "complete"):
            return jsonify({"error": "status must be 'pending' or 'complete'"}), 400

        oid = oid_or_400(id)
        if oid is None:
            return jsonify({"error": "Invalid item ObjectId"}), 400

        result = daily_obs_collection.update_one(
            {"_id": oid},
            {"$set": {"status": status, "updated_at": utcnow_naive()}}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Item not found"}), 404

        return jsonify({"message": "Status updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/daily-obs/<id>", methods=["DELETE"])
def delete_daily_obs(id):
    try:
        oid = oid_or_400(id)
        if oid is None:
            return jsonify({"error": "Invalid item ObjectId"}), 400

        result = daily_obs_collection.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "Item not found"}), 404
        return jsonify({"message": "Item deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary():
    try:
        horse_count = horse_collection.count_documents({})
        pending_tasks = daily_obs_collection.count_documents({"status": "pending", "is_todo": True})
        pending_obs = daily_obs_collection.count_documents({"status": "pending", "is_observation": True})

        recent_items = list(daily_obs_collection.find({}).sort("date", -1).limit(10))
        recent_items = [format_doc(d) for d in recent_items]

        return jsonify({
            "horseCount": horse_count,
            "pendingTasks": pending_tasks,
            "pendingObservations": pending_obs,
            "recentDailyObs": recent_items
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app)  # This allows the HTML file to talk to this Python script

# Database Connection
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"
COLLECTION_NAME = "Horse_Tables"

try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    print(f"✅ SERVER CONNECTED to {DB_NAME}.{COLLECTION_NAME}")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")

# --- HELPER ---
def format_doc(doc):
    """Converts MongoDB document to JSON-friendly format"""
    if not doc: return None
    doc['_id'] = str(doc['_id']) # Convert ObjectId to string
    return doc

# --- API ROUTES ---

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Horse Backend is Running!"})

# 1. GET ALL HORSES (Read)
@app.route('/horses', methods=['GET'])
def get_horses():
    try:
        # Get all horses, sort by Name
        cursor = collection.find().sort("Name", 1)
        horses = [format_doc(doc) for doc in cursor]
        return jsonify(horses), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. ADD A NEW HORSE (Create)
@app.route('/horses', methods=['POST'])
def add_horse():
    try:
        data = request.json
        if not data.get('Name'):
            return jsonify({"error": "Horse Name is required"}), 400

        # Add metadata
        data['created_at'] = datetime.utcnow()
        data['active_status'] = True
        
        # Insert
        result = collection.insert_one(data)
        return jsonify({"message": "Horse Added", "id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. UPDATE A HORSE (Update)
@app.route('/horses/<id>', methods=['PUT'])
def update_horse(id):
    try:
        data = request.json
        # Remove _id from data if it exists (can't update _id)
        if '_id' in data: del data['_id']
        
        data['last_updated'] = datetime.utcnow()
        
        result = collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Horse not found"}), 404
            
        return jsonify({"message": "Horse Updated Successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. DELETE A HORSE (Delete)
@app.route('/horses/<id>', methods=['DELETE'])
def delete_horse(id):
    try:
        result = collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Horse not found"}), 404
        return jsonify({"message": "Horse Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- RUN SERVER ---
if __name__ == '__main__':
    # Runs on port 5000
    app.run(debug=True, port=5000)
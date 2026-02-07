import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from bson import json_util

app = Flask(__name__)
CORS(app)

# Configuration via environment variables
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.environ.get('MONGODB_DB', 'HorseSanctuary')
MONGODB_COLLECTION = os.environ.get('MONGODB_COLLECTION', 'Horse_Treatment_Tables')

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[MONGODB_DB]
collection = db[MONGODB_COLLECTION]


def parse_compound_id(compound_id: str):
    """Parse IDs of the form XXXX-XXXX-2 (or similar).

    Returns a dict with keys: full (original), horse (first segment or first 4 chars), mid (middle segment), table (last segment).
    """
    parts = compound_id.split('-')
    horse = parts[0] if parts and len(parts[0]) > 0 else ''
    if len(horse) > 4:
        horse = horse[:4]
    mid = parts[1] if len(parts) >= 3 else (parts[1] if len(parts) == 2 else '')
    table = parts[-1] if len(parts) >= 1 else ''
    return {'full': compound_id, 'horse': horse, 'mid': mid, 'table': table}


def flexible_query(parsed):
    """Build a flexible MongoDB query to match likely field names.

    The function tries a few common field names so it works with different schemas.
    """
    horse = parsed['horse']
    table = parsed['table']
    full = parsed['full']

    # Try direct id matches first
    candidates = []
    candidates.append({'id': full})
    candidates.append({'_id': full})

    # common horse id field names
    horse_fields = ['horse_id', 'HorseID', 'Horse_ID', 'horse', 'Horse']
    table_fields = ['treatment_id', 'TreatmentID', 'treatmentTableId', 'table_id', 'TableID', 'table']

    # match combinations of horse + table
    and_clauses = []
    horse_or = [{f: horse} for f in horse_fields if horse]
    table_or = [{f: table} for f in table_fields if table]
    if horse_or and table_or:
        and_clauses.append({'$and': [{'$or': horse_or}, {'$or': table_or}]})

    # if only horse known
    if horse_or:
        and_clauses.append({'$or': horse_or})

    # if only table known
    if table_or:
        and_clauses.append({'$or': table_or})

    # Build final $or combining simple candidates and the and_clauses
    query_or = candidates + and_clauses

    if len(query_or) == 1:
        return query_or[0]
    return {'$or': query_or}


@app.route('/api/treatment', methods=['GET'])
def get_treatment():
    """Endpoint to retrieve treatment records by compound id.

    Accepts `id` as a query parameter or path segment.
    Example: /api/treatment?id=1234-5678-2
    """
    id_param = request.args.get('id')
    if not id_param:
        return jsonify({'error': 'missing id parameter'}), 400

    parsed = parse_compound_id(id_param)

    # Test DB connection early
    try:
        client.server_info()
    except ServerSelectionTimeoutError:
        return jsonify({'error': 'cannot connect to MongoDB. Check MONGODB_URI'}), 500

    query = flexible_query(parsed)

    try:
        cursor = collection.find(query).limit(100)
        docs = list(cursor)
        # Use bson.json_util to serialize ObjectId and other BSON types
        json_docs = json_util.dumps(docs)
        return app.response_class(response=json_docs, status=200, mimetype='application/json')
    except Exception as e:
        return jsonify({'error': 'query failed', 'details': str(e), 'query': query}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

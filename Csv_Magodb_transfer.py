import os
import csv
import sys
import ssl
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# --- CONFIGURATION ---
uri = os.environ.get(
    'MONGODB_URI',
    'mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary'
)

TEST_ALLOW_INVALID_TLS = os.environ.get('TEST_ALLOW_INVALID_TLS', '0') == '1'

client_kwargs = {'server_api': ServerApi('1')}
if TEST_ALLOW_INVALID_TLS:
    client_kwargs.update({'tls': True, 'tlsAllowInvalidCertificates': True, 'ssl_cert_reqs': ssl.CERT_NONE})

try:
    client = MongoClient(uri, **client_kwargs)
    client.admin.command('ping')
except Exception as e:
    print('ERROR: Cannot connect to MongoDB server:', file=sys.stderr)
    print(repr(e), file=sys.stderr)
    sys.exit(1)

db = client.get_database(os.environ.get('MONGODB_DB', 'Data'))
collection = db.get_collection(os.environ.get('MONGODB_HORSE_COLLECTION', 'Horse_Tables'))

# --- HELPER FUNCTIONS ---
def parse_date(date_str):
    """Parse date string in multiple formats."""
    if not date_str or str(date_str).strip() == '':
        return None
    
    date_str = str(date_str).strip()
    formats = ["%m/%d/%Y", "%m/%Y", "%Y-%m-%d"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def parse_boolean(value):
    """Convert string to boolean (Y/N or True/False)."""
    if not value:
        return None
    val_str = str(value).strip().upper()
    return val_str in ['Y', 'YES', 'TRUE', '1']

def clean_string(value):
    """Return stripped string or None."""
    if not value:
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None

def calculate_birth_year(age_str):
    """Calculate birth year from age in 2026."""
    if not age_str:
        return None
    try:
        digits = ''.join(ch for ch in str(age_str) if ch.isdigit())
        if digits:
            age = int(digits)
            return 2026 - age
    except Exception:
        pass
    return None

documents = []

csv_path = os.environ.get('HORSE_CSV_PATH', 'Horse_Table.csv')
if not os.path.exists(csv_path):
    print('ERROR: CSV file not found at', csv_path, file=sys.stderr)
    sys.exit(1)

with open(csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Basic normalization: strip whitespace from keys and values
        norm = {k.strip(): (v.strip() if v is not None else '') for k, v in row.items()}

        # --- BUILD COMPREHENSIVE HORSE DOCUMENT ---
        horse_doc = {
            # Section 1: Basic Information
            "name": clean_string(norm.get('Name')),
            "birth_year": calculate_birth_year(norm.get('Age (in 2026)')),
            "picture_url": clean_string(norm.get('Picture')),
            "biography_url": clean_string(norm.get('Biography')),
            "arrival_date": parse_date(norm.get('Arrival Date')),
            "breed": clean_string(norm.get('Breed')),
            "gender": clean_string(norm.get('Gender')),
            
            # Section 1: Eye Conditions
            "left_eye": clean_string(norm.get('Left Eye')),
            "right_eye": clean_string(norm.get('Right Eye')),
            
            # Section 2: Medical Conditions (Red/Medical attributes)
            "heart_murmur": parse_boolean(norm.get('Heart Murmur')),
            "cushings_positive": parse_boolean(norm.get('Cushings Positive')),
            "heaves": parse_boolean(norm.get('Heaves')),
            "anhidrosis": parse_boolean(norm.get('Anhidrosis')),
            "shivers": parse_boolean(norm.get('Shivers')),
            
            # Section 2: Behavior Attributes (Light Blue)
            "bites": parse_boolean(norm.get('Bites')),
            "kicks": parse_boolean(norm.get('Kicks')),
            "difficult_to_catch": parse_boolean(norm.get('Difficult to catch')),
            "problem_with_needles": parse_boolean(norm.get('Problem w/ needles')),
            "problem_with_farrier": parse_boolean(norm.get('Problem w/ farrier')),
            "sedation_for_farrier": parse_boolean(norm.get('Sedation for Farrier')),
            
            # Section 2: Feeding Attributes (Orange)
            "requires_extra_feed": parse_boolean(norm.get('Requires extra feed')),
            "requires_extra_mash": parse_boolean(norm.get('Requires extra mash')),
            
            # Section 3: Care & Status
            "seen_by_vet": parse_boolean(norm.get('Seen by Vet')),
            "seen_by_farrier": parse_boolean(norm.get('Seen by Farrier')),
            "military_police_horse": parse_boolean(norm.get('Military/Police Horse')),
            "ex_race_horse": parse_boolean(norm.get('ExRaceHorse')),
            
            # Section 3: Deceased Status
            "is_deceased": parse_boolean(norm.get('Deceased')),
            "date_of_death": parse_date(norm.get('Date of death')),
            
            # Section 3: Care Schedule & Notes
            "grooming_days": clean_string(norm.get('Grooming Day')),
            "pasture": clean_string(norm.get('Pasture')),
            "behavior_notes": clean_string(norm.get('Behavior Notes')),
            "regular_treatment": parse_boolean(norm.get('Regular Treatment')),
            "medical_notes": clean_string(norm.get('Medical Notes')),
            
            # Metadata
            "datetime_last_updated": datetime.utcnow(),
            "last_updated_by": None  # Will be set by app interface
        }
        
        documents.append(horse_doc)


if not documents:
    print('No documents found in CSV; nothing to insert.')
    sys.exit(0)

from pymongo import UpdateOne

# Prepare bulk upsert operations using Name as the unique key to avoid duplicates
ops = []
for doc in documents:
    name = doc.get('name')
    if not name:
        continue
    filter_doc = {'name': name}
    update_doc = {'$set': doc}
    ops.append(UpdateOne(filter_doc, update_doc, upsert=True))

if not ops:
    print('No upsert operations to perform (no named rows).')
    sys.exit(0)

try:
    result = collection.bulk_write(ops, ordered=False)
    upserted = result.upserted_count
    modified = result.modified_count
    print(f'✅ Bulk upsert completed. Upserted: {upserted}, Modified: {modified} into {collection.full_name}')
    print(f'📊 Horse Table schema updated with full attribute structure')
except Exception as e:
    print('ERROR: bulk_write failed:', file=sys.stderr)
    print(repr(e), file=sys.stderr)
    sys.exit(1)

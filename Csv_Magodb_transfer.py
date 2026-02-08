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
    """Calculate birth year from pure numeric age. If not pure number, return None."""
    if not age_str:
        return None
    age_str = str(age_str).strip()
    try:
        # Only convert if it's a pure number
        age = int(age_str)
        return 2026 - age
    except ValueError:
        # If not pure number (e.g., "29+"), return None
        return None

def parse_medical_conditions(med_conditions_str):
    """
    Parse medical conditions string and return dict of condition flags.
    Checks for condition keywords case-insensitively.
    Default all to False, set True if found in text.
    """
    conditions = {
        "heart_murmur": False,
        "cushings_positive": False,
        "heaves": False,
        "anhidrosis": False,
        "shivers": False,
        "bites": False,
        "kicks": False,
        "difficult_to_catch": False,
        "problem_with_needles": False,
        "problem_with_farrier": False,
        "sedation_for_farrier": False,
        "requires_extra_feed": False,
        "requires_extra_mash": False,
    }
    
    if not med_conditions_str:
        return conditions
    
    med_text = str(med_conditions_str).lower()
    
    # Check each condition keyword
    if "heart murmur" in med_text:
        conditions["heart_murmur"] = True
    if "cushing" in med_text:  # Catches "Cushing's", "Cushings", etc.
        conditions["cushings_positive"] = True
    if "heaves" in med_text:
        conditions["heaves"] = True
    if "anhidrosis" in med_text:
        conditions["anhidrosis"] = True
    if "shivers" in med_text:
        conditions["shivers"] = True
    if "bites" in med_text:
        conditions["bites"] = True
    if "kicks" in med_text:
        conditions["kicks"] = True
    if "difficult to catch" in med_text or "difficult_to_catch" in med_text:
        conditions["difficult_to_catch"] = True
    if "problem" in med_text and "needle" in med_text:
        conditions["problem_with_needles"] = True
    if "problem" in med_text and "farrier" in med_text:
        conditions["problem_with_farrier"] = True
    if "sedation" in med_text:
        conditions["sedation_for_farrier"] = True
    if "extra feed" in med_text or "extra-feed" in med_text:
        conditions["requires_extra_feed"] = True
    if "extra mash" in med_text or "extra-mash" in med_text:
        conditions["requires_extra_mash"] = True
    
    return conditions

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
        # Parse medical conditions to get all condition flags
        med_conditions_parsed = parse_medical_conditions(norm.get('Medical Conditions'))
        
        # Handle age: convert pure numbers to birth year, set to None if non-numeric
        age_str = clean_string(norm.get('Age (in 2026)'))
        birth_year = calculate_birth_year(age_str) if age_str else None
        
        # Handle Field of Dreams: if there's a date, horse is deceased
        field_of_dreams_date = parse_date(norm.get('Field of Dreams'))
        is_deceased = field_of_dreams_date is not None
        
        horse_doc = {
            # Section 1: Basic Information
            "name": clean_string(norm.get('Name')),
            "birth_year": birth_year,
            "picture_url": clean_string(norm.get('Picture')),
            "biography_url": clean_string(norm.get('Biography')),
            "arrival_date": parse_date(norm.get('RHH Arrival')),
            "breed": clean_string(norm.get('Breed')),
            "gender": clean_string(norm.get('Gender')),
            "pasture": clean_string(norm.get('Field Home')),
            
            # Eye Conditions (if in separate columns, add them, otherwise leave as None)
            "left_eye": clean_string(norm.get('Left Eye')),
            "right_eye": clean_string(norm.get('Right Eye')),
            
            # Section 2: Medical Conditions (parsed from Medical Conditions field)
            "heart_murmur": med_conditions_parsed["heart_murmur"],
            "cushings_positive": med_conditions_parsed["cushings_positive"],
            "heaves": med_conditions_parsed["heaves"],
            "anhidrosis": med_conditions_parsed["anhidrosis"],
            "shivers": med_conditions_parsed["shivers"],
            
            # Section 2: Behavior Attributes
            "bites": med_conditions_parsed["bites"],
            "kicks": med_conditions_parsed["kicks"],
            "difficult_to_catch": med_conditions_parsed["difficult_to_catch"],
            "problem_with_needles": med_conditions_parsed["problem_with_needles"],
            "problem_with_farrier": med_conditions_parsed["problem_with_farrier"],
            "sedation_for_farrier": med_conditions_parsed["sedation_for_farrier"],
            
            # Section 2: Feeding Attributes
            "requires_extra_feed": med_conditions_parsed["requires_extra_feed"],
            "requires_extra_mash": med_conditions_parsed["requires_extra_mash"],
            
            # Section 3: Care & Status
            "seen_by_vet": parse_boolean(norm.get('Seen by Vet')),
            "seen_by_farrier": parse_boolean(norm.get('Seen by Farrier')),
            "military_police_horse": parse_boolean(norm.get('Military/Police Horse')),
            "ex_race_horse": parse_boolean(norm.get('ExRaceHorse')),
            
            # Section 3: Deceased Status
            "is_deceased": is_deceased,
            "date_of_death": field_of_dreams_date,  # From Field of Dreams column
            
            # Section 3: Care Schedule & Notes
            "grooming_days": clean_string(norm.get('Grooming Day')),
            "last_farrier_date": parse_date(norm.get('Last Farrier Date')),
            "farrier_notes": clean_string(norm.get('Farrier notes')),
            "behavior_notes": clean_string(norm.get('Behavior Notes')),
            "regular_treatment": parse_boolean(norm.get('Regular Treatment')),
            "medical_notes": clean_string(norm.get('Medical Notes')),
            "general_notes": clean_string(norm.get('Notes')),
            
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

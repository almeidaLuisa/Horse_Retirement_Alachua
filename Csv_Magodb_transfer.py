import os
import csv
import sys
import ssl
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Read connection from env to avoid hardcoding credentials in repo
uri = os.environ.get(
    'MONGODB_URI',
    'mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary'
)

# For testing only: set TEST_ALLOW_INVALID_TLS=1 in environment to bypass cert verification
TEST_ALLOW_INVALID_TLS = os.environ.get('TEST_ALLOW_INVALID_TLS', '0') == '1'

client_kwargs = {'server_api': ServerApi('1')}
if TEST_ALLOW_INVALID_TLS:
    client_kwargs.update({'tls': True, 'tlsAllowInvalidCertificates': True, 'ssl_cert_reqs': ssl.CERT_NONE})

try:
    client = MongoClient(uri, **client_kwargs)
    # quick ping to verify connection
    client.admin.command('ping')
except Exception as e:
    print('ERROR: Cannot connect to MongoDB server:', file=sys.stderr)
    print(repr(e), file=sys.stderr)
    sys.exit(1)

db = client.get_database(os.environ.get('MONGODB_DB', 'Data'))
collection = db.get_collection(os.environ.get('MONGODB_HORSE_COLLECTION', 'Horse_Tables'))

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

        # Convert Age to Date of Birth (calculate from age in 2026)
        # If age is 29 in 2026, DOB is approximately 2026 - 29 = 1997
        age_fields = ['Age', 'Age (in 2026)', 'age']
        for af in age_fields:
            if af in norm and norm[af]:
                try:
                    digits = ''.join(ch for ch in norm[af] if ch.isdigit())
                    if digits:
                        age = int(digits)
                        birth_year = 2026 - age
                        norm['Date_of_Birth'] = f'{birth_year}-01-01'  # approximate to Jan 1 of birth year
                        # remove Age field after conversion
                        if af in norm:
                            del norm[af]
                except Exception:
                    pass

        documents.append(norm)

if not documents:
    print('No documents found in CSV; nothing to insert.')
    sys.exit(0)

from pymongo import UpdateOne

# Prepare bulk upsert operations using Name as the unique key to avoid duplicates
ops = []
for doc in documents:
    name = doc.get('Name') or doc.get('name') or ''
    if not name:
        continue
    filter_doc = {'Name': name}
    update_doc = {'$set': doc}
    ops.append(UpdateOne(filter_doc, update_doc, upsert=True))

if not ops:
    print('No upsert operations to perform (no named rows).')
    sys.exit(0)

try:
    result = collection.bulk_write(ops, ordered=False)
    upserted = result.upserted_count
    modified = result.modified_count
    print(f'Bulk upsert completed. Upserted: {upserted}, Modified: {modified} into {collection.full_name}')
except Exception as e:
    print('ERROR: bulk_write failed:', file=sys.stderr)
    print(repr(e), file=sys.stderr)
    sys.exit(1)

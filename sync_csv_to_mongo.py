import os
import csv
import sys
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ServerSelectionTimeoutError

CSV_PATH = os.environ.get('HORSE_CSV_PATH', 'Horse_Table.csv')
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.environ.get('MONGODB_DB', 'HorseSanctuary')
MONGODB_COLLECTION = os.environ.get('MONGODB_HORSE_COLLECTION', 'Horse_Table')


def normalize_key(k: str) -> str:
    return k.strip()


def load_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [ {normalize_key(k): (v.strip() if v is not None else '') for k,v in row.items()} for row in reader ]
    return rows


def connect(uri):
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.server_info()
    except ServerSelectionTimeoutError:
        print('ERROR: Cannot connect to MongoDB at', uri)
        sys.exit(1)
    return client


def prepare_bulk_ops(rows):
    ops = []
    for r in rows:
        # Use Name as unique key for upsert. If you have another unique id, change the filter.
        name = r.get('Name') or r.get('name') or ''
        if not name:
            # skip nameless rows
            continue
        filter_doc = {'Name': name}
        update_doc = {'$set': r}
        ops.append(UpdateOne(filter_doc, update_doc, upsert=True))
    return ops


def main():
    print('Loading CSV:', CSV_PATH)
    rows = load_csv(CSV_PATH)
    print('Rows to process:', len(rows))

    client = connect(MONGODB_URI)
    db = client[MONGODB_DB]
    coll = db[MONGODB_COLLECTION]

    ops = prepare_bulk_ops(rows)
    if not ops:
        print('No operations to perform (no named rows).')
        return

    print('Executing bulk write of', len(ops), 'operations...')
    result = coll.bulk_write(ops, ordered=False)
    print('Bulk write completed.')
    print('Inserted:', result.upserted_count, 'Modified:', result.modified_count)


if __name__ == '__main__':
    main()

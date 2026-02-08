# Hola muchachos

import pandas as pd
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import math

# --- CONFIGURATION ---
# 1. DATABASE CONNECTION
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Alejandro's_Labor_Camp"  # The specific database we are creating

# 2. FILE CONFIGURATION
CSV_FILE = 'Horse_Table.csv'

# --- HELPER FUNCTIONS ---
def parse_date(date_str):
    """
    Tries to convert a string (MM/DD/YYYY) to a MongoDB DateTime object.
    Returns None if the date is invalid or empty.
    """
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None
    
    # Handle the "00/2024" weird format seen in your CSV by defaulting to Jan 1st
    if "00/" in str(date_str):
        date_str = str(date_str).replace("00/", "01/")
        
    try:
        # Try standard US format: Month/Day/Year
        return datetime.strptime(str(date_str).strip(), "%m/%d/%Y")
    except ValueError:
        # Try Month/Year format (e.g., "02/2022")
        try:
             return datetime.strptime(str(date_str).strip(), "%m/%Y")
        except ValueError:
            return None

def clean_string(value):
    """Returns a stripped string or None if it's NaN."""
    if pd.isna(value) or value == "":
        return None
    return str(value).strip()

def main():
    print("🚀 Starting Data Migration...")

    # 1. Connect to MongoDB
    try:
        client = MongoClient(URI, server_api=ServerApi('1'))
        db = client[DB_NAME]
        print(f"✅ Connected to Database: {DB_NAME}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    # 2. Read the CSV
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"jw Loaded CSV with {len(df)} rows.")
    except FileNotFoundError:
        print("❌ CSV file not found. Make sure 'Horse_Table.csv' is in the same folder.")
        return

    # 3. Clear existing data (OPTIONAL - safer for testing)
    # Uncomment these lines if you want to wipe the DB clean every time you run this script
    # print("🧹 Clearing old data...")
    # db.horses.delete_many({})
    # db.treatments.delete_many({})

    horses_inserted = 0
    treatments_inserted = 0

    # 4. Iterate through rows and build documents
    for index, row in df.iterrows():
        
        # --- BUILD HORSE DOCUMENT ---
        # Logic: "Field of Dreams" having a date means the horse is deceased.
        deceased_date = parse_date(row.get('Field of Dreams'))
        is_deceased = deceased_date is not None

        horse_doc = {
            "name": clean_string(row.get('Name')),
            "breed": clean_string(row.get('Breed')),
            "gender": clean_string(row.get('Gender')),
            "location": clean_string(row.get('Field Home')), # Maps to 'pasture' in specs
            "age_text": clean_string(row.get('Age (in 2026)')), # Keeping as text to handle "29+"
            "medical_conditions": clean_string(row.get('Medical Conditions')), # Can split by comma later if needed
            "arrival_date": parse_date(row.get('RHH Arrival')),
            "is_deceased": is_deceased,
            "deceased_date": deceased_date,
            "last_farrier_date": parse_date(row.get('Last Farrier Date')),
            "farrier_notes": clean_string(row.get('Farrier notes')),
            "general_notes": clean_string(row.get('Notes')),
            # Initialize empty lists for future app features
            "profile_picture": None, 
            "documents": []
        }

        # INSERT HORSE to get its unique MongoDB _id
        result = db.horses.insert_one(horse_doc)
        new_horse_id = result.inserted_id
        horses_inserted += 1

        # --- BUILD TREATMENT DOCUMENT (If it exists) ---
        treatment_desc = clean_string(row.get('Treatment Description'))
        treatment_date = parse_date(row.get('Treatment Date'))

        if treatment_desc:
            treatment_doc = {
                "horse_id": new_horse_id,  # LINKING KEY: This connects Treatment -> Horse
                "horse_name": horse_doc['name'], # Redundant but useful for quick reads/debugging
                "description": treatment_desc,
                "date_administered": treatment_date,
                "type": "General", # Default type, can be updated by Editors later
                "frequency": "One-time" # Default, logic needed if it's recurring
            }
            db.treatments.insert_one(treatment_doc)
            treatments_inserted += 1

    # 5. Summary
    print("-" * 30)
    print("🎉 MIGRATION SUCCESSFUL")
    print(f"🐴 Horses Added: {horses_inserted}")
    print(f"💊 Initial Treatments Added: {treatments_inserted}")
    print("-" * 30)

if __name__ == "__main__":
    main()
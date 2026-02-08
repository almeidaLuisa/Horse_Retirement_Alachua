import csv
from pymongo import MongoClient

uri = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["HorseSanctuary"]
collection = db["Horse_Tables"]

documents = []

with open("people.csv", newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Convert types if needed
        if "age" in row:
            row["age"] = int(row["age"])

        # DO NOT set _id
        documents.append(row)

if documents:
    collection.insert_many(documents)

# mongo_api.py

Simple Flask API to query the `Horse_Treatment_Tables` collection in MongoDB.

Environment variables:
- `MONGODB_URI` (default: `mongodb://localhost:27017`)
- `MONGODB_DB` (default: `HorseSanctuary`)
- `MONGODB_COLLECTION` (default: `Horse_Treatment_Tables`)

Run locally:

```bash
python -m venv venv
venv\Scripts\activate   # on Windows
pip install -r requirements.txt
set MONGODB_URI=<your-connection-string>
python mongo_api.py
```

Example website call (JavaScript):

```js
const id = '1234-5678-2';
fetch(`/api/treatment?id=${encodeURIComponent(id)}`)
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

Notes:
- The endpoint `/api/treatment?id=...` accepts IDs like `XXXX-XXXX-2`.
- The script uses a flexible query strategy to match a variety of possible field names in your collection. If you have a fixed schema, adapt `flexible_query()` in `mongo_api.py` to build direct queries for the exact fields you use.

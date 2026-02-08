from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import PyMongoError

# Optional: load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class DailyObsItem:
    date: datetime
    is_observation: bool
    is_todo: bool
    note: str
    status: str = "pending"  # "pending" or "complete"
    horse_id: Optional[str] = None
    created_by: Optional[str] = None

    def to_mongo(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "is_observation": self.is_observation,
            "is_todo": self.is_todo,
            "note": self.note,
            "status": self.status,
            "horse_id": self.horse_id,
            "created_by": self.created_by,
            "created_at": datetime.now(timezone.utc),
        }


def _get_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("Missing MONGODB_URI env var (set it in .env or system env).")
    return MongoClient(uri, tls=True)


def _get_collection():
    db_name = os.getenv("MONGODB_DB", "Horse_Retirement")
    client = _get_client()
    db = client[db_name]
    col = db["DailyObs_Tables"]  # collection name (change if you want)

    # Create indexes once (safe to call repeatedly)
    col.create_index([("date", DESCENDING)])
    col.create_index([("status", ASCENDING), ("date", DESCENDING)])
    col.create_index([("horse_id", ASCENDING), ("date", DESCENDING)])
    col.create_index([("created_by", ASCENDING), ("date", DESCENDING)])

    return col


def add_daily_obs(
    note: str,
    obs: bool,
    todo: bool,
    date: Optional[datetime] = None,
    horse_id: Optional[str] = None,
    created_by: Optional[str] = None,
    status: str = "pending",
) -> str:
    """
    Insert a Daily Obs / To-Do item.
    Returns the inserted document id as a string.
    """
    if not note or not note.strip():
        raise ValueError("note cannot be empty")
    if not (obs or todo):
        raise ValueError("At least one of obs or todo must be True")

    if date is None:
        date = datetime.now(timezone.utc)
    elif date.tzinfo is None:
        # treat naive datetime as UTC
        date = date.replace(tzinfo=timezone.utc)

    item = DailyObsItem(
        date=date,
        is_observation=bool(obs),
        is_todo=bool(todo),
        note=note.strip(),
        status=status,
        horse_id=horse_id,
        created_by=created_by,
    )

    col = _get_collection()
    try:
        res = col.insert_one(item.to_mongo())
        return str(res.inserted_id)
    except PyMongoError as e:
        raise RuntimeError(f"MongoDB insert failed: {e}") from e


def list_daily_obs(
    limit: int = 50,
    status: Optional[str] = None,          # "pending"/"complete"/None
    horse_id: Optional[str] = None,
    created_by: Optional[str] = None,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Read recent Daily Obs / To-Do items.
    Returns plain dicts ready to JSON-ify (ObjectId converted to str).
    """
    q: Dict[str, Any] = {}

    if status:
        q["status"] = status
    if horse_id:
        q["horse_id"] = horse_id
    if created_by:
        q["created_by"] = created_by
    if since:
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        q["date"] = {"$gte": since}

    col = _get_collection()
    try:
        docs = list(col.find(q).sort("date", DESCENDING).limit(int(limit)))
    except PyMongoError as e:
        raise RuntimeError(f"MongoDB query failed: {e}") from e

    # Convert ObjectId + datetime to friendly values
    out: List[Dict[str, Any]] = []
    for d in docs:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("date"), datetime):
            d["date"] = d["date"].isoformat()
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return out


def set_status(item_id: str, status: str) -> bool:
    """
    Mark an item as pending/complete.
    Returns True if modified.
    """
    if status not in ("pending", "complete"):
        raise ValueError("status must be 'pending' or 'complete'")

    from bson import ObjectId

    col = _get_collection()
    try:
        res = col.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
        )
        return res.modified_count == 1
    except Exception as e:
        raise RuntimeError(f"MongoDB update failed: {e}") from e

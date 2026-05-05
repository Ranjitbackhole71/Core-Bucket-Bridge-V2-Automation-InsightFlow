"""
Bucket Store — Backward-compatible artifact read layer.

Provides get_all_artifacts() for legacy callers.
"""
import json
import os
from typing import List, Dict, Any

BUCKET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
BUCKET_FILE = os.path.join(BUCKET_DIR, "bucket_artifacts.json")


def get_all_artifacts() -> List[Dict[str, Any]]:
    if not os.path.exists(BUCKET_FILE):
        return []
    with open(BUCKET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

import json
import os

BUCKET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "bucket_artifacts.json")
BUCKET_PATH = os.path.normpath(BUCKET_PATH)


def get_all_artifacts() -> list:
    """Return all persisted artifacts from the bucket."""
    if not os.path.exists(BUCKET_PATH):
        return []
    with open(BUCKET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

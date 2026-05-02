import json
import os

BUCKET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "bucket_artifacts.json")
BUCKET_PATH = os.path.normpath(BUCKET_PATH)


def store_artifact(artifact: dict) -> dict:
    """Persist artifact to bucket_artifacts.json and return stored record."""
    artifacts = []
    if os.path.exists(BUCKET_PATH):
        with open(BUCKET_PATH, "r", encoding="utf-8") as f:
            artifacts = json.load(f)

    artifacts.append(artifact)

    with open(BUCKET_PATH, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2)

    return artifact

import json
import os

FILE_PATH = "last_hash.json"

def load_last_hash():
    if not os.path.exists(FILE_PATH):
        return None
    with open(FILE_PATH, "r") as f:
        data = json.load(f)
        return data.get("last_hash")

def save_last_hash(hash_value):
    with open(FILE_PATH, "w") as f:
        json.dump({"last_hash": hash_value}, f)
"""
Sarathi — Replay Attack Detector (PERSISTENT)

File-backed persistent JTI store. Survives process restarts.
Thread-safe with TTL-based cleanup.
"""
import os
import json
import time
import threading
from typing import Optional

REPLAY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(REPLAY_DIR, exist_ok=True)
REPLAY_FILE = os.path.join(REPLAY_DIR, "sarathi_replay_store.json")


class ReplayDetector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._lock = threading.Lock()
            self._ttl_seconds: int = 300
            self._load_store()

    def _load_store(self):
        if os.path.exists(REPLAY_FILE):
            try:
                with open(REPLAY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._used_jtis: dict[str, float] = data.get("used_jtis", {})
                self._ttl_seconds = data.get("ttl_seconds", 300)
            except Exception:
                self._used_jtis = {}
        else:
            self._used_jtis = {}

    def _save_store(self):
        data = {
            "used_jtis": self._used_jtis,
            "ttl_seconds": self._ttl_seconds,
        }
        with open(REPLAY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def is_replayed(self, jti: str) -> bool:
        with self._lock:
            return jti in self._used_jtis

    def mark_used(self, jti: str):
        with self._lock:
            self._used_jtis[jti] = time.time()
            self._save_store()

    def cleanup_expired(self):
        with self._lock:
            now = time.time()
            expired = [jti for jti, ts in self._used_jtis.items() if now - ts > self._ttl_seconds]
            for jti in expired:
                del self._used_jtis[jti]
            if expired:
                self._save_store()

    def set_ttl(self, seconds: int):
        with self._lock:
            self._ttl_seconds = seconds
            self._save_store()

    def clear(self):
        with self._lock:
            self._used_jtis.clear()
            self._save_store()

    @property
    def count(self):
        with self._lock:
            return len(self._used_jtis)

    @property
    def used_jtis(self):
        with self._lock:
            return dict(self._used_jtis)


replay_detector = ReplayDetector()

"""
Sarathi — Cryptographic Key Manager

Manages RSA key pairs for authority token signing and verification.
Keys are generated on first load; public key is exported for Core to sign tokens.
"""
import os
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend


class SarathiKeyManager:
    _instance = None
    _private_key = None
    _public_key = None
    _public_key_pem = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._private_key is None:
            self._load_or_generate_keys()

    def _load_or_generate_keys(self):
        key_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "keys")
        os.makedirs(key_dir, exist_ok=True)

        private_path = os.path.join(key_dir, "sarathi_private.pem")
        public_path = os.path.join(key_dir, "sarathi_public.pem")

        if os.path.exists(private_path) and os.path.exists(public_path):
            with open(private_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            with open(public_path, "rb") as f:
                self._public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        else:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self._public_key = self._private_key.public_key()

            priv_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            pub_pem = self._public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            with open(private_path, "wb") as f:
                f.write(priv_pem)
            with open(public_path, "wb") as f:
                f.write(pub_pem)

        self._public_key_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def get_private_key(self):
        return self._private_key

    def get_public_key(self):
        return self._public_key

    def get_public_key_pem(self):
        return self._public_key_pem

    def get_public_key_b64(self):
        return base64.b64encode(self._public_key_pem).decode("utf-8")

    def sign_payload(self, payload_bytes: bytes) -> bytes:
        signature = self._private_key.sign(
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return signature

    def reload_keys(self):
        self._private_key = None
        self._public_key = None
        self._public_key_pem = None
        self._load_or_generate_keys()


sarathi_keys = SarathiKeyManager()

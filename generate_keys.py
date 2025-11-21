from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Serialize private key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Get public key
public_key = private_key.public_key()

# Serialize public key
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Write keys to files
with open("security/private.pem", "wb") as f:
    f.write(private_pem)

with open("security/public.pem", "wb") as f:
    f.write(public_pem)

print("RSA keypair generated successfully!")
print("Private key saved to: security/private.pem")
print("Public key saved to: security/public.pem")
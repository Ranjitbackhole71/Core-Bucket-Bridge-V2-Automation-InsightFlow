# Key Rotation Procedure

## Overview

This document describes the procedure for rotating RSA keys used by the Core-Bucket Bridge system. Regular key rotation is essential for maintaining security.

## When to Rotate Keys

Key rotation should be performed:
- Annually as part of routine security maintenance
- Immediately if a key compromise is suspected
- After any security incident involving the system

## Prerequisites

- Administrative access to the Core-Bucket Bridge server
- Backup of current keys (if available)
- Downtime window for key rotation (typically minimal)

## Key Rotation Steps

### 1. Generate New Key Pair

```bash
# Navigate to the security directory
cd /opt/core-bucket-bridge/security

# Generate new private key
openssl genrsa -out private_new.pem 2048

# Extract new public key
openssl rsa -in private_new.pem -pubout -out public_new.pem
```

### 2. Backup Current Keys

```bash
# Create backup directory with timestamp
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup current keys
cp private.pem "$BACKUP_DIR/"
cp public.pem "$BACKUP_DIR/"

# Also backup nonce cache
cp nonce_cache.json "$BACKUP_DIR/"
```

### 3. Update System Configuration

Update any configuration files that reference the key paths if needed. In most cases, the system expects keys to be named `private.pem` and `public.pem`.

### 4. Coordinate with Connected Systems

Notify all systems that connect to the Core-Bucket Bridge about the upcoming key rotation:
- Sohum rule engine
- Anmol backend pipeline
- Yash dashboard system
- Any other integrated systems

Provide them with the new public key well in advance.

### 5. Perform the Rotation

```bash
# Stop the Core-Bucket Bridge service
sudo systemctl stop core-bridge

# Replace old keys with new ones
mv private.pem private_old.pem
mv public.pem public_old.pem
mv private_new.pem private.pem
mv public_new.pem public.pem

# Restart the Core-Bucket Bridge service
sudo systemctl start core-bridge
```

### 6. Verify the Rotation

```bash
# Check that the service is running
sudo systemctl status core-bridge

# Test API endpoints
curl -X GET http://localhost:8000/core/health

# Monitor logs for any errors
tail -f /opt/core-bucket-bridge/logs/security_rejects.log
```

### 7. Update Connected Systems

Update all connected systems to use the new public key for signing requests.

### 8. Cleanup

After confirming that everything is working correctly and all systems have been updated:
- Remove old key files after a grace period (e.g., 30 days)
- Update documentation with new key details
- Record the rotation in security logs

## Rollback Procedure

If issues occur after key rotation:

```bash
# Stop the Core-Bucket Bridge service
sudo systemctl stop core-bridge

# Restore old keys
mv private.pem private_new.pem
mv public.pem public_new.pem
mv private_old.pem private.pem
mv public_old.pem public.pem

# Restart the Core-Bucket Bridge service
sudo systemctl start core-bridge
```

## Security Considerations

1. **Key Storage**: Ensure private keys are stored securely with appropriate file permissions (600)
2. **Access Control**: Limit access to private keys to authorized personnel only
3. **Transmission**: When sharing public keys, use secure channels
4. **Audit Trail**: Document all key rotations in security logs
5. **Grace Period**: Allow overlap period where both old and new keys are accepted during transition

## Monitoring

Monitor the following after key rotation:
- Security rejection logs for signature verification failures
- System health metrics
- Connected system connectivity status
- Error rates in API responses

## Automation

Consider automating key rotation using scripts that:
- Generate new keys on schedule
- Perform automated backups
- Handle service restarts
- Send notifications on completion
- Log rotation events

Example automation script outline:
```bash
#!/bin/bash
# key_rotation_automated.sh

# Implementation would include all steps above
# with proper error handling and notifications
```
# Token Policy and Administration Guide

## Overview

This document describes the JWT token policy and administration procedures for the Core-Bucket Bridge system. Tokens are used for authentication and authorization of API requests.

## Token Structure

Tokens follow the standard JWT format with the following claims:

```json
{
  "iss": "core-bucket-bridge",
  "exp": 1234567890,
  "roles": ["module"]
}
```

Claims:
- `iss`: Issuer (always "core-bucket-bridge")
- `exp`: Expiration timestamp (Unix epoch time)
- `roles`: Array of roles assigned to the token holder

## Roles and Permissions

### Available Roles

1. **module**: Basic role for core modules
   - Can send data to `/core/update`
   - Can send heartbeats to `/core/heartbeat`
   - Can query bucket status at `/bucket/status`

2. **automation**: Role for automation systems
   - Inherits all module permissions
   - Can access additional automation endpoints (if any)

3. **admin**: Administrative role
   - Inherits all automation permissions
   - Can access administrative endpoints
   - Can query system health at `/core/health`

### Role Mapping

| Endpoint | Required Role |
|----------|---------------|
| POST /core/update | module |
| POST /core/heartbeat | module |
| GET /bucket/status | module |
| GET /core/health | (public access) |

## Token Generation

### Python Script for Token Generation

```python
import jwt
from datetime import datetime, timedelta

def generate_token(secret_key, roles=["module"], expires_in_hours=24):
    """
    Generate a JWT token for Core-Bucket Bridge
    
    Args:
        secret_key (str): Secret key for signing the token
        roles (list): List of roles to assign to the token
        expires_in_hours (int): Hours until token expiration
    
    Returns:
        str: JWT token string
    """
    payload = {
        "iss": "core-bucket-bridge",
        "exp": (datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp(),
        "roles": roles
    }
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

# Example usage
SECRET_KEY = "your-secret-key-here"  # Should be stored securely
token = generate_token(SECRET_KEY, ["module"], 24)
print(f"Bearer {token}")
```

### Command Line Token Generation

```bash
# Using Python one-liner
python3 -c "
import jwt
from datetime import datetime, timedelta
payload = {
    'iss': 'core-bucket-bridge',
    'exp': (datetime.utcnow() + timedelta(hours=24)).timestamp(),
    'roles': ['module']
}
token = jwt.encode(payload, 'your-secret-key-here', algorithm='HS256')
print(f'Bearer {token}')
"
```

## Secret Key Management

### Generating a Secure Secret Key

```bash
# Generate a random 32-byte secret key
openssl rand -hex 32
```

### Storing the Secret Key

The secret key should be stored securely:
- As an environment variable
- In a secure configuration file with restricted permissions (600)
- Using a secrets management system in production

Example environment variable:
```bash
export CORE_BRIDGE_SECRET="your-generated-secret-key-here"
```

## Token Administration

### Token Lifecycle

1. **Creation**: Generate token with appropriate roles and expiration
2. **Distribution**: Securely distribute token to authorized systems
3. **Usage**: Systems use token for authenticated API requests
4. **Expiration**: Token automatically expires after set time
5. **Revocation**: If needed, revoke token by changing secret key

### Best Practices

1. **Short Lifespans**: Issue tokens with short expiration times (hours, not days)
2. **Role Minimization**: Assign only the minimum required roles
3. **Secure Distribution**: Use encrypted channels for token distribution
4. **Regular Rotation**: Rotate secret keys regularly
5. **Audit Logging**: Log token generation and usage

### Revocation Process

If a token needs to be revoked before expiration:
1. Change the secret key used for signing tokens
2. Generate new tokens for legitimate systems
3. Distribute new tokens to authorized systems
4. Update systems to use new tokens

Note: This revokes ALL tokens signed with the old secret key.

## Monitoring and Auditing

### Token Usage Monitoring

Monitor the following:
- Token authentication failures
- Unauthorized access attempts
- Excessive token usage from single sources
- Token expiration patterns

### Log Analysis

Check logs for:
- Invalid token errors
- Expired token errors
- Role-based access violations
- Unusual access patterns

Example log entries:
```
2025-12-06T10:00:00Z - Invalid token: Signature verification failed
2025-12-06T10:05:00Z - Expired token
2025-12-06T10:10:00Z - Insufficient privileges. Required role: module
```

## Troubleshooting

### Common Issues

1. **Invalid Token**: Check token signature and secret key
2. **Expired Token**: Generate a new token with future expiration
3. **Insufficient Privileges**: Verify token has required roles
4. **Token Rejected**: Check system time synchronization

### Debugging Steps

1. Decode the JWT token to verify claims:
   ```bash
   # Using online decoder or command line tool
   python3 -c "
   import jwt
   token = 'your-token-here'
   try:
       decoded = jwt.decode(token, options={'verify_signature': False})
       print(decoded)
   except Exception as e:
       print(f'Decode error: {e}')
   "
   ```

2. Check system time synchronization:
   ```bash
   timedatectl status
   ```

3. Verify secret key configuration:
   ```bash
   echo $CORE_BRIDGE_SECRET
   ```

## Security Considerations

1. **Secret Key Protection**: Never commit secret keys to version control
2. **Token Transmission**: Always use HTTPS for token transmission
3. **Token Storage**: Store tokens securely on client systems
4. **Access Logging**: Maintain logs of token usage for audit purposes
5. **Rate Limiting**: Implement rate limiting to prevent token brute-force attacks
# HTTPS Certificate Setup Guide

## Self-Signed Certificate (Development/Testing)

For development and testing purposes, you can generate a self-signed certificate:

```bash
# Create directory for certificates
sudo mkdir -p /etc/ssl/certs /etc/ssl/private

# Generate private key
sudo openssl genrsa -out /etc/ssl/private/core-bridge.key 2048

# Generate certificate signing request (CSR)
sudo openssl req -new -key /etc/ssl/private/core-bridge.key -out /etc/ssl/certs/core-bridge.csr

# Generate self-signed certificate (valid for 365 days)
sudo openssl x509 -req -days 365 -in /etc/ssl/certs/core-bridge.csr -signkey /etc/ssl/private/core-bridge.key -out /etc/ssl/certs/core-bridge.crt
```

## Production Certificate (Let's Encrypt)

For production environments, it's recommended to use Let's Encrypt certificates:

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (add to crontab)
# Edit crontab: sudo crontab -e
# Add this line to check for renewal twice daily:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Certificate Permissions

Ensure proper permissions for your certificates:

```bash
# Private key should be readable only by root
sudo chmod 600 /etc/ssl/private/core-bridge.key
sudo chown root:root /etc/ssl/private/core-bridge.key

# Certificate should be readable by nginx
sudo chmod 644 /etc/ssl/certs/core-bridge.crt
sudo chown root:root /etc/ssl/certs/core-bridge.crt
```

## Certificate Renewal

Self-signed certificates need to be manually renewed when they expire. For Let's Encrypt, automatic renewal is handled by Certbot.

To manually renew a self-signed certificate:
```bash
# Backup old certificate
sudo cp /etc/ssl/certs/core-bridge.crt /etc/ssl/certs/core-bridge.crt.backup

# Generate new certificate
sudo openssl x509 -req -days 365 -in /etc/ssl/certs/core-bridge.csr -signkey /etc/ssl/private/core-bridge.key -out /etc/ssl/certs/core-bridge.crt
```

## Testing HTTPS Connection

After setting up your certificates, test the HTTPS connection:

```bash
# Test with curl
curl -I https://your-domain.com

# Test with openssl
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## Troubleshooting

Common issues and solutions:

1. **Permission denied errors**: Check file permissions and ownership
2. **Certificate verification failed**: Ensure certificate chain is complete
3. **Nginx won't start**: Check nginx error logs: `sudo journalctl -u nginx`
4. **Mixed content warnings**: Ensure all resources are loaded over HTTPS
#!/bin/bash
# generate-password.sh - Generate a secure random password for MikroTik CHR

set -e

# Generate a 24-character random password using base64
PASSWORD=$(openssl rand -base64 18 | tr -d "=+/" | cut -c1-24)

echo "Generated password: $PASSWORD"
echo "password=$PASSWORD" >> $GITHUB_OUTPUT

# Replace the placeholder in startup.rsc
sed -i "s/PLACEHOLDER_PASSWORD/$PASSWORD/g" scripts/startup.rsc

echo "Password injected into startup.rsc"
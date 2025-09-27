#!/bin/bash
# generate-password.sh - Generate a secure random password for MikroTik CHR

set -e

# Generate a 24-character random password using base64
PASSWORD=$(openssl rand -base64 18 | tr -d "=+/" | cut -c1-24)

echo "Generated password: $PASSWORD"
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "password=$PASSWORD" >> "$GITHUB_OUTPUT"
fi

# Replace the placeholder in startup.rsc
if grep -q "PLACEHOLDER_PASSWORD" scripts/startup.rsc; then
    sed -i "s/PLACEHOLDER_PASSWORD/$PASSWORD/g" scripts/startup.rsc
    echo "Password injected into startup.rsc"
else
    echo "Warning: PLACEHOLDER_PASSWORD not found in startup.rsc"
    echo "This might indicate the placeholder was already replaced or is missing"
fi
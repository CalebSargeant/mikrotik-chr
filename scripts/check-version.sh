#!/bin/bash
# check-version.sh - Manually check for new Mikrotik CHR versions

set -euo pipefail

echo "🔍 MikroTik CHR Version Checker"
echo "==============================="

# Get latest version using the same logic as workflow
echo "📡 Attempting to get latest CHR version..."

# Method 1: Try parsing download page
LATEST_VERSION=$(curl -s "https://mikrotik.com/download" \
  | grep -o 'chr-[0-9]\.[0-9]\+\.[0-9]\+\.img\.zip' \
  | grep -v "beta" \
  | grep -v "rc" \
  | sort -V \
  | tail -n 1 \
  | sed 's/chr-\(.*\)\.img\.zip/\1/' || true)
  
# Method 2: If that fails, check existing releases to get current version 
if [ -z "$LATEST_VERSION" ]; then
  echo "⚠️ Download page parsing failed, checking existing releases..."
  LATEST_VERSION=$(git ls-remote --tags origin | \
    grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+$' | \
    sed 's/^v//' | sort -V | tail -n 1 || echo "")
fi

# Method 3: Fallback to known working version if all else fails
if [ -z "$LATEST_VERSION" ]; then
  echo "⚠️ All version detection methods failed, using fallback version"
  LATEST_VERSION="7.19.6"
fi

echo "✅ Latest CHR version: $LATEST_VERSION"

# Check if this version already exists as a release
TAG="v${LATEST_VERSION}"
echo ""
echo "🏷️ Checking for existing release: $TAG"

if git ls-remote --tags origin | grep -q "$TAG$"; then
  echo "✅ Release $TAG already exists"
  echo "ℹ️ To force rebuild, scripts or workflows must be modified"
else
  echo "🆕 New version detected - $TAG would be built"
  
  # Test download URL
  DOWNLOAD_URL="https://download.mikrotik.com/routeros/${LATEST_VERSION}/chr-${LATEST_VERSION}.img.zip"
  echo "📦 Testing download URL: $DOWNLOAD_URL"
  
  if curl --head --fail "$DOWNLOAD_URL" >/dev/null 2>&1; then
    echo "✅ Download URL is accessible"
  else
    echo "❌ Download URL is not accessible - build would fail"
    exit 1
  fi
fi

echo ""
echo "🎉 Version check complete!"
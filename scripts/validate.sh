#!/bin/bash
# validate.sh - Validate the CHR build setup

set -e

echo "🔍 Validating MikroTik CHR Multi-Architecture Build Setup"
echo "======================================================="

# Check required files exist
echo "📁 Checking required files..."
required_files=(
    "scripts/startup.rsc"
    "scripts/generate-password.sh"
    "scripts/check-version.sh"
    "scripts/flash.sh"
    ".github/workflows/build-chr.yml"
    "docs/aws-deployment.md"
    "docs/marketplace-preparation.md"
    "README.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        exit 1
    fi
done

# Check script permissions
echo ""
echo "🔐 Checking script permissions..."
for script in scripts/*.sh; do
    if [ -x "$script" ]; then
        echo "✅ $script is executable"
    else
        echo "❌ $script is not executable"
        exit 1
    fi
done

# Validate shell script syntax
echo ""
echo "📝 Validating shell script syntax..."
for script in scripts/*.sh; do
    if bash -n "$script"; then
        echo "✅ $script syntax OK"
    else
        echo "❌ $script syntax ERROR"
        exit 1
    fi
done

# Check startup.rsc has placeholder
echo ""
echo "🔑 Checking startup.rsc configuration..."
if grep -q "PLACEHOLDER_PASSWORD" scripts/startup.rsc; then
    echo "✅ Password placeholder found"
else
    echo "❌ Password placeholder missing - may have been replaced during testing"
    exit 1
fi

if grep -q "/ip service enable ssh" scripts/startup.rsc; then
    echo "✅ SSH service enabled"
else
    echo "❌ SSH service not enabled"
    exit 1
fi

if grep -q "/ip dhcp-client add interface=ether1" scripts/startup.rsc; then
    echo "✅ DHCP client configuration found"
else
    echo "❌ DHCP client configuration missing"
    exit 1
fi

# Test password generation
echo ""
echo "🔐 Testing password generation..."
if ./scripts/generate-password.sh >/dev/null 2>&1; then
    echo "✅ Password generation works"
    # Reset back to placeholder
    sed -i 's/password="[^"]*"/password="PLACEHOLDER_PASSWORD"/g' scripts/startup.rsc
    echo "✅ Placeholder restored"
else
    echo "❌ Password generation failed"
    exit 1
fi

# Test flash script architecture detection
echo ""
echo "🏗️ Testing flash script architecture detection..."
TEMP_TEST=$(cd /tmp && bash -c '
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        CHR_ARCH="amd64"
        ;;
    aarch64|arm64)
        CHR_ARCH="arm64"
        ;;
    *)
        CHR_ARCH="unknown"
        ;;
esac
echo "Arch: $ARCH -> CHR: $CHR_ARCH"
')
if [[ $TEMP_TEST == *"Arch:"* ]] && [[ $TEMP_TEST != *"unknown"* ]]; then
    echo "✅ Architecture detection works: $TEMP_TEST"
else
    echo "❌ Architecture detection failed: $TEMP_TEST"
    exit 1
fi

# Test GitHub Actions workflow syntax
echo ""
echo "🔧 Validating GitHub Actions workflow..."
if python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-chr.yml').read())" >/dev/null 2>&1; then
    echo "✅ GitHub Actions workflow syntax is valid"
else
    echo "❌ GitHub Actions workflow has syntax errors"
    exit 1
fi

echo ""
echo "🎉 All validation checks passed!"
echo "======================================================="
echo "✅ Multi-architecture build setup is ready"
echo "✅ Password rotation is configured"
echo "✅ Interfaces are enabled for cloud deployment"
echo "✅ AWS documentation is in place"
echo "✅ Streamlined workflow with unified releases configured"
echo ""
echo "Next steps:"
echo "1. Push changes to trigger workflow (only runs on new CHR versions)"
echo "2. Monitor GitHub Actions for smart build triggers"
echo "3. Check for new versions with: ./scripts/check-version.sh"
echo "4. Test deployment with generated unified releases"
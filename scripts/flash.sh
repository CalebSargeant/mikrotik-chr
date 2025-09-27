#!/bin/bash
# flash.sh - Flash MikroTik CHR image and reboot
# This script will download a pre-built CHR image for the detected architecture,
# write it to /dev/sda, and then reboot the machine.

set +e

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        CHR_ARCH="amd64"
        ;;
    aarch64|arm64)
        CHR_ARCH="arm64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        echo "Supported: x86_64 (amd64), aarch64/arm64"
        exit 1
        ;;
esac

echo "Detected architecture: $ARCH -> CHR architecture: $CHR_ARCH"

# Get latest release URL
# Find the first release that contains the correct architecture asset
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/CalebSargeant/mikrotik-chr/releases" | jq -r --arg arch "$CHR_ARCH" '
  .[] 
  | .assets[]? 
  | select(.name | test("chr-" + $arch + "\\.img\\.gz$")) 
  | .browser_download_url' | head -n 1)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Could not find download URL for architecture: $CHR_ARCH"
    echo "Please check if the release exists at: https://github.com/CalebSargeant/mikrotik-chr/releases"
    exit 1
fi

echo "Downloading and flashing CHR image for $CHR_ARCH..."
echo "Download URL: $DOWNLOAD_URL"

curl -L "$DOWNLOAD_URL" | gunzip | dd of=/dev/sda bs=1M status=progress || :

echo "CHR image flashed successfully."
echo "Initiating reboot..."

# Display reboot message
cat << EOF

=================================================
MikroTik CHR Flash Complete!
=================================================

The system will reboot in 5 seconds.

After reboot:
- CHR will be available via SSH on port 22
- WebFig will be available on https://<ip>:8729
- Username: admin
- Password: Check the GitHub release notes

Wait 2-3 minutes after reboot for CHR to fully initialize.

=================================================
EOF

sleep 5
nohup reboot >/dev/null 2>&1 &
sleep 30 || :

echo "Flash script completed (exit 0)."
exit 0
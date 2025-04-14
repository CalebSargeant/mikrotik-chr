#!/bin/bash
# flash.sh - Flash MikroTik CHR image and reboot
# This script will download a pre-baked CHR image,
# write it to /dev/sda, and then reboot the machine.

set +e

echo "Downloading and flashing CHR image..."
curl -L "https://github.com/CalebSargeant/mikrotik-chr/releases/download/v7.18.2/chr.img.gz" | gunzip | dd of=/dev/sda bs=1M || :

echo "Initiating reboot..."
nohup reboot >/dev/null 2>&1 &
sleep 30 || :

echo "Flash script completed (exit 0)."
exit 0
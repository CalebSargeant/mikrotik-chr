#!/bin/bash
# inject.sh - Inject startup config into a CHR raw image as /rw/autorun.scr
#
# Usage: sudo ./scripts/inject.sh [chr-image.img]   (default: chr.img)
#
# RouterOS executes /rw/autorun.scr exactly once on first boot, then clears it.
# The file MUST be under rw/ with the .scr extension on the writable partition
# (ext3, volume label "RouterOS"). A file at the partition root, or named .rsc,
# is NOT executed — that was the previous bug (and why "the startup did nothing").
set -euo pipefail

IMG="${1:-chr.img}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STARTUP="${SCRIPT_DIR}/startup.rsc"

if [[ $EUID -ne 0 ]]; then
    echo "❌ Must run as root (needs losetup/mount). Try: sudo $0 $*"
    exit 1
fi
[[ -f "$IMG" ]]     || { echo "❌ Image not found: $IMG"; exit 1; }
[[ -f "$STARTUP" ]] || { echo "❌ startup.rsc not found: $STARTUP"; exit 1; }

MNT="$(mktemp -d)"
LOOP="$(losetup --show -Pf "$IMG")"
cleanup() {
    umount "$MNT" 2>/dev/null || true
    losetup -d "$LOOP" 2>/dev/null || true
    rmdir "$MNT" 2>/dev/null || true
}
trap cleanup EXIT

# Find the writable partition (the one containing rw/) instead of hardcoding p2,
# so this survives image layout changes.
found=""
for part in "${LOOP}"p{1..8}; do
    [[ -e "$part" ]] || continue
    mount "$part" "$MNT" 2>/dev/null || continue
    if [[ -d "$MNT/rw" ]]; then
        found="$part"
        break
    fi
    umount "$MNT" 2>/dev/null || true
done
[[ -n "$found" ]] || { echo "❌ Could not find the rw/ partition in $IMG"; exit 1; }
echo "Using writable partition: $found"

cp "$STARTUP" "$MNT/rw/autorun.scr"
echo "Injected /rw/autorun.scr:"
cat "$MNT/rw/autorun.scr"
sync

echo "✅ Startup script injected successfully as /rw/autorun.scr"

#!/bin/bash
set -e

echo "Extracting CHR image..."
# Extract the CHR image using 7z
7z x chr.img -o./chr_extract

echo "Creating directory structure if needed..."
mkdir -p ./chr_extract/router/rw/store/

echo "Injecting startup script..."
cp scripts/startup.rsc ./chr_extract/router/rw/store/

echo "Repacking the image..."
# Navigate to the extraction directory
cd ./chr_extract

# Repack only the RouterOS.img file (which contains the router directory)
7z a -tzip ../modified-RouterOS.img ./router/

# Move back to the original directory
cd ..

# Replace the original RouterOS.img in chr.img with our modified version
7z u chr.img modified-RouterOS.img

echo "✅ Startup script injected successfully"
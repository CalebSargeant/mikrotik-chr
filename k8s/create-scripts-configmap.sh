#!/bin/bash
# create-scripts-configmap.sh
# Helper script to create the scripts ConfigMap from actual files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Creating scripts ConfigMap..."

kubectl create configmap routeros-version-checker-scripts \
  --from-file=check_routeros_version.py="$REPO_ROOT/scripts/check_routeros_version.py" \
  --from-file=requirements.txt="$REPO_ROOT/requirements.txt" \
  --dry-run=client -o yaml > "$SCRIPT_DIR/scripts-configmap.yaml"

echo "✅ Created scripts-configmap.yaml"
echo "Apply it with: kubectl apply -f k8s/scripts-configmap.yaml"

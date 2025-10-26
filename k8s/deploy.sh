#!/bin/bash
# deploy.sh - Quick deployment script for Kubernetes
# This script helps you deploy the RouterOS version checker to Kubernetes

set -euo pipefail

echo "🚀 RouterOS Version Checker - Kubernetes Deployment"
echo "===================================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster"
    echo "Please configure kubectl to connect to your cluster"
    exit 1
fi

echo "✅ kubectl is configured and connected to cluster"
echo ""

# Prompt for namespace
read -p "Enter namespace (default: default): " NAMESPACE
NAMESPACE=${NAMESPACE:-default}

echo "Using namespace: $NAMESPACE"
echo ""

# Check if secret exists
if kubectl get secret routeros-version-checker-secret -n "$NAMESPACE" &> /dev/null; then
    echo "✅ Secret 'routeros-version-checker-secret' already exists"
else
    echo "❌ Secret 'routeros-version-checker-secret' not found"
    echo ""
    echo "Please create the secret first:"
    echo "1. Copy k8s/secret.yaml.template to k8s/secret.yaml"
    echo "2. Edit k8s/secret.yaml with your GitHub App credentials"
    echo "3. Apply: kubectl apply -f k8s/secret.yaml -n $NAMESPACE"
    echo ""
    read -p "Do you want to create the secret now? (y/N): " CREATE_SECRET
    
    if [[ "$CREATE_SECRET" =~ ^[Yy]$ ]]; then
        echo ""
        read -p "Enter your GitHub App ID: " APP_ID
        echo "Paste your GitHub App private key (press Ctrl+D when done):"
        PRIVATE_KEY=$(cat)
        
        # Base64 encode
        APP_ID_B64=$(echo -n "$APP_ID" | base64 -w 0)
        PRIVATE_KEY_B64=$(echo -n "$PRIVATE_KEY" | base64 -w 0)
        
        # Create secret
        cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: routeros-version-checker-secret
  namespace: $NAMESPACE
type: Opaque
data:
  GITHUB_APP_ID: $APP_ID_B64
  GITHUB_PRIVATE_KEY: $PRIVATE_KEY_B64
EOF
        
        echo "✅ Secret created successfully"
    else
        echo "Exiting. Please create the secret and run this script again."
        exit 1
    fi
fi

echo ""
echo "📦 Deploying resources..."
echo ""

# Apply ConfigMap
echo "Creating ConfigMap..."
kubectl apply -f k8s/configmap.yaml -n "$NAMESPACE"

# Generate and apply scripts ConfigMap
echo "Creating scripts ConfigMap..."
./k8s/create-scripts-configmap.sh
kubectl apply -f k8s/scripts-configmap.yaml -n "$NAMESPACE"

# Apply PVC
echo "Creating PersistentVolumeClaim..."
kubectl apply -f k8s/pvc.yaml -n "$NAMESPACE"

# Wait for PVC to be bound
echo "Waiting for PVC to be bound..."
kubectl wait --for=condition=bound pvc/routeros-version-data -n "$NAMESPACE" --timeout=60s || echo "⚠️  PVC not bound yet, continuing anyway..."

# Apply CronJob
echo "Creating CronJob..."
kubectl apply -f k8s/cronjob.yaml -n "$NAMESPACE"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Verify the deployment:"
echo "  kubectl get cronjobs -n $NAMESPACE"
echo "  kubectl get pvc -n $NAMESPACE"
echo ""
echo "🔍 Check logs (after a job runs):"
echo "  kubectl get jobs -n $NAMESPACE"
echo "  kubectl logs -l app=routeros-version-checker -n $NAMESPACE"
echo ""
echo "🧪 Manually trigger a job:"
echo "  kubectl create job --from=cronjob/routeros-version-checker manual-test-\$(date +%s) -n $NAMESPACE"
echo ""

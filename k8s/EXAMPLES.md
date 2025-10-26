# Example Configuration for RouterOS Version Checker

This directory contains example configuration files for deploying the RouterOS version checker in different scenarios.

## Quick Start Example

The simplest deployment for testing:

```bash
# 1. Create namespace
kubectl create namespace routeros-checker

# 2. Create secret with your GitHub App credentials
# Method 1: From files (recommended - doesn't expose secrets in shell history)
echo -n "your-app-id" > /tmp/app-id.txt
cat private-key.pem > /tmp/private-key.pem
kubectl create secret generic routeros-version-checker-secret \
  --from-file=GITHUB_APP_ID=/tmp/app-id.txt \
  --from-file=GITHUB_PRIVATE_KEY=/tmp/private-key.pem \
  -n routeros-checker
rm /tmp/app-id.txt /tmp/private-key.pem

# Method 2: From literals (simpler but exposes in shell history)
# kubectl create secret generic routeros-version-checker-secret \
#   --from-literal=GITHUB_APP_ID="your-app-id" \
#   --from-literal=GITHUB_PRIVATE_KEY="$(cat private-key.pem)" \
#   -n routeros-checker

# 3. Deploy all resources
cd k8s
kubectl apply -f configmap.yaml -n routeros-checker
./create-scripts-configmap.sh
kubectl apply -f scripts-configmap.yaml -n routeros-checker
kubectl apply -f pvc.yaml -n routeros-checker
kubectl apply -f cronjob.yaml -n routeros-checker

# 4. Manually trigger a test job
kubectl create job --from=cronjob/routeros-version-checker test-run -n routeros-checker

# 5. Check the logs
kubectl logs -l app=routeros-version-checker -n routeros-checker --tail=100
```

## Example Scenarios

### 1. Development/Testing

For testing purposes, run the job more frequently:

```yaml
# In cronjob.yaml, change schedule to every hour
schedule: "0 * * * *"
```

### 2. Production

For production, run less frequently and add resource limits:

```yaml
# In cronjob.yaml, change schedule to every 12 hours
schedule: "0 */12 * * *"

# Increase resource limits
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 3. Multiple Repositories

To monitor multiple repositories, create separate CronJobs:

```yaml
# cronjob-repo1.yaml
metadata:
  name: routeros-version-checker-repo1
---
# cronjob-repo2.yaml
metadata:
  name: routeros-version-checker-repo2
```

Each with its own ConfigMap specifying the repository.

## Environment Variables

All supported environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_APP_ID` | Yes | - | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Yes | - | GitHub App private key (PEM format) |
| `GITHUB_REPO` | No | `CalebSargeant/mikrotik-chr` | Repository to trigger workflows in |
| `WORKFLOW_ID` | No | `build-chr.yml` | Workflow file to trigger |
| `VERSION_FILE` | No | `/data/current_version.txt` | Path to version storage file |

## Testing the Script Locally

Before deploying to Kubernetes, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_APP_ID="12345"
export GITHUB_PRIVATE_KEY="$(cat /path/to/private-key.pem)"
export GITHUB_REPO="CalebSargeant/mikrotik-chr"
export WORKFLOW_ID="build-chr.yml"
export VERSION_FILE="/tmp/current_version.txt"

# Run the script
python scripts/check_routeros_version.py
```

## Troubleshooting Examples

### Check if PVC is bound

```bash
kubectl get pvc -n routeros-checker
```

### View ConfigMap contents

```bash
kubectl get configmap routeros-version-checker-config -n routeros-checker -o yaml
```

### Check Secret (without revealing values)

```bash
kubectl get secret routeros-version-checker-secret -n routeros-checker
```

### Debug a failed job

```bash
# Get the failed pod name
kubectl get pods -n routeros-checker --field-selector=status.phase=Failed

# View logs
kubectl logs <pod-name> -n routeros-checker
```

### Force a new version check

```bash
# Method 1: Delete the version file using a debug pod with proper volume mounts
kubectl run -it --rm debug --image=busybox -n routeros-checker \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "debug",
      "image": "busybox",
      "stdin": true,
      "tty": true,
      "command": ["sh", "-c", "rm -f /data/current_version.txt && echo Version file deleted"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "routeros-version-data"
      }
    }]
  }
}'

# Method 2: Using kubectl exec if a job pod is still running
# POD_NAME=$(kubectl get pods -n routeros-checker -l app=routeros-version-checker -o jsonpath='{.items[0].metadata.name}')
# kubectl exec -it $POD_NAME -n routeros-checker -- rm -f /data/current_version.txt

# Trigger a job to re-check
kubectl create job --from=cronjob/routeros-version-checker force-check -n routeros-checker
```

## Security Considerations

### Using Sealed Secrets

For production, consider using [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets):

```bash
# Install kubeseal
# ... installation steps ...

# Create sealed secret
echo -n "your-app-id" | kubectl create secret generic routeros-version-checker-secret \
  --dry-run=client \
  --from-file=GITHUB_APP_ID=/dev/stdin \
  -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml
```

### Using External Secrets

For AWS Secrets Manager, Azure Key Vault, etc., use [External Secrets Operator](https://external-secrets.io/):

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: routeros-version-checker-secret
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: routeros-version-checker-secret
  data:
  - secretKey: GITHUB_APP_ID
    remoteRef:
      key: github-app
      property: app_id
  - secretKey: GITHUB_PRIVATE_KEY
    remoteRef:
      key: github-app
      property: private_key
```

## Monitoring and Alerting

### Using Prometheus

Add Prometheus annotations to the CronJob:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
```

### Using Grafana

Create a dashboard to monitor:
- Job success/failure rate
- Time between version checks
- Last detected version
- Workflow trigger success rate

## Advanced Examples

### Custom Notification on New Version

Extend the script to send Slack notifications:

```python
def send_slack_notification(self, message: str):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={'text': message})

# In the run() method:
if self.trigger_workflow(access_token, latest_version):
    self.send_slack_notification(f"🚀 New RouterOS {latest_version} detected!")
```

### Multiple Workflow Triggers

Trigger multiple workflows:

```python
workflows = ['build-chr.yml', 'test-chr.yml', 'deploy-chr.yml']
for workflow in workflows:
    self.trigger_workflow(access_token, latest_version, workflow)
```

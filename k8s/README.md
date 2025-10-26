# RouterOS Version Checker for Kubernetes

This directory contains Kubernetes manifests for deploying an automated RouterOS version checker that runs as a CronJob. When a new MikroTik RouterOS version is detected, it triggers a GitHub workflow using GitHub App authentication.

## Overview

The RouterOS version checker:
- 🔍 Checks MikroTik's download page for new RouterOS releases every 6 hours
- 💾 Stores the current version in a PersistentVolume
- 🔐 Authenticates with GitHub using a GitHub App (JWT + installation token)
- 🚀 Triggers the `build-chr.yml` workflow when a new version is detected
- 📊 Provides comprehensive logging for debugging

## Architecture

```
┌─────────────────────┐
│   Kubernetes        │
│   CronJob           │
│  (Every 6 hours)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Python Script      │
│  - Check MikroTik   │
│  - Compare Version  │
│  - Auth with GitHub │
│  - Trigger Workflow │
└──────────┬──────────┘
           │
           ├─────────────────────┐
           │                     │
           ▼                     ▼
┌──────────────────┐   ┌────────────────┐
│ PersistentVolume │   │  GitHub API    │
│  (Store Version) │   │  (Trigger WF)  │
└──────────────────┘   └────────────────┘
```

## Prerequisites

1. **Kubernetes Cluster**: Access to a Kubernetes cluster (1.19+)
2. **kubectl**: Configured to access your cluster
3. **GitHub App**: A GitHub App with the following:
   - Repository access to `CalebSargeant/mikrotik-chr`
   - Permissions: `actions: write` (to trigger workflows)
   - Private key (PEM format)

## Setting Up a GitHub App

1. **Create a GitHub App**:
   - Go to GitHub Settings → Developer settings → GitHub Apps → New GitHub App
   - Name: `RouterOS Version Checker`
   - Homepage URL: `https://github.com/CalebSargeant/mikrotik-chr`
   - Webhook: Uncheck "Active"

2. **Set Permissions**:
   - Repository permissions → Actions: Read & write

3. **Install the App**:
   - Install the app on the `CalebSargeant/mikrotik-chr` repository

4. **Get Credentials**:
   - Note the **App ID** (you'll need this)
   - Generate and download a **private key** (PEM file)

## Deployment Steps

### 1. Create Namespace (Optional)

```bash
kubectl create namespace routeros-checker
```

If you use a different namespace, update all YAML files accordingly.

### 2. Create the Secret

First, base64 encode your GitHub App credentials:

```bash
# Encode App ID
echo -n "YOUR_APP_ID" | base64

# Encode private key (must be one line)
cat private-key.pem | base64 -w 0
```

Create `secret.yaml` from the template:

```bash
cp k8s/secret.yaml.template k8s/secret.yaml
```

Edit `k8s/secret.yaml` and replace the placeholders:
- `<YOUR_GITHUB_APP_ID>`: Base64-encoded App ID
- `<YOUR_GITHUB_PRIVATE_KEY_BASE64>`: Base64-encoded private key

Apply the secret:

```bash
kubectl apply -f k8s/secret.yaml
```

**⚠️ Important**: Never commit `secret.yaml` with real credentials to version control!

### 3. Create ConfigMap for Configuration

```bash
kubectl apply -f k8s/configmap.yaml
```

You can customize the configuration by editing `configmap.yaml`:
- `GITHUB_REPO`: Repository to trigger workflows in
- `WORKFLOW_ID`: Workflow file to trigger
- `VERSION_FILE`: Path where version is stored

### 4. Create Scripts ConfigMap

Generate the scripts ConfigMap from the actual Python script:

```bash
./k8s/create-scripts-configmap.sh
kubectl apply -f k8s/scripts-configmap.yaml
```

### 5. Create PersistentVolumeClaim

```bash
kubectl apply -f k8s/pvc.yaml
```

This creates a 1Gi volume to store the current RouterOS version.

### 6. Deploy the CronJob

```bash
kubectl apply -f k8s/cronjob.yaml
```

This creates a CronJob that runs every 6 hours by default.

## Verification

### Check CronJob Status

```bash
kubectl get cronjobs
```

### View Recent Jobs

```bash
kubectl get jobs
```

### Check Pod Logs

```bash
# Get the most recent pod
kubectl get pods --sort-by=.metadata.creationTimestamp

# View logs
kubectl logs <pod-name>
```

### Manually Trigger a Job

```bash
kubectl create job --from=cronjob/routeros-version-checker manual-check-$(date +%s)
```

## Configuration

### Changing the Schedule

Edit `k8s/cronjob.yaml` and modify the `schedule` field:

```yaml
schedule: "0 */6 * * *"  # Every 6 hours
```

Examples:
- Every hour: `"0 * * * *"`
- Every day at 3 AM: `"0 3 * * *"`
- Every 12 hours: `"0 */12 * * *"`

### Changing the Workflow

Edit `k8s/configmap.yaml` and update `WORKFLOW_ID`:

```yaml
WORKFLOW_ID: "build-chr.yml"  # or another workflow file
```

### Using a Different Repository

Edit `k8s/configmap.yaml` and update `GITHUB_REPO`:

```yaml
GITHUB_REPO: "owner/repository"
```

## Monitoring and Debugging

### View All Resources

```bash
kubectl get all -l app=routeros-version-checker
```

### Check PersistentVolume Data

```bash
# Create a debug pod
kubectl run -it --rm debug --image=busybox --restart=Never -- sh

# Inside the pod (after mounting the PVC):
cat /data/current_version.txt
```

### Common Issues

#### 1. Secret Not Found

**Error**: `Secret "routeros-version-checker-secret" not found`

**Solution**: Ensure you created the secret:
```bash
kubectl apply -f k8s/secret.yaml
```

#### 2. Permission Denied on GitHub

**Error**: `Failed to trigger workflow: 403`

**Solution**: 
- Verify GitHub App has `actions: write` permission
- Ensure the app is installed on the repository
- Check that the private key is correct and properly base64-encoded

#### 3. Version File Not Persisting

**Error**: Script always sees version as `None`

**Solution**: 
- Verify PVC is bound: `kubectl get pvc`
- Check pod has mounted the volume: `kubectl describe pod <pod-name>`

#### 4. Python Dependencies Failed to Install

**Error**: `Could not find a version that satisfies the requirement...`

**Solution**: 
- Check network connectivity from the cluster
- Verify the Python image version in `cronjob.yaml`

### Viewing Logs

```bash
# Get recent job
JOB_NAME=$(kubectl get jobs --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')

# Get pod from job
POD_NAME=$(kubectl get pods --selector=job-name=$JOB_NAME -o jsonpath='{.items[0].metadata.name}')

# View logs
kubectl logs $POD_NAME
```

### Example Log Output

Successful run:
```
2025-10-26 05:00:00 - __main__ - INFO - ============================================================
2025-10-26 05:00:00 - __main__ - INFO - RouterOS Version Checker - Starting
2025-10-26 05:00:00 - __main__ - INFO - ============================================================
2025-10-26 05:00:01 - __main__ - INFO - Fetching latest RouterOS version from MikroTik...
2025-10-26 05:00:02 - __main__ - INFO - Latest RouterOS version found: 7.20.2
2025-10-26 05:00:02 - __main__ - INFO - Current stored version: 7.20.1
2025-10-26 05:00:02 - __main__ - INFO - New version detected! Current: 7.20.1, Latest: 7.20.2
2025-10-26 05:00:03 - __main__ - INFO - Getting GitHub App installation token...
2025-10-26 05:00:04 - __main__ - INFO - Installation token obtained successfully
2025-10-26 05:00:04 - __main__ - INFO - Triggering workflow for RouterOS version 7.20.2...
2025-10-26 05:00:05 - __main__ - INFO - Workflow triggered successfully for version 7.20.2
2025-10-26 05:00:05 - __main__ - INFO - Updated stored version to: 7.20.2
2025-10-26 05:00:05 - __main__ - INFO - ============================================================
2025-10-26 05:00:05 - __main__ - INFO - RouterOS Version Checker - Completed Successfully
2025-10-26 05:00:05 - __main__ - INFO - ============================================================
```

## Security Best Practices

1. **Never commit secrets**: The `secret.yaml` file should never be committed with real credentials
2. **Use RBAC**: Consider creating a dedicated ServiceAccount with minimal permissions
3. **Rotate credentials**: Regularly rotate your GitHub App private key
4. **Monitor logs**: Regularly check logs for unauthorized access attempts
5. **Namespace isolation**: Deploy in a dedicated namespace with network policies

## Cleanup

To remove all resources:

```bash
kubectl delete cronjob routeros-version-checker
kubectl delete configmap routeros-version-checker-config
kubectl delete configmap routeros-version-checker-scripts
kubectl delete secret routeros-version-checker-secret
kubectl delete pvc routeros-version-data
```

## Advanced Configuration

### Using Existing ConfigMaps/Secrets

If you store the version in an existing ConfigMap:

1. Update `VERSION_FILE` in `configmap.yaml` to point to your ConfigMap mount
2. Add the ConfigMap as a volume in `cronjob.yaml`

### Adding Notifications

You can extend the Python script to send notifications (Slack, email, etc.) when a new version is detected:

```python
# Add to the run() method after triggering workflow
if self.trigger_workflow(access_token, latest_version):
    self.send_notification(f"New RouterOS version {latest_version} detected and workflow triggered!")
```

### Running in Different Environments

For different environments (dev, staging, prod), create separate:
- Namespaces
- ConfigMaps with environment-specific settings
- Secrets with environment-specific GitHub Apps

## Troubleshooting

### Enable Debug Logging

Add an environment variable to the CronJob:

```yaml
env:
- name: LOG_LEVEL
  value: "DEBUG"
```

Then update the Python script to use this:

```python
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
```

### Test Locally

You can test the script locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_APP_ID="your-app-id"
export GITHUB_PRIVATE_KEY="$(cat private-key.pem)"
export GITHUB_REPO="CalebSargeant/mikrotik-chr"
export WORKFLOW_ID="build-chr.yml"
export VERSION_FILE="/tmp/current_version.txt"

# Run the script
python scripts/check_routeros_version.py
```

## License

MIT License - See the main repository LICENSE file.

## Support

For issues or questions:
- Open an issue: [GitHub Issues](https://github.com/CalebSargeant/mikrotik-chr/issues)
- Check logs: `kubectl logs <pod-name>`
- Review GitHub App permissions and installation

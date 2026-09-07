# OCI VRRP failover helper.
#
# Runs as a container on each MikroTik CHR, alongside cloudflared. Listens on
# HTTP for a POST /promote from the RouterOS VRRP on-master hook and, when it
# arrives, calls the OCI API to reassign a configured floating secondary
# private IP to the local instance's primary VNIC.
#
# Why an extra container instead of doing this from RouterOS directly: the
# router's API doesn't include `oci-cli`, and shelling out from a hook script
# is brittle. The container packages the OCI CLI + a small Python listener so
# the hook script just does `/tool/fetch url=http://172.17.0.3:8080/promote`.
#
# Build: docker build -t oci-vrrp-failover .
# Run:   docker run -e FLOATING_PRIVATE_IP_OCID=... -e OCI_REGION=... -p 8080 oci-vrrp-failover
#
# Auth modes (set OCI_AUTH explicitly to pick, or let the helper auto-detect):
# - instance_principal: container reads VNIC + creds from the OCI metadata
#   service at 169.254.169.254. Cleanest — no static credentials anywhere.
#   Requires the container can reach link-local 169.254 from inside the
#   RouterOS container bridge (verify before relying on it).
# - api_key: container reads ~/.oci/config (typically a mounted file) and
#   uses the configured user OCID + key fingerprint + private key. Fallback
#   for when instance_principal isn't reachable from the container.

FROM python:3.13-slim

# python:3.13-slim has cve hits via system packages over time — keep this
# pinned to a major version + base image rebuild on schedule, dependabot
# bumps the base. Also bring in `curl` for HEALTHCHECK reliability without
# adding a Python subprocess for every probe.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# oci-cli pin is pinned in requirements.txt rather than hard-coded here so
# dependabot can bump it; the matching server.py runs against any 3.x cli.
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY server.py /app/server.py

# Internal HTTP listener for VRRP master-state webhook + container health.
EXPOSE 8080

# Restart-on-unhealthy: HEALTHCHECK + container runtime restart policy means
# a crashed listener gets cycled instead of silently leaving VRRP unable to
# trigger a failover. The probe hits /health on the same listener, so a hung
# server is also caught (not just a dead process).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:${LISTEN_PORT:-8080}/health || exit 1

# Run as non-root. oci-cli + the listener don't need root; binding to 8080
# (>1024) is fine for an unprivileged user.
RUN useradd --create-home --shell /bin/bash failover
USER failover

CMD ["python", "/app/server.py"]

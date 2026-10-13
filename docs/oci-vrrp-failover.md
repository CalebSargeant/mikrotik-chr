# OCI VRRP Failover Helper

A lightweight container solution for managing high-availability MikroTik CHR deployments on Oracle Cloud Infrastructure (OCI) using VRRP with automatic route table failover.

## Overview

The OCI VRRP Failover helper solves a critical limitation in OCI VCN route tables: they can have **only one default route per route table** (no ECMP). When deploying two egress routers in a VRRP HA pair, the route table can name only one as the next-hop. When that router fails, subnets lose egress connectivity until the route is manually updated.

This container automates that failover by listening for VRRP promotion events from RouterOS and updating OCI route tables to point at the new master's primary private IP.

## How It Works

On a VRRP `on-master` event from RouterOS, the newly promoted master MikroTik can trigger this listener:

```routeros
/tool/fetch url=http://172.17.0.3:8080/promote method=post keep-result=no
```

This calls the `/promote` endpoint, which:
1. Fetches each configured route table from OCI
2. Updates the failover destination rule's `network-entity-id` to point at this instance's primary private IP
3. Pushes the updated route table back to OCI
4. Returns success/failure status for each route table

Testing against eu-amsterdam-1 showed failover times of **~1.2 s API call / ~1.9 s visible** — well under the 30 s VRRP hold timer.

## Why Route Table Updates (Not Floating IPs)

The naive HA pattern moves a secondary private IP between VNICs. **This doesn't work on OCI** — the OCI `UpdatePrivateIp` API call doesn't support moving between VNICs. To "move" a secondary IP requires unassign + reassign (which creates a NEW private-ip OCID), breaking any route that referenced the old OCID.

The pattern that works: keep the route table's `network_entity_id` pointing at whichever **primary** private IP belongs to the active master. This container updates the route table on failover to maintain that invariant.

## Configuration

Configure the container via environment variables:

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `OCI_REGION` | ✓ | — | OCI region, e.g. `eu-amsterdam-1` |
| `LOCAL_PRIVATE_IP_OCID` | ✓ | — | This instance's **primary** private IP OCID — the next-hop the route table should point at when we're the master |
| `ROUTE_TABLE_OCIDS` | ✓ | — | Comma-separated list of route table OCIDs to update on promote (one per affected subnet, typically app + data) |
| `FAILOVER_DESTINATION` |   | `0.0.0.0/0` | The destination CIDR of the route rule whose next-hop we own |
| `OCI_AUTH` |   | `instance_principal` | `instance_principal` or `api_key`. Use `api_key` (and mount `~/.oci/config`) when the container can't reach the metadata service |
| `LISTEN_HOST` |   | `0.0.0.0` | HTTP listener bind address |
| `LISTEN_PORT` |   | `8080` | HTTP listener port |

## API Endpoints

### POST /promote
Fetch each route table, swap the `FAILOVER_DESTINATION` rule's `network-entity-id` to `LOCAL_PRIVATE_IP_OCID`, and update OCI.

**Response**: `{ok, results: [{route_table, ok, message}, ...]}` with status 200 if all route tables updated, 500 if any failed.

### GET /health
Configuration echo endpoint used by container `HEALTHCHECK`.

**Response**: `{ok, local_private_ip_ocid, route_table_ocids, failover_destination}`

## IAM Configuration

The `instance_principal` auth path requires the MikroTik VM's OCI dynamic group to carry a policy like:

```
Allow dynamic-group edge-prod-failover to use route-tables in compartment <prod>
Allow dynamic-group edge-prod-failover to read vcns in compartment <prod>
```

The `use route-tables` permission is sufficient — the container only reads and updates route tables, it doesn't delete them.

## Deployment

### Build the Container

```sh
cd dockerfiles/oci-vrrp-failover
docker build -t oci-vrrp-failover .
```

### Local Testing

Run with API key authentication (mounts your local `~/.oci/config`):

```sh
docker run --rm -p 8080:8080 \
  -e OCI_REGION=eu-amsterdam-1 \
  -e OCI_AUTH=api_key \
  -e LOCAL_PRIVATE_IP_OCID=ocid1.privateip... \
  -e ROUTE_TABLE_OCIDS=ocid1.routetable...,ocid1.routetable... \
  -v ~/.oci:/home/failover/.oci:ro \
  oci-vrrp-failover

# From another shell, trigger a promotion
curl -fsS -X POST http://localhost:8080/promote | jq
```

### Run Unit Tests

```sh
cd dockerfiles/oci-vrrp-failover
python3 -m unittest test_server.py -v
```

### Production Deployment on MikroTik CHR

See the consuming Terraform module in `CalebSargeant/infra:terraform/oci/modules/mikrotik/` — it adds a `routeros_container.failover_helper` resource alongside the existing cloudflared container.

The container runs as a RouterOS container, allowing RouterOS to trigger failover via HTTP requests to the local listener.

## References

- [OCI Reference Architecture: Provide highly available services across availability domains](https://docs.oracle.com/en/solutions/multi-region-high-availability/)
- [MikroTik RouterOS VRRP](https://help.mikrotik.com/docs/display/ROS/VRRP)
- [OCI Route Tables Documentation](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingroutetables.htm)

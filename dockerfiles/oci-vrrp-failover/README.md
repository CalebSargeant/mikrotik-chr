# oci-vrrp-failover

A tiny Python HTTP listener + `oci-cli` packaged as a container, intended
to run alongside `cloudflared` on each MikroTik CHR that's part of a
two-node VRRP HA pair on OCI.

## What problem it solves

OCI VCN route tables can have **only one default route per route table**
(no ECMP). If you have two egress routers, the route table can name only
one as the next-hop. When that router dies, the subnets that route
through it lose egress until something repoints the route.

This image is the "something." On the VRRP `on-master` hook from
RouterOS, the master MikroTik does:

```routeros
/tool/fetch url=http://172.17.0.3:8080/promote method=post keep-result=no
```

…which calls this listener, which calls the OCI API to update the named
route table(s) so the default route points at the new master's primary
private IP.

## Why a separate container

RouterOS doesn't include `oci-cli` and doesn't expose a general shell.
Packaging the OCI CLI + a small HTTP listener as a container is the same
pattern used by `cloudflared` on MikroTik CHRs — bring the dependency,
not try to bend RouterOS.

## Why route-table update and not a "floating private IP"

The naive HA pattern moves a secondary private IP between VNICs. **That
doesn't work on OCI:** `UpdatePrivateIp` doesn't take a `vnic_id`. To
"move" a secondary IP you have to unassign + reassign (creates a NEW
private-ip OCID), which breaks any route table that referenced the old
OCID.

The pattern that works is: keep the route table's `network_entity_id`
referring to whichever **primary** private IP belongs to the active
master, and update the route table on failover. That's what this image
does. A live smoke test against eu-amsterdam-1 saw the OCI control
plane reflect the change in **~1.2 s API call / ~1.9 s visible** —
total failover well under the 30 s budget.

## Configuration (environment variables)

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `OCI_REGION` | ✓ | — | OCI region, e.g. `eu-amsterdam-1` |
| `LOCAL_PRIVATE_IP_OCID` | ✓ | — | This instance's **primary** private IP OCID — the next-hop the route table should point at when we're the master |
| `ROUTE_TABLE_OCIDS` | ✓ | — | Comma-separated list of route table OCIDs to update on promote (one per affected subnet, typically app + data) |
| `FAILOVER_DESTINATION` |   | `0.0.0.0/0` | The destination CIDR of the route rule whose next-hop we own |
| `OCI_AUTH` |   | `instance_principal` | `instance_principal` or `api_key`. Use `api_key` (and mount `~/.oci/config`) when the container can't reach the metadata service |
| `LISTEN_HOST` |   | `0.0.0.0` | HTTP listener bind address |
| `LISTEN_PORT` |   | `8080` | HTTP listener port |

## Endpoints

- `POST /promote` — fetch each route table, swap the `FAILOVER_DESTINATION`
  rule's `network-entity-id` to `LOCAL_PRIVATE_IP_OCID`, PUT it back.
  Returns `{ok, results: [{route_table, ok, message}, ...]}`. Status
  200 if all route tables updated, 500 if any failed.
- `GET /health` — config echo, used by the container `HEALTHCHECK`.
  Returns `{ok, local_private_ip_ocid, route_table_ocids, failover_destination}`.

## IAM (OCI side)

The `instance_principal` auth path needs the MikroTik VM's dynamic
group to carry a policy roughly like:

```
Allow dynamic-group edge-prod-failover to use route-tables in compartment <prod>
Allow dynamic-group edge-prod-failover to read vcns in compartment <prod>
```

`use route-tables` is enough — `manage` would let the container delete the
table, which it doesn't need.

## Local build / test

```sh
# Unit tests (no OCI creds needed)
cd dockerfiles/oci-vrrp-failover
python3 -m unittest test_server.py -v

# Build image
docker build -t oci-vrrp-failover .

# Run with api_key auth (mount your local ~/.oci/config)
docker run --rm -p 8080:8080 \
  -e OCI_REGION=eu-amsterdam-1 \
  -e OCI_AUTH=api_key \
  -e LOCAL_PRIVATE_IP_OCID=ocid1.privateip... \
  -e ROUTE_TABLE_OCIDS=ocid1.routetable...,ocid1.routetable... \
  -v ~/.oci:/home/failover/.oci:ro \
  oci-vrrp-failover

# Trigger a promotion from another shell
curl -fsS -X POST http://localhost:8080/promote | jq
```

## Deploy (on MikroTik CHR via RouterOS container runtime)

See the consuming Terraform module in
`CalebSargeant/infra:terraform/oci/modules/mikrotik/` — adds a
`routeros_container.failover_helper` resource alongside the existing
cloudflared container.

## References

- [OCI Reference Architecture: Provide highly available services across availability domains](https://docs.oracle.com/en/solutions/multi-region-high-availability/)
- [MikroTik RouterOS VRRP](https://help.mikrotik.com/docs/display/ROS/VRRP)
- Companion design doc: `CalebSargeant/infra:docs/reference/oci-vrrp-ha-design.md`

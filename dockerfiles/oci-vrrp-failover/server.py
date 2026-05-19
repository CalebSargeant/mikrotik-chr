#!/usr/bin/env python3
"""
OCI VRRP failover helper.

Listens on HTTP for a POST /promote from the MikroTik RouterOS VRRP
on-master hook and, when it arrives, updates one or more OCI route
tables so the configured destination (typically `0.0.0.0/0`) now
next-hops to the local instance's primary private IP.

Why this and not "move a floating private IP between VNICs":

    OCI's UpdatePrivateIp API doesn't take a vnic_id — secondary
    private IPs can't be re-parented atomically. The HA pattern that
    *does* work, and that the design doc validates with a smoke test,
    is to update the route table's `network_entity_id` for the default
    route from r1's primary-private-IP OCID to r2's (or back). The
    route table is the single source of truth for "who's the current
    egress gateway."

The MikroTik runs in OCI as a VM; the container runs on the MikroTik via
RouterOS's container runtime (same pattern as cloudflared). When VRRP
state transitions r1 or r2 to master, the on-master hook does
`/tool/fetch url=http://172.17.0.3:8080/promote method=post` and this
listener performs the route-table update.

Environment:
    OCI_REGION                required. e.g. "eu-amsterdam-1".
    LOCAL_PRIVATE_IP_OCID     required. OCID of THIS instance's primary
                              private IP — what the route table should
                              next-hop to when we're the master.
    ROUTE_TABLE_OCIDS         required. Comma-separated list of route
                              table OCIDs to update on promote (one
                              per affected subnet — typically app + data).
    FAILOVER_DESTINATION      optional, default "0.0.0.0/0". The CIDR
                              of the route rule whose next-hop we own.
    OCI_AUTH                  optional. "instance_principal" (default)
                              or "api_key" — picks how oci-cli
                              authenticates. Use "api_key" when the
                              container can't reach the metadata service.
    LISTEN_HOST               optional, default "0.0.0.0".
    LISTEN_PORT               optional, default 8080.

Endpoints:
    POST /promote   reassign the configured route(s) to the local
                    primary private IP. Returns JSON
                    {ok, updated, errors}.
    GET  /health    liveness probe — 200 if the helper is up and
                    configured.

Logs to stdout; the container runtime is responsible for collection.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import socketserver
import subprocess
import sys
from typing import List, Tuple


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("oci-vrrp-failover")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or malformed."""


class FailoverHelper:
    """Stateful glue: holds config, knows how to update OCI route tables."""

    def __init__(
        self,
        local_private_ip_ocid: str,
        route_table_ocids: List[str],
        region: str,
        failover_destination: str,
        auth_mode: str,
    ) -> None:
        if not local_private_ip_ocid.startswith("ocid1.privateip."):
            raise ConfigError(
                f"LOCAL_PRIVATE_IP_OCID must start with ocid1.privateip., got {local_private_ip_ocid!r}"
            )
        if not route_table_ocids:
            raise ConfigError("ROUTE_TABLE_OCIDS must list at least one route table")
        for rt in route_table_ocids:
            if not rt.startswith("ocid1.routetable."):
                raise ConfigError(
                    f"every entry in ROUTE_TABLE_OCIDS must start with ocid1.routetable., got {rt!r}"
                )
        if auth_mode not in ("instance_principal", "api_key"):
            raise ConfigError(
                f"OCI_AUTH must be 'instance_principal' or 'api_key', got {auth_mode!r}"
            )

        self.local_private_ip_ocid = local_private_ip_ocid
        self.route_table_ocids = route_table_ocids
        self.region = region
        self.failover_destination = failover_destination
        self.auth_mode = auth_mode

    def _auth_args(self) -> List[str]:
        if self.auth_mode == "instance_principal":
            return ["--auth", "instance_principal"]
        # api_key path: oci-cli reads ~/.oci/config by default; nothing extra.
        return []

    def _run_oci(self, args: List[str]) -> subprocess.CompletedProcess:
        cmd = ["oci"] + args + ["--region", self.region] + self._auth_args()
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired as exc:
            logger.error("oci-cli timed out after 60s: %s", exc)
            return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr=str(exc))

    def _update_route_table(self, rt_ocid: str) -> Tuple[bool, str]:
        """Read-modify-write the rules list, updating the matching destination.

        OCI's UpdateRouteTable PUT semantics replace the entire `route-rules`
        list — we have to fetch the current state, modify the one rule, and
        send the full list back. Net effect for our use: change exactly one
        rule (the default route), leave any DRG/VPN routes alone.
        """
        get = self._run_oci([
            "network", "route-table", "get",
            "--rt-id", rt_ocid,
            "--query", 'data."route-rules"',
        ])
        if get.returncode != 0:
            return False, f"get failed: {get.stderr.strip()}"

        try:
            rules = json.loads(get.stdout)
        except json.JSONDecodeError as exc:
            return False, f"get returned malformed JSON: {exc}"
        if not isinstance(rules, list):
            return False, f"expected list of rules, got {type(rules).__name__}"

        # Mutate the single rule whose destination matches our target. If
        # the operator added more than one default-route rule (shouldn't
        # happen — OCI rejects duplicate destinations), we update the
        # first match and warn.
        matches = [r for r in rules if r.get("destination") == self.failover_destination]
        if not matches:
            return False, f"no rule with destination={self.failover_destination!r} found in {rt_ocid}"
        if len(matches) > 1:
            logger.warning(
                "%d rules match destination=%s on %s — updating first only",
                len(matches), self.failover_destination, rt_ocid,
            )

        target = matches[0]
        old_next_hop = target.get("network-entity-id")
        if old_next_hop == self.local_private_ip_ocid:
            logger.info(
                "rt %s already next-hops to local IP %s — no-op",
                rt_ocid, self.local_private_ip_ocid,
            )
            return True, "no-op (already current)"

        target["network-entity-id"] = self.local_private_ip_ocid
        target["description"] = (
            f"Internet egress via local primary IP (VRRP master) — "
            f"managed by oci-vrrp-failover, was {old_next_hop}"
        )

        # PUT the full modified list.
        upd = self._run_oci([
            "network", "route-table", "update",
            "--rt-id", rt_ocid,
            "--route-rules", json.dumps(rules),
            "--force",
        ])
        if upd.returncode != 0:
            return False, f"update failed: {upd.stderr.strip()}"
        return True, "updated"

    def promote(self) -> Tuple[bool, List[dict]]:
        """Reassign all configured route tables to the local primary IP."""
        logger.info(
            "promoting: %d route tables → local IP %s (auth=%s, region=%s)",
            len(self.route_table_ocids), self.local_private_ip_ocid,
            self.auth_mode, self.region,
        )
        results = []
        all_ok = True
        for rt in self.route_table_ocids:
            ok, message = self._update_route_table(rt)
            results.append({"route_table": rt, "ok": ok, "message": message})
            if not ok:
                all_ok = False
                logger.error("rt %s: %s", rt, message)
            else:
                logger.info("rt %s: %s", rt, message)
        return all_ok, results


def make_handler(helper: FailoverHelper) -> type:
    """Build a request handler class closed over the configured helper."""

    class Handler(http.server.BaseHTTPRequestHandler):
        # Override the default Apache-style logger so requests appear with
        # the same formatter as the rest of the helper's logs.
        def log_message(self, fmt: str, *args) -> None:  # noqa: A003 (stdlib name)
            logger.info("%s - %s", self.address_string(), fmt % args)

        def _json(self, status: int, body: dict) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802 (stdlib name)
            if self.path != "/promote":
                self._json(404, {"error": "not found"})
                return
            ok, results = helper.promote()
            self._json(200 if ok else 500, {"ok": ok, "results": results})

        def do_GET(self) -> None:  # noqa: N802 (stdlib name)
            if self.path == "/health":
                self._json(200, {
                    "ok": True,
                    "local_private_ip_ocid": helper.local_private_ip_ocid,
                    "route_table_ocids": helper.route_table_ocids,
                    "failover_destination": helper.failover_destination,
                })
                return
            self._json(404, {"error": "not found"})

    return Handler


def load_config() -> FailoverHelper:
    region = os.environ.get("OCI_REGION", "")
    if not region:
        raise ConfigError("OCI_REGION is required (e.g. eu-amsterdam-1)")

    local_ip = os.environ.get("LOCAL_PRIVATE_IP_OCID", "")
    if not local_ip:
        raise ConfigError(
            "LOCAL_PRIVATE_IP_OCID is required (this instance's primary "
            "private IP OCID — set per-router at deploy time)"
        )

    rt_raw = os.environ.get("ROUTE_TABLE_OCIDS", "")
    if not rt_raw:
        raise ConfigError(
            "ROUTE_TABLE_OCIDS is required (comma-separated list, one OCID "
            "per route table that should next-hop to the active master)"
        )
    rt_list = [s.strip() for s in rt_raw.split(",") if s.strip()]

    destination = os.environ.get("FAILOVER_DESTINATION", "0.0.0.0/0")
    auth_mode = os.environ.get("OCI_AUTH", "instance_principal")

    return FailoverHelper(local_ip, rt_list, region, destination, auth_mode)


def main() -> int:
    try:
        helper = load_config()
    except ConfigError as exc:
        logger.error("startup config error: %s", exc)
        return 2

    host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    port = int(os.environ.get("LISTEN_PORT", "8080"))

    logger.info(
        "oci-vrrp-failover listening on %s:%d (region=%s, dest=%s, "
        "local_ip=%s, route_tables=%d, auth=%s)",
        host, port, helper.region, helper.failover_destination,
        helper.local_private_ip_ocid, len(helper.route_table_ocids),
        helper.auth_mode,
    )
    with socketserver.TCPServer((host, port), make_handler(helper)) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("shutting down")
            return 0


if __name__ == "__main__":
    sys.exit(main())

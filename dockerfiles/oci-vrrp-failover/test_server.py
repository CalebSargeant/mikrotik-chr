"""Unit tests for the OCI VRRP failover helper.

What's covered:
- env-var parsing and validation (wrong OCID prefix is the most likely
  copy-paste mistake when bootstrapping a new deployment)
- the read-modify-write logic for route tables (the smoke test in the
  design doc confirmed the OCI API shape; these tests assert the
  helper preserves untouched rules and only swaps the matching one)
- HTTP route surface (/promote, /health, 404)

What's NOT covered:
- actual OCI API calls (network + creds — exercised by the design doc's
  end-to-end smoke test, which timed the real `oci network route-table
  update` against the prod compartment at ~1.2s API / ~1.9s visible)
- container HEALTHCHECK behaviour (covered by docker-build local test)
"""

from __future__ import annotations

import json
import socketserver
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

# server.py lives next to this file in the Docker build context; pytest is
# invoked with cwd=dockerfiles/oci-vrrp-failover (see CI workflow) so the
# relative import works.
import server  # noqa: E402


VALID_LOCAL_IP = "ocid1.privateip.oc1.eu-amsterdam-1.abqw2ljr6so6czsy275spwzlp73fhkxbmbqqvkcoo7k3aqonzpfdqfjbcquq"
PEER_IP = "ocid1.privateip.oc1.eu-amsterdam-1.abqw2ljrfqk45hotftgqis5dyczbbawgl3m6hr2o2wxthklbxqlbuadddxga"
VALID_RT_APP = "ocid1.routetable.oc1.eu-amsterdam-1.aaaaaaaapnqbav7zm6sge2he6rirutzoauj7odiultswzxufpmejgco64vga"
VALID_RT_DATA = "ocid1.routetable.oc1.eu-amsterdam-1.aaaaaaaavob5bz6ljitzyiwzgqw53cyha6jmfgcamz6mguohnonktom6umra"
DRG = "ocid1.drg.oc1.eu-amsterdam-1.aaaaaaaagwugj5kaivxokwwyudlfynxp7v43gspstpaufzflxyf53jxvprtq"


def _make_rules(default_next_hop: str) -> list:
    """Shape of the route-rules list that oci_core_route_table.app produces
    in prod today — used as the mock return value for `route-table get`."""
    return [
        {
            "cidr-block": None,
            "description": "FranklinHouse OCI Johannesburg (DRG peering)",
            "destination": "192.168.72.0/24",
            "destination-type": "CIDR_BLOCK",
            "network-entity-id": DRG,
            "route-type": "STATIC",
        },
        {
            "cidr-block": None,
            "description": "Internet egress via MikroTik (R1)",
            "destination": "0.0.0.0/0",
            "destination-type": "CIDR_BLOCK",
            "network-entity-id": default_next_hop,
            "route-type": "STATIC",
        },
        {
            "cidr-block": None,
            "description": "Sargeant on-prem network (MikroTik)",
            "destination": "192.168.19.0/24",
            "destination-type": "CIDR_BLOCK",
            "network-entity-id": DRG,
            "route-type": "STATIC",
        },
    ]


class TestFailoverHelperInit(unittest.TestCase):
    def test_accepts_valid_inputs(self):
        h = server.FailoverHelper(
            VALID_LOCAL_IP, [VALID_RT_APP, VALID_RT_DATA],
            "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
        )
        self.assertEqual(h.local_private_ip_ocid, VALID_LOCAL_IP)
        self.assertEqual(h.route_table_ocids, [VALID_RT_APP, VALID_RT_DATA])

    def test_rejects_local_ip_with_wrong_prefix(self):
        with self.assertRaises(server.ConfigError) as ctx:
            server.FailoverHelper(
                "ocid1.vnic.oc1...", [VALID_RT_APP],
                "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
            )
        self.assertIn("LOCAL_PRIVATE_IP_OCID", str(ctx.exception))

    def test_rejects_rt_ocid_with_wrong_prefix(self):
        with self.assertRaises(server.ConfigError) as ctx:
            server.FailoverHelper(
                VALID_LOCAL_IP, [VALID_RT_APP, "ocid1.subnet.oc1..."],
                "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
            )
        self.assertIn("ROUTE_TABLE_OCIDS", str(ctx.exception))

    def test_rejects_empty_rt_list(self):
        with self.assertRaises(server.ConfigError):
            server.FailoverHelper(
                VALID_LOCAL_IP, [],
                "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
            )

    def test_rejects_unknown_auth_mode(self):
        with self.assertRaises(server.ConfigError) as ctx:
            server.FailoverHelper(
                VALID_LOCAL_IP, [VALID_RT_APP],
                "eu-amsterdam-1", "0.0.0.0/0", "magic_beans",
            )
        self.assertIn("OCI_AUTH", str(ctx.exception))


class TestPromote(unittest.TestCase):
    """Read-modify-write semantics: helper must fetch existing rules,
    flip exactly the matching destination's next-hop, and PUT the full
    list back (preserving DRG/VPN routes)."""

    def setUp(self):
        self.helper = server.FailoverHelper(
            VALID_LOCAL_IP, [VALID_RT_APP],
            "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
        )

    def _mock_run(self, rules_before, update_ok=True):
        """Return a side_effect for subprocess.run that yields the rules
        on `get` and a success/failure on `update`."""
        def fn(cmd, **kwargs):
            if "get" in cmd:
                return MagicMock(returncode=0, stdout=json.dumps(rules_before), stderr="")
            if "update" in cmd:
                # Inspect the --route-rules payload the helper PUTs
                self.last_put = json.loads(cmd[cmd.index("--route-rules") + 1])
                if update_ok:
                    return MagicMock(returncode=0, stdout="", stderr="")
                return MagicMock(returncode=1, stdout="", stderr="ServiceError")
            return MagicMock(returncode=1, stdout="", stderr=f"unexpected cmd: {cmd}")
        return fn

    @patch("server.subprocess.run")
    def test_swaps_only_matching_destination(self, mock_run):
        rules = _make_rules(default_next_hop=PEER_IP)  # current: routes to peer
        mock_run.side_effect = self._mock_run(rules)

        ok, results = self.helper.promote()
        self.assertTrue(ok)

        # Default route now points at LOCAL_IP
        default = next(r for r in self.last_put if r["destination"] == "0.0.0.0/0")
        self.assertEqual(default["network-entity-id"], VALID_LOCAL_IP)

        # DRG routes left untouched
        drg_routes = [r for r in self.last_put if r["network-entity-id"] == DRG]
        self.assertEqual(len(drg_routes), 2)
        for r in drg_routes:
            self.assertIn(r["destination"], ["192.168.72.0/24", "192.168.19.0/24"])

    @patch("server.subprocess.run")
    def test_no_op_when_already_current(self, mock_run):
        rules = _make_rules(default_next_hop=VALID_LOCAL_IP)  # already routes to us
        mock_run.side_effect = self._mock_run(rules)
        ok, results = self.helper.promote()
        self.assertTrue(ok)
        # Should never have called update — only get
        update_calls = [c for c in mock_run.call_args_list if "update" in c.args[0]]
        self.assertEqual(len(update_calls), 0)
        self.assertIn("no-op", results[0]["message"])

    @patch("server.subprocess.run")
    def test_propagates_oci_update_failure(self, mock_run):
        rules = _make_rules(default_next_hop=PEER_IP)
        mock_run.side_effect = self._mock_run(rules, update_ok=False)
        ok, results = self.helper.promote()
        self.assertFalse(ok)
        self.assertIn("update failed", results[0]["message"])

    @patch("server.subprocess.run")
    def test_fails_when_no_matching_destination(self, mock_run):
        # Construct a rule set with NO default route
        rules = [r for r in _make_rules(default_next_hop=PEER_IP) if r["destination"] != "0.0.0.0/0"]
        mock_run.side_effect = self._mock_run(rules)
        ok, results = self.helper.promote()
        self.assertFalse(ok)
        self.assertIn("no rule with destination", results[0]["message"])

    @patch("server.subprocess.run")
    def test_partial_failure_across_multiple_route_tables(self, mock_run):
        """Two RTs: first updates fine, second fails. Overall result = False
        but successful one is reported as ok in the per-RT results."""
        helper = server.FailoverHelper(
            VALID_LOCAL_IP, [VALID_RT_APP, VALID_RT_DATA],
            "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
        )
        get_call = 0
        def fn(cmd, **kwargs):
            nonlocal get_call
            if "get" in cmd:
                get_call += 1
                return MagicMock(returncode=0, stdout=json.dumps(_make_rules(PEER_IP)), stderr="")
            if "update" in cmd:
                # First update OK, second fails
                rt = cmd[cmd.index("--rt-id") + 1]
                if rt == VALID_RT_APP:
                    return MagicMock(returncode=0, stdout="", stderr="")
                return MagicMock(returncode=1, stdout="", stderr="ServiceError")
            return MagicMock(returncode=1, stdout="", stderr="bad")
        mock_run.side_effect = fn

        ok, results = helper.promote()
        self.assertFalse(ok)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["ok"])
        self.assertFalse(results[1]["ok"])


class TestHttpRoutes(unittest.TestCase):
    """Round-trip the handler against an in-process server so we exercise
    the actual http.server dispatch, not a hand-rolled mock."""

    def setUp(self):
        helper = server.FailoverHelper(
            VALID_LOCAL_IP, [VALID_RT_APP, VALID_RT_DATA],
            "eu-amsterdam-1", "0.0.0.0/0", "instance_principal",
        )
        helper.promote = MagicMock(return_value=(True, [{"route_table": VALID_RT_APP, "ok": True, "message": "updated"}]))
        self.helper = helper

        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), server.make_handler(helper))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()

    def _request(self, method: str, path: str) -> tuple[int, dict]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_health_returns_200_with_config_echo(self):
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["local_private_ip_ocid"], VALID_LOCAL_IP)
        self.assertEqual(body["route_table_ocids"], [VALID_RT_APP, VALID_RT_DATA])
        self.assertEqual(body["failover_destination"], "0.0.0.0/0")

    def test_promote_returns_200_on_success(self):
        status, body = self._request("POST", "/promote")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.helper.promote.assert_called_once()

    def test_promote_returns_500_on_helper_failure(self):
        self.helper.promote.return_value = (False, [{"route_table": VALID_RT_APP, "ok": False, "message": "update failed: ServiceError"}])
        status, body = self._request("POST", "/promote")
        self.assertEqual(status, 500)
        self.assertFalse(body["ok"])

    def test_unknown_path_returns_404(self):
        status, _ = self._request("GET", "/nonexistent")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

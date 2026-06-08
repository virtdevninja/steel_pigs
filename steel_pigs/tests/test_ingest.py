#   Copyright 2026 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Tests for POST /v1/servers and POST /v1/servers/<n>/switches."""

import json
import os
import unittest
from unittest.mock import patch

from steel_pigs.webapp import create_app

API_TOKEN = "ingest-test-token"


def _valid_server_payload(**overrides):
    """A complete, valid request body for POST /v1/servers."""
    payload = {
        "server_number": 999001,
        "primary_ip": "10.0.0.10",
        "primary_gw": "10.0.0.1",
        "primary_nm": "255.255.255.0",
        "primary_mac": "aa:bb:cc:00:00:01",
        "hostname": "ingest-1",
        "dns_server_primary": "8.8.8.8",
        "bootstrapped": False,
        "boot_os": "Ubuntu",
        "boot_os_version": "22.04",
        "boot_profile": "Standard",
        "boot_status": "kicking",
        "operational_status": "provisioning",
        "ntp_server": "pool.ntp.org",
    }
    payload.update(overrides)
    return payload


class _IngestTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env_patcher = patch.dict(os.environ, {"STEEL_PIGS_API_TOKEN": API_TOKEN})
        cls._env_patcher.start()
        cls.app = create_app(config_overrides={"TESTING": True})

    @classmethod
    def tearDownClass(cls):
        cls._env_patcher.stop()

    def setUp(self):
        self.client = self.app.test_client()

    def _auth(self):
        return {"Authorization": f"Bearer {API_TOKEN}"}


class TestCreateServer(_IngestTestBase):
    # --- auth -------------------------------------------------------------

    def test_unauthenticated_returns_401(self):
        rv = self.client.post("/v1/servers", json=_valid_server_payload())
        self.assertEqual(rv.status_code, 401)

    # --- happy path -------------------------------------------------------

    def test_valid_payload_returns_201_and_created_dict(self):
        payload = _valid_server_payload(server_number=999100)
        rv = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(rv.status_code, 201)
        body = json.loads(rv.data)
        self.assertEqual(body["server_number"], 999100)
        self.assertEqual(body["hostname"], "ingest-1")
        # id should be populated server-side.
        self.assertIn("id", body)

    def test_created_server_is_readable_via_get(self):
        payload = _valid_server_payload(server_number=999101, hostname="readback")
        self.client.post("/v1/servers", json=payload, headers=self._auth())
        fetched = self.app.extensions["steel_pigs"].server_data.get_server_by_number(999101)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["hostname"], "readback")

    # --- validation -------------------------------------------------------

    def test_missing_required_field_returns_400(self):
        payload = _valid_server_payload(server_number=999102)
        del payload["hostname"]
        rv = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(rv.status_code, 400)

    def test_invalid_boot_status_returns_400(self):
        payload = _valid_server_payload(server_number=999103, boot_status="garbage")
        rv = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(rv.status_code, 400)

    def test_invalid_operational_status_returns_400(self):
        payload = _valid_server_payload(server_number=999104, operational_status="bogus")
        rv = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(rv.status_code, 400)

    def test_unknown_field_returns_400(self):
        payload = _valid_server_payload(server_number=999105)
        payload["totally_made_up_field"] = "x"
        rv = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(rv.status_code, 400)

    # --- duplicates -------------------------------------------------------

    def test_duplicate_server_number_returns_409(self):
        payload = _valid_server_payload(server_number=999200)
        first = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/v1/servers", json=payload, headers=self._auth())
        self.assertEqual(second.status_code, 409)


class TestAddSwitch(_IngestTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create one server for the switch tests to target.
        cls.app.test_client().post(
            "/v1/servers",
            json=_valid_server_payload(server_number=888001, hostname="switch-host"),
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )

    def test_unauthenticated_returns_401(self):
        rv = self.client.post(
            "/v1/servers/888001/switches",
            json={"switch_name": "sw-1", "switch_port": "1"},
        )
        self.assertEqual(rv.status_code, 401)

    def test_valid_payload_returns_201(self):
        rv = self.client.post(
            "/v1/servers/888001/switches",
            json={"switch_name": "sw-A", "switch_port": "1"},
            headers=self._auth(),
        )
        self.assertEqual(rv.status_code, 201)
        body = json.loads(rv.data)
        self.assertEqual(body["server_number"], 888001)
        self.assertEqual(body["switch_name"], "sw-A")
        self.assertEqual(body["switch_port"], "1")

    def test_missing_switch_name_returns_400(self):
        rv = self.client.post(
            "/v1/servers/888001/switches",
            json={"switch_port": "5"},
            headers=self._auth(),
        )
        self.assertEqual(rv.status_code, 400)

    def test_missing_switch_port_returns_400(self):
        rv = self.client.post(
            "/v1/servers/888001/switches",
            json={"switch_name": "sw-X"},
            headers=self._auth(),
        )
        self.assertEqual(rv.status_code, 400)

    def test_nonexistent_server_returns_404(self):
        rv = self.client.post(
            "/v1/servers/123456789/switches",
            json={"switch_name": "sw-9", "switch_port": "9"},
            headers=self._auth(),
        )
        self.assertEqual(rv.status_code, 404)


if __name__ == "__main__":
    unittest.main()

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

import json
import logging
import os
import unittest
from unittest.mock import patch

from steel_pigs.tests import seed_sql_plugin
from steel_pigs.webapp import create_app

API_TOKEN = "audit-test-token"

AUDIT_LOGGER_NAME = "steel_pigs.audit"


class CaptureHandler(logging.Handler):
    """Collect every audit record (already JSON-formatted by audit.emit)."""

    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        self.events.append(json.loads(record.getMessage()))


class TestAuditLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env_patcher = patch.dict(os.environ, {"STEEL_PIGS_API_TOKEN": API_TOKEN})
        cls._env_patcher.start()
        cls.app = create_app(config_overrides={"TESTING": True})
        seed_sql_plugin(cls.app.extensions["steel_pigs"].server_data)

    @classmethod
    def tearDownClass(cls):
        cls._env_patcher.stop()

    def setUp(self):
        self.client = self.app.test_client()
        self.capture = CaptureHandler()
        self.audit_logger = logging.getLogger(AUDIT_LOGGER_NAME)
        self.audit_logger.addHandler(self.capture)
        self.audit_logger.setLevel(logging.INFO)

    def tearDown(self):
        self.audit_logger.removeHandler(self.capture)

    # --- mutation events ---------------------------------------------------

    def test_set_boot_status_emits_audit_event(self):
        self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "provision"},
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )
        self.assertEqual(len(self.capture.events), 1)
        ev = self.capture.events[0]
        self.assertEqual(ev["action"], "set_boot_status")
        self.assertEqual(ev["resource"], "server/555121")
        self.assertEqual(ev["actor"], "env-token")
        self.assertEqual(ev["after"], {"boot_status": "provision"})
        self.assertIn("boot_status", ev["before"])
        self.assertIsNotNone(ev["timestamp"])
        self.assertIsNotNone(ev["request_id"])

    def test_set_boot_os_emits_audit_event(self):
        self.client.post(
            "/v1/update/os",
            json={"server_number": 555121, "boot_os": "Fedora"},
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )
        self.assertEqual(len(self.capture.events), 1)
        ev = self.capture.events[0]
        self.assertEqual(ev["action"], "set_boot_os")
        self.assertEqual(ev["after"], {"boot_os": "Fedora"})

    def test_set_opstatus_emits_audit_event(self):
        self.client.post(
            "/v1/update/opstatus",
            json={"server_number": 555121, "opstatus": "kicking"},
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )
        self.assertEqual(len(self.capture.events), 1)
        ev = self.capture.events[0]
        self.assertEqual(ev["action"], "set_operational_status")
        self.assertEqual(ev["after"], {"operational_status": "kicking"})

    # --- auth-failure events ----------------------------------------------

    def test_unauthenticated_emits_auth_failed(self):
        self.client.post("/v1/update/status", json={"server_number": 555121})
        self.assertEqual(len(self.capture.events), 1)
        ev = self.capture.events[0]
        self.assertEqual(ev["action"], "auth_failed")
        self.assertEqual(ev["resource"], "/v1/update/status")
        self.assertIsNone(ev["actor"])

    def test_wrong_token_emits_auth_failed(self):
        self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "provision"},
            headers={"Authorization": "Bearer wrong"},
        )
        self.assertEqual(len(self.capture.events), 1)
        self.assertEqual(self.capture.events[0]["action"], "auth_failed")

    # --- request-id propagation -------------------------------------------

    def test_request_id_from_header_is_recorded(self):
        self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "online"},
            headers={
                "Authorization": f"Bearer {API_TOKEN}",
                "X-Request-ID": "rid-from-upstream-7",
            },
        )
        self.assertEqual(self.capture.events[0]["request_id"], "rid-from-upstream-7")

    # --- log-injection defense --------------------------------------------

    def test_newline_in_body_value_is_stripped(self):
        # CWE-117: a value containing CR/LF could be used to forge log
        # entries if it landed verbatim in the output. Inject via the
        # JSON body (Werkzeug refuses CR/LF in headers, so the HTTP layer
        # already blocks that vector). Verify audit._strip_control
        # strips them from the after-state we record.
        self.client.post(
            "/v1/update/os",
            json={"server_number": 555121, "boot_os": "Fedora\r\nFORGED ENTRY"},
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )
        recorded = self.capture.events[0]["after"]["boot_os"]
        self.assertNotIn("\n", recorded)
        self.assertNotIn("\r", recorded)
        self.assertEqual(recorded, "FedoraFORGED ENTRY")


class TestStripControl(unittest.TestCase):
    """Direct coverage of audit._strip_control."""

    def test_strips_newlines_in_string(self):
        from steel_pigs.audit import _strip_control

        self.assertEqual(_strip_control("a\nb\rc"), "abc")

    def test_recurses_into_dicts(self):
        from steel_pigs.audit import _strip_control

        self.assertEqual(_strip_control({"k": "a\nb"}), {"k": "ab"})

    def test_recurses_into_lists(self):
        from steel_pigs.audit import _strip_control

        self.assertEqual(_strip_control(["a\nb", "c"]), ["ab", "c"])

    def test_passes_through_non_strings(self):
        from steel_pigs.audit import _strip_control

        self.assertIsNone(_strip_control(None))
        self.assertEqual(_strip_control(42), 42)
        self.assertEqual(_strip_control(True), True)


if __name__ == "__main__":
    unittest.main()

#   Copyright 2015 Michael Rice <michael@michaelrice.org>
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

API_TOKEN = "test-token-12345"


class _RecordingHandler(logging.Handler):
    """Collect every log record reaching this handler."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class TestFlaskApp(unittest.TestCase):
    """Open / unauthenticated routes."""

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

    def test_healthz(self):
        rv = self.client.get("/healthz")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.get_json(), {"status": "ok"})

    def test_readyz_when_plugins_loaded(self):
        rv = self.client.get("/readyz")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.get_json(), {"status": "ok"})

    def test_hardware_fails_with_422_when_missing_prop(self):
        rv = self.client.get("/hardware")
        self.assertEqual(rv.status_code, 422)

    def test_hardware_serves_proper_ipxe_script(self):
        rv = self.client.get("/hardware?manufacturer=Dell%20&product=r%20810")
        self.assertIn(b"r810", rv.data)

    def test_versions_json(self):
        rv = self.client.get("/versions")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.content_type, "application/json")

    def test_get_versions_ipxe(self):
        rv = self.client.get("/versions/ipxe")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"set latest_version 4", rv.data)

    def test_hardware_log_repr_escapes_newline_in_query_arg(self):
        # CWE-117 defense: the route logs dict(request.args) via
        # _log_safe, so a URL-encoded newline lands as the
        # two-character escape `\n` in the captured log message instead
        # of a real newline that could forge a second log line.
        handler = _RecordingHandler()
        logger = logging.getLogger("steel_pigs.webapp")
        previous_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            rv = self.client.get("/hardware?manufacturer=Dell&product=r810%0AFORGED")
            self.assertEqual(rv.status_code, 200)
            hw_msgs = [
                r.getMessage() for r in handler.records if "Request to /hardware" in r.getMessage()
            ]
            self.assertEqual(len(hw_msgs), 1)
            msg = hw_msgs[0]
            self.assertNotIn("\n", msg)
            self.assertIn("\\n", msg)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)


class TestV1MutationRoutes(unittest.TestCase):
    """POST /v1/update/* with bearer auth."""

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

    def _auth_headers(self):
        return {"Authorization": f"Bearer {API_TOKEN}"}

    # --- /v1/update/status -------------------------------------------------

    def test_status_unauthenticated_returns_401(self):
        rv = self.client.post("/v1/update/status", json={"server_number": 555121})
        self.assertEqual(rv.status_code, 401)
        self.assertTrue(rv.headers["WWW-Authenticate"].startswith("Bearer"))

    def test_status_wrong_token_returns_401(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "provision"},
            headers={"Authorization": "Bearer wrong"},
        )
        self.assertEqual(rv.status_code, 401)

    def test_status_success(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "provision"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data)["operation"], "success")

    def test_status_missing_server_number_returns_422(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"boot_status": "provision"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 422)

    def test_status_unknown_value_returns_422(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "garbage"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 422)

    # --- /v1/update/os ----------------------------------------------------

    def test_os_unauthenticated_returns_401(self):
        rv = self.client.post(
            "/v1/update/os",
            json={"server_number": 555121, "boot_os": "Fedora"},
        )
        self.assertEqual(rv.status_code, 401)

    def test_os_success(self):
        rv = self.client.post(
            "/v1/update/os",
            json={"server_number": 555121, "boot_os": "Fedora"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data)["operation"], "success")

    def test_os_missing_field_returns_422(self):
        rv = self.client.post(
            "/v1/update/os",
            json={"server_number": 555121},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 422)

    # --- /v1/update/opstatus ----------------------------------------------

    def test_opstatus_unauthenticated_returns_401(self):
        rv = self.client.post("/v1/update/opstatus", json={"server_number": 555121})
        self.assertEqual(rv.status_code, 401)

    def test_opstatus_success(self):
        rv = self.client.post(
            "/v1/update/opstatus",
            json={"server_number": 555121, "opstatus": "kicking"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data)["operation"], "success")

    def test_opstatus_unknown_value_returns_422(self):
        rv = self.client.post(
            "/v1/update/opstatus",
            json={"server_number": 555121, "opstatus": "garbage"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 422)


if __name__ == "__main__":
    unittest.main()

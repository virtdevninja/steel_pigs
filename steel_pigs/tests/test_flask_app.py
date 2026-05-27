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
import os
import unittest
from unittest.mock import patch

from steel_pigs.tests import seed_sql_plugin
from steel_pigs.webapp import create_app

API_TOKEN = "test-token-12345"


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

    def test_hardware_fails_with_412_when_missing_prop(self):
        rv = self.client.get("/hardware")
        self.assertEqual(rv.status_code, 412)

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


class TestLegacyMutationRoutes(unittest.TestCase):
    """GET /update/* used to mutate state; now returns 405 -> POST /v1/."""

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

    def test_legacy_status_returns_405(self):
        rv = self.client.get("/update/status?server_number=555121&boot_status=provision")
        self.assertEqual(rv.status_code, 405)
        self.assertEqual(rv.headers["Allow"], "POST")
        self.assertIn("/v1/update/status", rv.get_json()["message"])

    def test_legacy_os_returns_405(self):
        rv = self.client.get("/update/os?server_number=555121&boot_os=Fedora")
        self.assertEqual(rv.status_code, 405)
        self.assertEqual(rv.headers["Allow"], "POST")

    def test_legacy_opstatus_returns_405(self):
        rv = self.client.get("/update/opstatus?server_number=555121&opstatus=kicking")
        self.assertEqual(rv.status_code, 405)
        self.assertEqual(rv.headers["Allow"], "POST")


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
        self.assertEqual(rv.headers["WWW-Authenticate"], "Bearer")

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

    def test_status_missing_server_number_returns_400(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"boot_status": "provision"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 400)

    def test_status_unknown_value_returns_400(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "garbage"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 400)

    def test_status_normalises_case(self):
        rv = self.client.post(
            "/v1/update/status",
            json={"server_number": 555121, "boot_status": "ONLINE"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data)["status_set"], "online")

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

    def test_os_missing_field_returns_400(self):
        rv = self.client.post(
            "/v1/update/os",
            json={"server_number": 555121},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 400)

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

    def test_opstatus_unknown_value_returns_400(self):
        rv = self.client.post(
            "/v1/update/opstatus",
            json={"server_number": 555121, "opstatus": "garbage"},
            headers=self._auth_headers(),
        )
        self.assertEqual(rv.status_code, 400)


if __name__ == "__main__":
    unittest.main()

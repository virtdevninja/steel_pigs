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

"""Pin the auto-generated OpenAPI 3 spec.

Spec drift across PRs is the main thing this layer of tooling is
supposed to prevent; CI re-validating the doc against the OpenAPI 3
schema on every change is the enforcement.
"""

import unittest

from openapi_spec_validator import validate

from steel_pigs.webapp import create_app


class TestOpenAPISpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_overrides={"TESTING": True})

    def setUp(self):
        self.client = self.app.test_client()

    def test_spec_endpoint_serves_valid_openapi_3(self):
        rv = self.client.get("/openapi.json")
        self.assertEqual(rv.status_code, 200)
        spec = rv.get_json()
        validate(spec)
        self.assertEqual(spec["openapi"][0], "3")
        self.assertEqual(spec["info"]["title"], "Steel PIGS")

    def test_swagger_ui_is_served(self):
        rv = self.client.get("/docs")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"swagger", rv.data.lower())

    def test_security_scheme_is_published(self):
        spec = self.client.get("/openapi.json").get_json()
        self.assertIn("BearerAuth", spec["components"]["securitySchemes"])
        self.assertEqual(
            spec["components"]["securitySchemes"]["BearerAuth"]["type"],
            "http",
        )
        self.assertEqual(
            spec["components"]["securitySchemes"]["BearerAuth"]["scheme"],
            "bearer",
        )

    def test_v1_mutation_routes_require_bearer_auth_in_spec(self):
        spec = self.client.get("/openapi.json").get_json()
        for path in (
            "/v1/update/status",
            "/v1/update/os",
            "/v1/update/opstatus",
            "/v1/servers",
            "/v1/servers/{server_number}/switches",
        ):
            op = spec["paths"][path]["post"]
            self.assertIn(
                "security",
                op,
                f"{path} is missing a security requirement",
            )
            self.assertIn(
                {"BearerAuth": []},
                op["security"],
                f"{path} doesn't list BearerAuth",
            )

    def test_read_routes_do_not_require_auth_in_spec(self):
        spec = self.client.get("/openapi.json").get_json()
        for path in ("/healthz", "/readyz", "/pxe", "/hardware", "/versions"):
            op = spec["paths"][path]["get"]
            # Open routes should either have no `security` key, or an
            # explicit empty list. Either is "no auth required."
            sec = op.get("security", [])
            self.assertFalse(
                any(s for s in sec),
                f"{path} should not require auth but has {sec!r}",
            )


if __name__ == "__main__":
    unittest.main()

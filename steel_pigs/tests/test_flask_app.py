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

from steel_pigs.tests import PigTests

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import steel_pigs.webapp


class TestFlaskApp(PigTests):

    @classmethod
    def setUpClass(cls):
        steel_pigs.webapp._add_server_data(cls._create_entry_data())

    def setUp(self):
        steel_pigs.webapp.app.config['TESTING'] = True
        self.app = steel_pigs.webapp.app.test_client()

    def test_hardware_fails_with_412_when_missing_prop(self):
        rv = self.app.get("/hardware")
        self.assertEqual(rv.status_code, 412)

    def test_hardware_serves_proper_ipxe_script(self):
        rv = self.app.get("/hardware?manufacturer=Dell%20&product=r%20810")
        self.assertIn("r810", rv.data)

    def test_versions_json(self):
        rv = self.app.get("/versions")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.content_type, "application/json")

    def test_set_operational_status_fails_when_missing_required_args(self):
        rv = self.app.get("/update/opstatus")
        self.assertEqual(rv.status_code, 412)

    def test_set_operational_status_works_as_expected(self):
        rv = self.app.get("/update/opstatus?server_number=555121&opstatus=kicking")
        self.assertEqual(rv.content_type, "application/json")
        data = json.loads(rv.data)
        self.assertEqual(data["operation"], "success")

    def test_set_boot_os_fails_with_missing_props(self):
        rv = self.app.get("/update/os")
        self.assertEqual(rv.status_code, 412)

    def test_set_boot_os_success_with_valid_params(self):
        rv = self.app.get("/update/os?boot_os=Fedora&server_number=555121")
        self.assertEqual(rv.content_type, "application/json")
        data = json.loads(rv.data)
        self.assertEqual(data["operation"], "success")

    def test_update_boot_status_fails_with_missing_params(self):
        rv = self.app.get("/update/status")
        self.assertEqual(rv.status_code, 412)

    def test_update_boot_status_success_with_valid_params(self):
        rv = self.app.get("/update/status?server_number=555121&boot_status=provision")
        self.assertEqual(rv.content_type, "application/json")
        data = json.loads(rv.data)
        self.assertEqual(data["operation"], "success")

    def test_get_versions_ipxe(self):
        rv = self.app.get("/versions/ipxe")
        self.assertEqual(rv.status_code, 200)
        self.assertIn("set latest_version 4", rv.data)

if __name__ == '__main__':
    unittest.main()

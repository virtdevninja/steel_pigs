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

import os
import unittest

from tests import PigTests

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import steel_pigs


class TestFlaskApp(PigTests):

    def setUp(self):
        steel_pigs.app.config['TESTING'] = True
        self.app = steel_pigs.app.test_client()

    def test_hardware_fails_with_412_when_missing_prop(self):
        rv = self.app.get("/hardware")
        self.assertEqual(rv.status_code, 412)

    def test_hardware_serves_proper_ipxe_script(self):
        rv = self.app.get("/hardware?manufacturer=Dell%20&product=r%20810")
        self.assertIn("r810", rv.data)


if __name__ == '__main__':
    unittest.main()

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

import unittest

from sqlalchemy.exc import IntegrityError

from tests import PigTests

class TestSQL(PigTests):

    def test_duplicate_server_number_not_allowed(self):
        with self.assertRaises(IntegrityError):
            self._add_entry()

    def test_find_by_name(self):
        name = "hogzilla"
        entry = self.sql.get_server_by_name(name)
        self.assertEqual(name, entry["hostname"])

    def test_find_by_number(self):
        number = 555121
        entry = self.sql.get_server_by_number(number)
        self.assertEqual(number, entry["server_number"])

    def test_find_by_number_works_using_string(self):
        number = "555121"
        entry = self.sql.get_server_by_number(number)
        self.assertEqual(int(number), entry["server_number"])

    def test_find_server_by_mac(self):
        mac = "00:11:22:33:44:55"
        entry = self.sql.get_server_by_mac(mac)
        self.assertEqual(mac, entry["primary_mac"])

    def test_no_results_return_none(self):
        name = "badname"
        entry = self.sql.get_server_by_name(name)
        self.assertIsNone(entry)

    def test_update_boot_status_by_server_number(self):
        number = 555121
        self.sql.set_boot_status(number, "Done")
        entry = self.sql.get_server_by_number(number)
        self.assertEqual("Done", entry["boot_status"])

    def test_update_boot_os_by_server_number(self):
        number = 555121
        self.sql.set_boot_os(number, "Gentoo")
        entry = self.sql.get_server_by_number(number)
        self.assertEqual("Gentoo", entry["boot_os"])

    def test_update_operational_status_by_server_number(self):
        number = 555121
        self.sql.set_operational_status(number, "Production")
        entry = self.sql.get_server_by_number(number)
        self.assertEqual("Production", entry["operational_status"])

    def test_find_server_by_switch(self):
        switch_name = "Switch 01"
        switch_port = "1"
        entry = self.sql.get_server_by_switch(switch_name, switch_port)
        self.assertEqual(555121, entry["server_number"])

if __name__ == '__main__':
    unittest.main()

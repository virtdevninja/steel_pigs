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

import logging
import unittest

from sqlalchemy.exc import IntegrityError

from plugins.providers.sql import ServerDataModel, SwitchInfo
from plugins.providers.sql import SQL
from tests import Config
from tests import PigTests
config = Config()

class TestSQL(PigTests):

    @classmethod
    def setUpClass(cls):
        cls.sql = SQL(config)
        logging.basicConfig()
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
        cls._add_entry()

    @classmethod
    def _add_entry(cls):
        server_entry = ServerDataModel()
        server_entry.boot_os = "Ubuntu"
        server_entry.boot_os_version = "14.04.2"
        server_entry.boot_profile = "Unknown"
        server_entry.boot_status = "Kicking"
        server_entry.bootstrapped = False
        server_entry.dns_domain_name = "rpc.local"
        server_entry.dns_server_primary = "8.8.8.8"
        server_entry.hostname = "hogzilla"
        server_entry.operational_status = "Provisioning"
        server_entry.primary_gw = "10.12.1.1"
        server_entry.primary_ip = "10.12.1.10"
        server_entry.primary_mac = "00:11:22:33:44:55"
        server_entry.primary_nm = "255.255.255.0"
        server_entry.server_number = 555121
        cls.sql.create_entry(server_entry)

        switch_entry = SwitchInfo()
        switch_entry.server_number = 555121
        switch_entry.switch_name = "Switch 01"
        switch_entry.switch_port = "1"
        cls.sql.add_switch_entry(switch_entry)

        switch_entry1 = SwitchInfo()
        switch_entry1.server_number = 555121
        switch_entry1.switch_name = "Switch 01"
        switch_entry1.switch_port = "2"
        cls.sql.add_switch_entry(switch_entry1)

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

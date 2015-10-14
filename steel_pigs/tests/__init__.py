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

from steel_pigs.plugins.providers.sql import ServerDataModel, SwitchInfo
from steel_pigs.plugins.providers.sql import SQL

config = {'engine': "sqlite:///:memory:"}


class PigTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sql = SQL(config)
        logging.basicConfig()
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
        cls._add_entry()

    @classmethod
    def _add_entry(cls):
        data = cls._create_entry_data()
        server_data = data["server_data"]
        switch_info = data["switch_info"]
        cls.sql.create_entry(server_data)
        for switch in switch_info:
            cls.sql.add_switch_entry(switch)

    @classmethod
    def _create_entry_data(cls):
        data = {}
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
        data["server_data"] = server_entry
        switch_entry = SwitchInfo()
        switch_entry.server_number = 555121
        switch_entry.switch_name = "Switch 01"
        switch_entry.switch_port = "1"
        switch_entry1 = SwitchInfo()
        switch_entry1.server_number = 555121
        switch_entry1.switch_name = "Switch 01"
        switch_entry1.switch_port = "2"
        data["switch_info"] = [switch_entry, switch_entry1]
        return data

    def setUp(self):
        logging.basicConfig()
        log = logging.getLogger()
        log.setLevel(logging.DEBUG)

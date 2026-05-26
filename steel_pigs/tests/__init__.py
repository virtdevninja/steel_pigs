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

from steel_pigs.plugins.providers.sql import SQL, ProvisionZone, ServerDataModel, SwitchInfo


def make_seed_data():
    """Build a fresh set of ORM objects for an in-memory SQL plugin."""
    p_zone = ProvisionZone(
        provision_img_host="10.12.1.10",
        provision_mirror_host="10.12.1.10",
        zone_name="DFW1",
    )
    server = ServerDataModel(
        boot_os="Ubuntu",
        boot_os_version="14.04.2",
        boot_profile="Unknown",
        boot_status="Kicking",
        bootstrapped=False,
        dns_domain_name="rpc.local",
        dns_server_primary="8.8.8.8",
        hostname="hogzilla",
        operational_status="Provisioning",
        primary_gw="10.12.1.1",
        primary_ip="10.12.1.10",
        primary_mac="00:11:22:33:44:55",
        primary_nm="255.255.255.0",
        server_number=555121,
        ntp_server="10.12.1.10",
        provision_zone=p_zone,
    )
    switches = [
        SwitchInfo(server_number=555121, switch_name="Switch 01", switch_port="1"),
        SwitchInfo(server_number=555121, switch_name="Switch 01", switch_port="2"),
    ]
    return {"server_data": server, "switch_info": switches}


def seed_sql_plugin(sql_plugin):
    data = make_seed_data()
    sql_plugin.create_entry(data["server_data"])
    for switch in data["switch_info"]:
        sql_plugin.add_switch_entry(switch)


class PigTests(unittest.TestCase):
    """Base class for tests that exercise the SQL plugin in isolation."""

    @classmethod
    def setUpClass(cls):
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        cls.sql = SQL({"engine": "sqlite:///:memory:"})
        seed_sql_plugin(cls.sql)

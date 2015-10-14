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

from .formatterbase import DataFormatterProvider


class NoFormatProvider(DataFormatterProvider):

    def __init__(self, config):
        pass

    def format_port(self, port):
        """
        Returns the port because we dont need formatting done.

        :param port:
        :return:
        """
        return port

    def format_switch(self, switch):
        """
        Returns the switch because we dont need formatting done.

        :param switch:
        :return:
        """
        return switch

    def format_mac(self, mac):
        """
        Returns the mac because we are not formatting anything

        :param mac:
        :return:
        """
        return mac

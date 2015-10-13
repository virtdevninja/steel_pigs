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

import abc


class DataFormatterProvider(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def format_switch(self, switch):
        """
        Returns a formatted version of the switch.

        :param switch:
        :return:
        """
        return

    @abc.abstractmethod
    def format_port(self, port):
        """
        Returns a formatted version of the port

        :param port:
        :return:
        """
        return

    @abc.abstractmethod
    def format_mac(self, mac):
        """
        Returns a formatted version of the mac address.

        :param mac:
        :return:
        """
        return

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

class ProviderPluginBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_server_by_name(self, name):
        """
        Retrieve data about a server by name and return an object that
        represents it.
        """
        return

    @abc.abstractmethod
    def get_server_by_number(self, number):
        """
        Retrieve data about a server and return a dict that
        represents it.

        :param number: The device number or asset number of a given server
        :return: returns a dict that represents a server
        """
        return

    @abc.abstractmethod
    def get_server_by_mac(self, mac):
        """
        Retrieve data about a server and return a dict that
        represents it.

        :param mac: Any MAC address from a given server
        :return: returns a dict that represents a server
        """
        return

    @abc.abstractmethod
    def get_server_by_switch(self, switch_name, switch_port):
        """
        Retrieve data about a server and return a dict that
        represents it.

        :param switch_name: The name of a switch where a server is plugged in
        :param switch_port: The port name/number the server is plugged in
        :return: returns a dict that represents a server
        """
        return

    @abc.abstractmethod
    def set_boot_status(self, server_number, boot_status):
        """
        Sets the boot status of a server to the given status

        :param server_number: The device number of a given server
        :param boot_status: The status to set
        :return: void method
        """
        return

    @abc.abstractmethod
    def set_boot_os(self, server_number, boot_os):
        """
        Changes the boot_os to another value to change boot
        behaviour

        :param server_number: The device number of a given server
        :param boot_os: The operating system value for the device
        :return: void method
        """
        return

    @abc.abstractmethod
    def set_operational_status(self, server_number, operational_status):
        """
        Changes the operational status of a device to a given status.
        This could be from provisioning to production, or vice versa.

        :param server_number: The device number of a given server
        :param operational_status: The status for the device
        :return: void method
        """
        return

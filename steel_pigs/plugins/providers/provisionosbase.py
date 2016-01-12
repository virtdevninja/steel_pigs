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


class ProvisionOsBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_provision_script(self, server=None):
        """
        Returns a provision script for a given server.
        This could be a pre-seed file for Debian or Ubuntu
        or it could be a Kickstart file.

        :param server: Server object as returned by the ProviderBase
        :return:
        """

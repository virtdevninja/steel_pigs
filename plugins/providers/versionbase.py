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


class VersionProviderBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_latest_versions(self):
        """
        Returns the most recent versions and locations of the software projects
        needed to make your systems run.

        :return:
        """
        return

    @abc.abstractmethod
    def get_latest_ipxe(self, project):
        """
        This method is almost identical to get_software_versions_json() except
        that it returns variables in iPXE script format.

        :param project:
        :return:
        """

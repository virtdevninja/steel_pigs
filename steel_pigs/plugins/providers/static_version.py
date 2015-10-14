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

from .versionbase import VersionProviderBase


class StaticVersionProvider(VersionProviderBase):

    def __init__(self, config):
        pass

    def get_latest_versions(self):
        """
        Returns a static dictionary useful in testing.

        :return:
        """
        return {
            "cloud_files": {
                "cdn_url": "http://cloudfiles.rpc.local",
                "container": "private",
                "torrent_url": "torrent://torrents.rpc.local"
            },
            "region": "ORD",
            "last_checked_date": "Thu, 08 Oct 2015 20:30:04 +0000",
            "last_checked": 1444336204,
            "projects": {"squashible-kvm-fedora23": {"files": [
                "squashible-kvm-fedora23/27/initrd.img",
                "squashible-kvm-fedora23/27/rootfs.img.tgz",
                "squashible-kvm-fedora23/27/squashible-kvm-fedora23-27-DFW.torrent",
                "squashible-kvm-fedora23/27/squashible-kvm-fedora23-27-ORD.torrent",
                "squashible-kvm-fedora23/27/squashible-kvm-fedora23-27.torrent",
                "squashible-kvm-fedora23/27/vmlinuz"
            ],
                "latest": 27
            }}
        }

    def get_latest_ipxe(self, project=None):
        """
        This method would contain all logic to serve up an ipxe script
        for a given project.

        :param project:
        :return:
        """
        return """#!ipxe
# Last updated: Thu, 08 Oct 2015 20:30:04 +0000

set vmlinuz_url http://cloudfiles.rpc.local/squashible-kvm-centos7/4/vmlinuz
set initrd_url http://cloudfiles.rpc.local/squashible-kvm-centos7/4/initrd.img
set torrent_url torrent://torrents.rpc.local/squashible-kvm-centos7/4/squashible-kvm-centos7-4-ORD.torrent
set latest_version 4"""

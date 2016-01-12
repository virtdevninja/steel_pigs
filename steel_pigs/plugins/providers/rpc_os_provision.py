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

from flask import render_template, make_response

from steel_pigs.exceptions.pigs_exceptions import ProvisionException

from .provisionosbase import ProvisionOsBase


class RPCProvision(ProvisionOsBase):

    def __init__(self, config):
        pass

    def get_provision_script(self, server=None):
        if server is None:
            raise ProvisionException("Server can not be None")
        data = render_template("rpc-pre-seed.j2", server=server)
        return data

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
import json

from time import gmtime, strftime

from flask import render_template, make_response

from .ipxebase import PXEProvider


class StaticPXEProvider(PXEProvider):

    def __init__(self, *args, **kwargs):
        pass

    def generate_ipxe_script(self, *args, **kwargs):
        """
        Returns an iPXE script using the provided args and kwargs

        :param args:
        :param kwargs:
        :return:
        """
        request = kwargs.get("request")
        server_data = kwargs.get("server_data")
        timestamp = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        server_data_dump = self._indenter(server_data)
        data = render_template("pigs.ipxe",
                               server_data=server_data,
                               server_data_dump=server_data_dump,
                               server_hostname=server_data["hostname"],
                               terraform_ip=request.args.get("terraform_ip"),
                               request=request,
                               timestamp=timestamp)
        r = make_response(data)
        r.mimetype = "text/plain"
        return r

    def _indenter(self, text_to_indent):
        """
        Transforms the indented json.dumps() output into a commented form to go
        into the iPXE script.  This would have been less hackish if the textwrap
        module in Python 2.7 wasn't so awful.
        """
        temp = ""
        for line in json.dumps(text_to_indent, indent=2).split('\n'):
            temp += "#   %s\n" % line
        return temp.strip()

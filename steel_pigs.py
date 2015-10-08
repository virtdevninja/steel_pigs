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

from flask import Flask, render_template, make_response, request, abort
from flask_bootstrap import Bootstrap

from pigs_app_settings.nav import nav
from pigs_app_settings.frontend import frontend

import pigs_config

#logging.basicConfig(
#    format='%(asctime)s %(message)s',
#    level="{}".format(pigs_config.LOGLEVEL)
#)

app = Flask(__name__)
Bootstrap(app)
app.register_blueprint(frontend)
app.secret_key = pigs_config.SECRET_KEY

nav.init_app(app)

server_data_provider_plugin = __import__(
    pigs_config.PROVIDER_PLUGIN["namespace"],
    fromlist=pigs_config.PROVIDER_PLUGIN["class"]
)

klass = getattr(
    server_data_provider_plugin,
    pigs_config.PROVIDER_PLUGIN["class"]
)

provider_plugin = klass(pigs_config.PROVIDER_PLUGIN)


@app.route("/pxe")
@app.route("/pxe/configs/<config_file>")
def get_pxe_script(config_file=None):
    """
    Takes a request and returns an iPXE script based on data pulled live from
    what ever plugin provider you have configured.

    :param config_file:
    :return:
    """
    pass


@app.route("/hardware")
def get_hardware_specs():
    """
    Matching on strings with spaces in iPXE is a royal pain. This is a hack
    that allows iPXE to feed data into steel_pigs and get a reasonable
    response based on the hardware platform.

    :return: ipxe script
    """
    logging.info("Request to /hardware with params: {0}".format(
        dict(request.args))
    )
    # Get manufacturer and product
    manufacturer = request.args.get('manufacturer')
    product = request.args.get('product')
    if manufacturer is None or product is None:
        abort(412)

    # Strip out spaces and rewrite hardware detection variables for ipxe
    manufacturer_stripped = manufacturer.replace(" ", "")
    product_stripped = product.replace(" ", "")

    # Generate PXE script and write it to disk for a static boot next time
    hardwaredata = render_template('hardware.ipxe',
                                   make=manufacturer_stripped,
                                   model=product_stripped)

    r = make_response(hardwaredata)
    r.mimetype = "text/plain"

    return r



#@app.route("/versions")
#@app.route("/versions/json")
#@app.route("/versions/ipxe")
#@app.route("/versions/ipxe/<project>")

#@app.route("/update", methods=["PUT"])
#@app.route("/update/status", methods=["PUT"])
#@app.route("/update/os")
#@app.route("/update/opstatus")



if __name__ == '__main__':
    app.run(debug=True)

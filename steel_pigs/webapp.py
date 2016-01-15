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
from flask import jsonify
from flask_bootstrap import Bootstrap

from pigs_app_settings.nav import nav
from pigs_app_settings.frontend import frontend

import pigs_config

app = Flask(__name__, static_folder='static', static_url_path='',
            template_folder='templates')

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
# This is to catch instances where a plugin does not have an
# __init__ method that supports passing in the config dict
try:
    server_data_plugin = klass(pigs_config.PROVIDER_PLUGIN)
except TypeError as te:
    print te.message
    raise SystemExit

version_data_provider_plugin = __import__(
    pigs_config.VERSION_PROVIDER_PLUGIN["namespace"],
    fromlist=pigs_config.VERSION_PROVIDER_PLUGIN["class"]
)
del klass
klass = getattr(
    version_data_provider_plugin,
    pigs_config.VERSION_PROVIDER_PLUGIN["class"]
)

try:
    version_data_plugin = klass(pigs_config.VERSION_PROVIDER_PLUGIN)
except TypeError as te:
    print te.message
    raise SystemExit

formatter_provider_plugin = __import__(
    pigs_config.FORMATTER_PROVIDER_PLUGIN["namespace"],
    fromlist=pigs_config.FORMATTER_PROVIDER_PLUGIN["class"]
)
del klass
klass = getattr(
    formatter_provider_plugin,
    pigs_config.FORMATTER_PROVIDER_PLUGIN["class"]
)

try:
    formatter_plugin = klass(pigs_config.FORMATTER_PROVIDER_PLUGIN)
except TypeError as te:
    print te.message
    raise SystemExit

pxe_provider_plugin = __import__(
    pigs_config.PXE_PROVIDER_PLUGIN["namespace"],
    fromlist=pigs_config.PXE_PROVIDER_PLUGIN["class"]
)
del klass
klass = getattr(
    pxe_provider_plugin,
    pigs_config.PXE_PROVIDER_PLUGIN["class"]
)

try:
    pxe_plugin = klass(pigs_config.PXE_PROVIDER_PLUGIN)
except TypeError as te:
    print te.message
    raise SystemExit

provision_provider_plugin = __import__(
    pigs_config.PROVISION_PROVIDER_PLUGIN["namespace"],
    fromlist=pigs_config.PROVISION_PROVIDER_PLUGIN["class"]
)
del klass
klass = getattr(
    provision_provider_plugin,
    pigs_config.PROVISION_PROVIDER_PLUGIN["class"]
)

try:
    provision_plugin = klass(pigs_config.PROVISION_PROVIDER_PLUGIN)
except TypeError as te:
    print te.message
    raise SystemExit


# yucky but I couldnt think of a better way to solve this.
# for unit testing to work the app loads a separate in memory
# db so the data loaded during the class initialization is not
# accessible to the flask app :(
def _add_server_data(data):
    server_data = data["server_data"]
    switch_info = data["switch_info"]
    server_data_plugin.create_entry(server_data)
    for switch in switch_info:
        server_data_plugin.add_switch_entry(switch)


@app.route("/pxe")
@app.route("/pxe/configs/<config_file>")
def get_pxe_script(config_file=None):
    """
    Takes a request and returns an iPXE script based on data pulled live from
    what ever plugin provider you have configured.

    :param config_file:
    :return:
    """
    logging.info("Request to /pxe with params: %s" % dict(request.args))

    # Did we get a server number or a switch name/port combo?
    # NOTE(major): This is really ugly but Ant begged me to do it and said I
    #              would be forgiven at a later date.
    if 'number' in request.args:
        server_number = request.args.get('number')
        server_data = server_data_plugin.get_server_by_number(server_number)
    elif 'server_number' in request.args:
        server_number = request.args.get("server_number")
        server_data = server_data_plugin.get_server_by_number(server_number)
    elif 'mac' in request.args:
        mac = request.args.get('mac')
        mac_address = formatter_plugin.format_mac(mac)
        server_data = server_data_plugin.get_server_by_mac(mac_address)
    else:
        # Get the switch data and strip it
        switch_name = request.args.get('switch_name')
        switch_port = request.args.get('switch_port')
        if switch_name is None or switch_port is None:
            abort(412)
        switch_name_stripped = formatter_plugin.format_switch(switch_name)
        switch_port_stripped = formatter_plugin.format_port(switch_port)
        # Get the server_data for this switch name/port combo
        server_data = server_data_plugin.get_server_by_switch(
            switch_name_stripped, switch_port_stripped
        )
    # logic for your response including mime type, or headers should all
    # happen in your pxe plugin.
    return pxe_plugin.generate_ipxe_script(server_data=server_data, request=request)


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


@app.route("/versions")
@app.route("/versions/json")
def get_software_versions_json():
    """
    Returns the most recent versions and locations of the software projects
    needed to make the Servers run.

    Specifics on how this data is gathered are handled by the plugin configured
    in your config.

    :return:
    """
    logging.info("Returning version data.")
    return jsonify(version_data_plugin.get_latest_versions())


@app.route("/versions/ipxe")
@app.route("/versions/ipxe/<project>")
def get_software_versions_ipxe(project=None):
    """
    This method is almost identical to get_software_versions_json() except that
    it returns variables in iPXE script format.
    """
    # For backwards compatibility on requests that don't specify a project name
    logging.info("Fetching iPXE version script.")
    r = make_response(version_data_plugin.get_latest_ipxe(project))
    r.mimetype = "text/plain"
    return r


@app.route("/update")
@app.route("/update/status")
def set_boot_status():
    """
    Get the server number and status from request
    """
    server_number = request.args.get('server_number')
    boot_status = request.args.get('boot_status')

    if server_number is None or boot_status is None:
        abort(412)

    response = server_data_plugin.set_boot_status(server_number, boot_status)
    return jsonify(response)


@app.route("/update/os")
def set_boot_os():
    """
    Get the server number and status from request
    """
    server_number = request.args.get('server_number')
    boot_os = request.args.get('boot_os')

    if server_number is None or boot_os is None:
        abort(412)

    return jsonify(
        server_data_plugin.set_boot_os(server_number, boot_os)
    )


@app.route("/update/opstatus")
def set_operational_status():
    """
    Get the server number and status from request
    """
    logging.info("Set Operational Status: {}".format(dict(request.args)))
    server_number = request.args.get('server_number')
    operational_status = request.args.get('opstatus')

    if server_number is None or operational_status is None:
        abort(412)
    return jsonify(
        server_data_plugin.set_operational_status(server_number, operational_status)
    )


@app.route("/provision/os/start")
def begin_os_provisioning():
    """
    Get a provision script for a given device.
    This could be a kickstart file, or a preseed file
    just depends on the device and how you configure
    the plugin that provides this info.

    :return:
    """
    logging.info("Fetching provision start. Device: ".format(dict(request.args)))
    server_mac = request.args.get("mac")
    if server_mac is None:
        abort(412, description="Missing required param: mac")
    server = server_data_plugin.get_server_by_mac(mac=server_mac)
    if server is None:
        abort(404, description="Server not found using {}".format(server_mac))
    if str(server["operational_status"]).lower() == pigs_config.ONLINE_COMPLETE_STATUS.lower():
        return
    elif str(server["operational_status"]).lower() != pigs_config.PROVISION_STATUS.lower():
        return
    return provision_plugin.get_provision_script(server)


if __name__ == '__main__':
    app.run(debug=True)

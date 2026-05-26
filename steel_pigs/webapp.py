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
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
)
from flask_bootstrap import Bootstrap5

from . import pigs_config
from .pigs_app_settings.frontend import frontend

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Plugins:
    server_data: Any
    version: Any
    formatter: Any
    pxe: Any
    provision: Any


_PLUGIN_SPECS = {
    "server_data": "PROVIDER_PLUGIN",
    "version": "VERSION_PROVIDER_PLUGIN",
    "formatter": "FORMATTER_PROVIDER_PLUGIN",
    "pxe": "PXE_PROVIDER_PLUGIN",
    "provision": "PROVISION_PROVIDER_PLUGIN",
}


def _load_plugin(spec):
    """Instantiate a plugin from a {'namespace': ..., 'class': ...} config dict."""
    module = import_module(spec["namespace"])
    klass = getattr(module, spec["class"])
    return klass(spec)


def _plugins() -> Plugins:
    return current_app.extensions["steel_pigs"]


api = Blueprint("api", __name__)


@api.route("/pxe")
@api.route("/pxe/configs/<config_file>")
def get_pxe_script(config_file=None):
    """Render an iPXE script for the requested server."""
    log.info("Request to /pxe with params: %s", dict(request.args))
    p = _plugins()
    args = request.args
    # NOTE(major): This dispatch chain is preserved from the original code -
    # Ant requested both 'number' and 'server_number' aliases.
    if "number" in args:
        server_data = p.server_data.get_server_by_number(args["number"])
    elif "server_number" in args:
        server_data = p.server_data.get_server_by_number(args["server_number"])
    elif "mac" in args:
        mac = p.formatter.format_mac(args["mac"])
        server_data = p.server_data.get_server_by_mac(mac)
    else:
        switch_name = args.get("switch_name")
        switch_port = args.get("switch_port")
        if switch_name is None or switch_port is None:
            abort(412)
        server_data = p.server_data.get_server_by_switch(
            p.formatter.format_switch(switch_name),
            p.formatter.format_port(switch_port),
        )
    return p.pxe.generate_ipxe_script(server_data=server_data, request=request)


@api.route("/hardware")
def get_hardware_specs():
    """iPXE can't match strings with spaces; we strip them and re-emit."""
    log.info("Request to /hardware with params: %s", dict(request.args))
    manufacturer = request.args.get("manufacturer")
    product = request.args.get("product")
    if manufacturer is None or product is None:
        abort(412)
    body = render_template(
        "hardware.ipxe",
        make=manufacturer.replace(" ", ""),
        model=product.replace(" ", ""),
    )
    r = make_response(body)
    r.mimetype = "text/plain"
    return r


@api.route("/versions")
@api.route("/versions/json")
def get_software_versions_json():
    log.info("Returning version data.")
    return jsonify(_plugins().version.get_latest_versions())


@api.route("/versions/ipxe")
@api.route("/versions/ipxe/<project>")
def get_software_versions_ipxe(project=None):
    log.info("Fetching iPXE version script.")
    r = make_response(_plugins().version.get_latest_ipxe(project))
    r.mimetype = "text/plain"
    return r


@api.route("/update")
@api.route("/update/status")
def set_boot_status():
    server_number = request.args.get("server_number")
    boot_status = request.args.get("boot_status")
    if server_number is None or boot_status is None:
        abort(412)
    return jsonify(_plugins().server_data.set_boot_status(server_number, boot_status))


@api.route("/update/os")
def set_boot_os():
    server_number = request.args.get("server_number")
    boot_os = request.args.get("boot_os")
    if server_number is None or boot_os is None:
        abort(412)
    return jsonify(_plugins().server_data.set_boot_os(server_number, boot_os))


@api.route("/update/opstatus")
def set_operational_status():
    log.info("Set Operational Status: %s", dict(request.args))
    server_number = request.args.get("server_number")
    operational_status = request.args.get("opstatus")
    if server_number is None or operational_status is None:
        abort(412)
    return jsonify(_plugins().server_data.set_operational_status(server_number, operational_status))


@api.route("/provision/os/start")
def begin_os_provisioning():
    """Return a provision (kickstart / preseed) script for a device by MAC."""
    log.info("Fetching provision start: %s", dict(request.args))
    server_mac = request.args.get("mac")
    if server_mac is None:
        abort(412, description="Missing required param: mac")
    p = _plugins()
    server = p.server_data.get_server_by_mac(mac=server_mac)
    if server is None:
        abort(404, description=f"Server not found using {server_mac}")
    op_status = str(server["operational_status"]).lower()
    if op_status == pigs_config.ONLINE_COMPLETE_STATUS.lower():
        return "", 204
    if op_status != pigs_config.PROVISION_STATUS.lower():
        return "", 204
    return p.provision.get_provision_script(server)


def create_app(config_overrides=None, plugins: Plugins | None = None) -> Flask:
    """Build a configured Flask app.

    Pass ``plugins`` to inject pre-built plugin instances (used by tests so
    routes and seeding share the same in-memory plugin state).
    """
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="",
        template_folder="templates",
    )
    app.config["SECRET_KEY"] = pigs_config.SECRET_KEY
    if config_overrides:
        app.config.update(config_overrides)

    Bootstrap5(app)
    app.register_blueprint(frontend)
    app.register_blueprint(api)

    if plugins is None:
        plugins = Plugins(
            **{
                attr: _load_plugin(getattr(pigs_config, config_key))
                for attr, config_key in _PLUGIN_SPECS.items()
            }
        )
    app.extensions["steel_pigs"] = plugins
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

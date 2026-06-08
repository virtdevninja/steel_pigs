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
import uuid
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    g,
    jsonify,
    make_response,
    render_template,
    request,
)
from flask_bootstrap import Bootstrap5

from . import audit, pigs_config
from .auth import requires_auth
from .pigs_app_settings.frontend import frontend
from .states import BootStatus, OperationalStatus

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Plugins:
    server_data: Any
    version: Any
    formatter: Any
    pxe: Any
    provision: Any
    auth: Any


_PLUGIN_SPECS = {
    "server_data": "PROVIDER_PLUGIN",
    "version": "VERSION_PROVIDER_PLUGIN",
    "formatter": "FORMATTER_PROVIDER_PLUGIN",
    "pxe": "PXE_PROVIDER_PLUGIN",
    "provision": "PROVISION_PROVIDER_PLUGIN",
    "auth": "AUTH_PROVIDER_PLUGIN",
}


def _load_plugin(spec):
    """Instantiate a plugin from a {'namespace': ..., 'class': ...} config dict."""
    module = import_module(spec["namespace"])
    klass = getattr(module, spec["class"])
    return klass(spec)


def _plugins() -> Plugins:
    return current_app.extensions["steel_pigs"]


def _log_safe(value):
    """Render a value for logging with CR/LF stripped (CWE-117 defense).

    ``repr()`` already escapes embedded newlines in string fields, but
    CodeQL's dataflow analysis doesn't recognize ``%r`` formatting as a
    sanitizer for the py/log-injection rule. The explicit
    ``.replace()`` chain makes the sanitizer visible to static analysis
    and is a no-op in practice on repr output.
    """
    return repr(value).replace("\n", "").replace("\r", "")


def _validated_status(value, enum_cls):
    """Lowercase + validate ``value`` against ``enum_cls``.

    Returns the canonical enum string value on success. Aborts with 412
    if the param is missing, 400 if it is not a known status.
    """
    if value is None:
        abort(412)
    normalized = value.lower()
    try:
        return enum_cls(normalized).value
    except ValueError:
        allowed = ", ".join(m.value for m in enum_cls)
        abort(400, description=f"Invalid status {value!r}. Allowed: {allowed}")


api = Blueprint("api", __name__)


@api.route("/healthz")
def healthz():
    """Liveness: the WSGI process is alive and serving."""
    return {"status": "ok"}, 200


@api.route("/readyz")
def readyz():
    """Readiness: app booted, all plugins loaded.

    The plugin contract has no healthcheck method yet, so this only
    proves the dataclass exists. Once plugins grow a ``healthcheck()``
    method we can call into each here.
    """
    if current_app.extensions.get("steel_pigs") is None:
        return {"status": "not_ready", "reason": "plugins not initialized"}, 503
    return {"status": "ok"}, 200


@api.route("/pxe")
@api.route("/pxe/configs/<config_file>")
def get_pxe_script(config_file=None):
    """Render an iPXE script for the requested server."""
    log.info("Request to /pxe with params: %s", _log_safe(dict(request.args)))
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
    log.info("Request to /hardware with params: %s", _log_safe(dict(request.args)))
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


# --- Legacy mutation endpoints --------------------------------------------
# These accepted GETs that mutated state, were unauthenticated, and accepted
# parameters via query string. All three were moved to POST /v1/update/...
# in this release. The legacy paths respond 405 Method Not Allowed with a
# pointer at the new endpoint so existing callers fail loudly instead of
# silently succeeding against an unauth'd surface.


def _legacy_405(new_path):
    response = make_response(
        jsonify(
            {
                "error": "Method Not Allowed",
                "message": f"This endpoint moved to POST {new_path}",
            }
        ),
        405,
    )
    response.headers["Allow"] = "POST"
    return response


@api.route("/update", methods=["GET"])
@api.route("/update/status", methods=["GET"])
def legacy_set_boot_status_get():
    return _legacy_405("/v1/update/status")


@api.route("/update/os", methods=["GET"])
def legacy_set_boot_os_get():
    return _legacy_405("/v1/update/os")


@api.route("/update/opstatus", methods=["GET"])
def legacy_set_operational_status_get():
    return _legacy_405("/v1/update/opstatus")


@api.route("/provision/os/start")
def begin_os_provisioning():
    """Return a provision (kickstart / preseed) script for a device by MAC."""
    log.info("Fetching provision start: %s", _log_safe(dict(request.args)))
    server_mac = request.args.get("mac")
    if server_mac is None:
        abort(412, description="Missing required param: mac")
    p = _plugins()
    server = p.server_data.get_server_by_mac(mac=server_mac)
    if server is None:
        abort(404, description=f"Server not found using {server_mac}")
    op_status = str(server["operational_status"]).lower()
    if op_status == OperationalStatus.ONLINE.value:
        return "", 204
    if op_status != OperationalStatus.PROVISION.value:
        return "", 204
    return p.provision.get_provision_script(server)


# --- v1 mutation API ------------------------------------------------------
# POST + JSON body, behind @requires_auth. Replaces the legacy /update/*
# GET endpoints, which now return 405 (see above).

v1 = Blueprint("v1", __name__, url_prefix="/v1")


def _json_field(data, name):
    """Pull a required field from a parsed JSON body or abort 400."""
    value = data.get(name)
    if value is None:
        abort(400, description=f"Missing required field: {name}")
    return value


def _audit_context(field, server_number, new_value):
    """Build before/after snapshots for the audit log."""
    existing = _plugins().server_data.get_server_by_number(server_number)
    return {
        "before": {field: existing[field]} if existing else None,
        "after": {field: new_value},
    }


@v1.route("/update/status", methods=["POST"])
@requires_auth
def v1_set_boot_status():
    data = request.get_json(silent=True) or {}
    server_number = _json_field(data, "server_number")
    boot_status = _validated_status(data.get("boot_status"), BootStatus)
    ctx = _audit_context("boot_status", server_number, boot_status)
    result = _plugins().server_data.set_boot_status(server_number, boot_status)
    audit.emit(
        action="set_boot_status",
        resource=f"server/{server_number}",
        actor=g.get("actor"),
        before=ctx["before"],
        after=ctx["after"],
        request_id=g.get("request_id"),
    )
    return jsonify(result)


@v1.route("/update/os", methods=["POST"])
@requires_auth
def v1_set_boot_os():
    data = request.get_json(silent=True) or {}
    server_number = _json_field(data, "server_number")
    boot_os = _json_field(data, "boot_os")
    ctx = _audit_context("boot_os", server_number, boot_os)
    result = _plugins().server_data.set_boot_os(server_number, boot_os)
    audit.emit(
        action="set_boot_os",
        resource=f"server/{server_number}",
        actor=g.get("actor"),
        before=ctx["before"],
        after=ctx["after"],
        request_id=g.get("request_id"),
    )
    return jsonify(result)


@v1.route("/update/opstatus", methods=["POST"])
@requires_auth
def v1_set_operational_status():
    data = request.get_json(silent=True) or {}
    server_number = _json_field(data, "server_number")
    operational_status = _validated_status(data.get("opstatus"), OperationalStatus)
    ctx = _audit_context("operational_status", server_number, operational_status)
    result = _plugins().server_data.set_operational_status(server_number, operational_status)
    audit.emit(
        action="set_operational_status",
        resource=f"server/{server_number}",
        actor=g.get("actor"),
        before=ctx["before"],
        after=ctx["after"],
        request_id=g.get("request_id"),
    )
    return jsonify(result)


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
    app.register_blueprint(v1)

    @app.before_request
    def _assign_request_id():
        # X-Request-ID from upstream (load balancer, proxy) wins so audit
        # events can be correlated with infra logs; otherwise generate one.
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

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
    # Dev convenience only. Production runs via gunicorn -- see the
    # Dockerfile and README. ``debug=True`` here would expose the
    # Werkzeug debugger, an RCE vector if the dev server is ever
    # reachable beyond localhost (CodeQL py/flask-debug, alert #1).
    app.run(host="127.0.0.1")

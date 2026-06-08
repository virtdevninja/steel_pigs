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

"""HTTP surface for steel_pigs.

Built on APIFlask; OpenAPI 3 spec auto-generated from the per-route
schemas in ``steel_pigs.schemas`` and published at ``/openapi.json``
with Swagger UI at ``/docs``.

Two API blueprints:

* ``api``  -- unauthenticated reads for the PXE-boot flow plus health
              endpoints.
* ``v1``   -- authenticated mutation endpoints under ``/v1``.

The demo HTML frontend stays as a vanilla Flask Blueprint (so it
doesn't appear in the OpenAPI spec).
"""

import logging
import uuid
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from apiflask import APIBlueprint, APIFlask, abort
from flask import current_app, g, make_response, render_template, request
from flask_bootstrap import Bootstrap5

from . import audit, pigs_config
from .auth import auth
from .exceptions.pigs_exceptions import ServerAlreadyExists, ServerNotFound
from .pigs_app_settings.frontend import frontend
from .schemas import (
    AddSwitchIn,
    BootOsResultOut,
    BootStatusResultOut,
    CreateServerIn,
    HardwareQuery,
    HealthOut,
    OpStatusResultOut,
    ProvisionQuery,
    PxeQuery,
    ServerOut,
    SwitchOut,
    UpdateBootOsIn,
    UpdateBootStatusIn,
    UpdateOpStatusIn,
)
from .states import OperationalStatus

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


# --- /api -- open read + health routes -----------------------------------

api = APIBlueprint("api", __name__, tag="Read")


@api.get("/healthz")
@api.output(HealthOut)
@api.doc(summary="Liveness probe", description="Returns 200 if the WSGI process is serving.")
def healthz():
    return {"status": "ok"}


@api.get("/readyz")
@api.output(HealthOut)
@api.doc(summary="Readiness probe", description="Returns 200 if create_app() registered plugins.")
def readyz():
    return {"status": "ok"}


@api.get("/pxe")
@api.input(PxeQuery, location="query")
@api.doc(
    summary="Render an iPXE boot script",
    description=(
        "Returns an iPXE script tailored to the requested server. Supply "
        "one of ``server_number``, ``mac``, or the pair ``switch_name`` + "
        "``switch_port`` to identify the target. The response body is "
        "text/plain and produced by the configured PXE plugin."
    ),
    responses={
        200: {
            "description": "iPXE script",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        },
        412: {"description": "No identification params supplied"},
    },
)
def get_pxe_script(query_data):
    log.info("Request to /pxe with params: %s", _log_safe(query_data))
    p = _plugins()
    if query_data["server_number"] is not None:
        server_data = p.server_data.get_server_by_number(query_data["server_number"])
    elif query_data["mac"] is not None:
        server_data = p.server_data.get_server_by_mac(p.formatter.format_mac(query_data["mac"]))
    elif query_data["switch_name"] is not None and query_data["switch_port"] is not None:
        server_data = p.server_data.get_server_by_switch(
            p.formatter.format_switch(query_data["switch_name"]),
            p.formatter.format_port(query_data["switch_port"]),
        )
    else:
        abort(412, "Supply server_number, mac, or (switch_name and switch_port).")
    return p.pxe.generate_ipxe_script(server_data=server_data, request=request)


@api.get("/hardware")
@api.input(HardwareQuery, location="query")
@api.doc(
    summary="Render the hardware-detection iPXE callback",
    description=(
        "iPXE can't easily match strings with spaces. This route accepts "
        "the manufacturer / product strings, strips whitespace, and emits "
        "an iPXE script that re-assigns the cleaned values."
    ),
    responses={
        200: {
            "description": "iPXE script",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        },
    },
)
def get_hardware_specs(query_data):
    log.info("Request to /hardware with params: %s", _log_safe(query_data))
    body = render_template(
        "hardware.ipxe",
        make=query_data["manufacturer"].replace(" ", ""),
        model=query_data["product"].replace(" ", ""),
    )
    r = make_response(body)
    r.mimetype = "text/plain"
    return r


@api.get("/versions")
@api.doc(
    summary="Software versions metadata (JSON)",
    description="Returned shape is determined by the configured version plugin.",
)
def get_software_versions_json():
    log.info("Returning version data.")
    return _plugins().version.get_latest_versions()


@api.get("/versions/ipxe")
@api.get("/versions/ipxe/<project>")
@api.doc(
    summary="Software versions formatted as iPXE script",
    responses={
        200: {
            "description": "iPXE-formatted version variables",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        },
    },
)
def get_software_versions_ipxe(project=None):
    log.info("Fetching iPXE version script.")
    r = make_response(_plugins().version.get_latest_ipxe(project))
    r.mimetype = "text/plain"
    return r


@api.get("/provision/os/start")
@api.input(ProvisionQuery, location="query")
@api.doc(
    summary="Return a kickstart / preseed for a device",
    description=(
        "Servers in ``operational_status == online`` get a 204. Servers "
        "not in ``operational_status == provision`` also get a 204. "
        "Servers in provision state get the script body."
    ),
    responses={
        200: {
            "description": "Provision script body",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        },
        204: {"description": "Server already online or not ready to provision"},
        404: {"description": "Server not found for given MAC"},
    },
)
def begin_os_provisioning(query_data):
    log.info("Fetching provision start: %s", _log_safe(query_data))
    p = _plugins()
    server = p.server_data.get_server_by_mac(mac=query_data["mac"])
    if server is None:
        abort(404, f"Server not found using {query_data['mac']}")
    op_status = str(server["operational_status"]).lower()
    if op_status == OperationalStatus.ONLINE.value:
        return "", 204
    if op_status != OperationalStatus.PROVISION.value:
        return "", 204
    return p.provision.get_provision_script(server)


# --- /v1 -- authenticated mutations --------------------------------------

v1 = APIBlueprint("v1", __name__, url_prefix="/v1", tag="Mutate")


def _audit_context(field, server_number, new_value):
    """Build before/after snapshots for the audit log."""
    existing = _plugins().server_data.get_server_by_number(server_number)
    return {
        "before": {field: existing[field]} if existing else None,
        "after": {field: new_value},
    }


@v1.post("/update/status")
@v1.doc(summary="Set a server's boot status")
@v1.auth_required(auth)
@v1.input(UpdateBootStatusIn)
@v1.output(BootStatusResultOut)
def v1_set_boot_status(json_data):
    server_number = json_data["server_number"]
    boot_status = json_data["boot_status"]
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
    return result


@v1.post("/update/os")
@v1.doc(summary="Set a server's boot OS")
@v1.auth_required(auth)
@v1.input(UpdateBootOsIn)
@v1.output(BootOsResultOut)
def v1_set_boot_os(json_data):
    server_number = json_data["server_number"]
    boot_os = json_data["boot_os"]
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
    return result


@v1.post("/update/opstatus")
@v1.doc(summary="Set a server's operational status")
@v1.auth_required(auth)
@v1.input(UpdateOpStatusIn)
@v1.output(OpStatusResultOut)
def v1_set_operational_status(json_data):
    server_number = json_data["server_number"]
    operational_status = json_data["opstatus"]
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
    return result


@v1.post("/servers")
@v1.doc(
    summary="Register a new server",
    description=(
        "Required: network identity (IPs, MAC, hostname, DNS primary), "
        "boot template selection (boot_os, boot_os_version, boot_profile), "
        "and the NTP server. ``bootstrapped``, ``boot_status``, "
        "``operational_status``, and ``dns_domain_name`` get sensible "
        "first-boot defaults if omitted."
    ),
    responses={
        201: {"description": "Server registered"},
        409: {"description": "server_number already exists"},
        422: {"description": "Validation error"},
    },
)
@v1.auth_required(auth)
@v1.input(CreateServerIn)
@v1.output(ServerOut, status_code=201)
def v1_create_server(json_data):

    try:
        created = _plugins().server_data.create_server(json_data)
    except ServerAlreadyExists as exc:
        abort(409, str(exc))
    audit.emit(
        action="create_server",
        resource=f"server/{json_data['server_number']}",
        actor=g.get("actor"),
        before=None,
        after=created,
        request_id=g.get("request_id"),
    )
    return created


@v1.post("/servers/<int:server_number>/switches")
@v1.doc(
    summary="Attach a switch entry to an existing server",
    responses={
        201: {"description": "Switch attached"},
        404: {"description": "server_number not found"},
        422: {"description": "Validation error"},
    },
)
@v1.auth_required(auth)
@v1.input(AddSwitchIn)
@v1.output(SwitchOut, status_code=201)
def v1_add_switch(server_number, json_data):

    try:
        created = _plugins().server_data.add_switch(
            server_number, json_data["switch_name"], json_data["switch_port"]
        )
    except ServerNotFound as exc:
        abort(404, str(exc))
    audit.emit(
        action="add_switch",
        resource=(
            f"server/{server_number}/switch/{json_data['switch_name']}/{json_data['switch_port']}"
        ),
        actor=g.get("actor"),
        before=None,
        after=created,
        request_id=g.get("request_id"),
    )
    return created


# --- App factory ----------------------------------------------------------


def create_app(config_overrides=None, plugins: Plugins | None = None) -> APIFlask:
    """Build the configured APIFlask app.

    Pass ``plugins`` to inject pre-built plugin instances (used by tests
    so routes and seeding share the same in-memory plugin state).
    """
    app = APIFlask(
        __name__,
        title="Steel PIGS",
        version="0.4",
        spec_path="/openapi.json",
        docs_path="/docs",
        static_folder="static",
        static_url_path="",
        template_folder="templates",
    )
    app.config["DESCRIPTION"] = "Powerful iPXE Generation Service."
    app.config["SECURITY_SCHEMES"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "description": "Bearer token supplied via the Authorization header.",
        }
    }
    app.config["TAGS"] = [
        {"name": "Read", "description": "PXE-boot and health endpoints (unauthenticated)."},
        {"name": "Mutate", "description": "Inventory mutations (bearer auth required)."},
    ]
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

#   Copyright 2026 Michael Rice <michael@michaelrice.org>
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

"""Request / response / query schemas for the HTTP API.

These drive both runtime validation and the auto-generated OpenAPI spec
that's published at ``/openapi.json`` and rendered by Swagger UI at
``/docs``.

Field-level defaults on input schemas are deliberate: the goal is to
let an operator register a server with the minimum useful payload and
leave the obvious lifecycle defaults (``bootstrapped=False``,
``boot_status="kicking"``, ``operational_status="provisioning"``,
``dns_domain_name="rpc.local"``) implicit.
"""

from apiflask import Schema, fields
from apiflask.validators import Length, OneOf
from marshmallow import RAISE

from .states import BootStatus, OperationalStatus

_BOOT_STATUS_VALUES = [s.value for s in BootStatus]
_OPERATIONAL_STATUS_VALUES = [s.value for s in OperationalStatus]


class _StrictIn(Schema):
    """Base for input schemas that reject unknown fields with 422.

    Catches client-side typos at the boundary instead of silently
    dropping the offending key.
    """

    class Meta:
        unknown = RAISE


# --- Outputs -------------------------------------------------------------


class HealthOut(Schema):
    """Body of ``/healthz`` and ``/readyz``."""

    status = fields.String(required=True, metadata={"example": "ok"})
    reason = fields.String(metadata={"example": "plugins not initialized"})


class BootStatusResultOut(Schema):
    """Mutation result for ``POST /v1/update/status``."""

    operation = fields.String(required=True, validate=OneOf(["success", "failure"]))
    status_set = fields.String(required=True)


class BootOsResultOut(Schema):
    """Mutation result for ``POST /v1/update/os``."""

    operation = fields.String(required=True, validate=OneOf(["success", "failure"]))
    os_set = fields.String(required=True)


class OpStatusResultOut(Schema):
    """Mutation result for ``POST /v1/update/opstatus``."""

    operation = fields.String(required=True, validate=OneOf(["success", "failure"]))
    status_set = fields.String(required=True)


class ProvisionZoneOut(Schema):
    id = fields.Integer()
    zone_name = fields.String()
    provision_img_host = fields.String()
    provision_mirror_host = fields.String()


class ServerOut(Schema):
    """Server record returned from the create endpoint and reads."""

    id = fields.Integer(dump_only=True)
    server_number = fields.Integer(required=True)
    primary_ip = fields.String(required=True)
    primary_gw = fields.String(required=True)
    primary_nm = fields.String(required=True)
    primary_mac = fields.String(required=True)
    drac_ip = fields.String(allow_none=True)
    drac_gw = fields.String(allow_none=True)
    drac_nm = fields.String(allow_none=True)
    hostname = fields.String(required=True)
    dns_domain_name = fields.String()
    dns_server_primary = fields.String(required=True)
    dns_server_secondary = fields.String(allow_none=True)
    dns_server_tertiary = fields.String(allow_none=True)
    bootstrapped = fields.Boolean(required=True)
    boot_os = fields.String(required=True)
    boot_os_version = fields.String(required=True)
    boot_profile = fields.String(required=True)
    boot_status = fields.String(required=True)
    operational_status = fields.String(required=True)
    ntp_server = fields.String(required=True)
    provision_zone_id = fields.Integer(allow_none=True)
    provision_zone = fields.Nested(ProvisionZoneOut, allow_none=True, dump_only=True)


class SwitchOut(Schema):
    """Switch record returned from the add-switch endpoint."""

    id = fields.Integer(dump_only=True)
    server_number = fields.Integer(required=True)
    switch_name = fields.String(required=True)
    switch_port = fields.String(required=True)


# --- Inputs --------------------------------------------------------------


class UpdateBootStatusIn(_StrictIn):
    """Body of ``POST /v1/update/status``."""

    server_number = fields.Integer(required=True)
    boot_status = fields.String(required=True, validate=OneOf(_BOOT_STATUS_VALUES))


class UpdateBootOsIn(_StrictIn):
    """Body of ``POST /v1/update/os``."""

    server_number = fields.Integer(required=True)
    boot_os = fields.String(required=True, validate=Length(min=1))


class UpdateOpStatusIn(_StrictIn):
    """Body of ``POST /v1/update/opstatus``."""

    server_number = fields.Integer(required=True)
    opstatus = fields.String(
        required=True,
        validate=OneOf(_OPERATIONAL_STATUS_VALUES),
    )


class CreateServerIn(_StrictIn):
    """Body of ``POST /v1/servers``.

    Required fields are the network / identity bits steel_pigs cannot
    sensibly default. Status and lifecycle fields fall back to first-boot
    defaults so a basic register call stays small.
    """

    server_number = fields.Integer(required=True)
    primary_ip = fields.String(required=True)
    primary_gw = fields.String(required=True)
    primary_nm = fields.String(required=True)
    primary_mac = fields.String(required=True)
    hostname = fields.String(required=True)
    dns_server_primary = fields.String(required=True)
    boot_os = fields.String(required=True)
    boot_os_version = fields.String(required=True)
    boot_profile = fields.String(required=True)
    ntp_server = fields.String(required=True)

    # Defaulted -- operators can omit these on first register.
    bootstrapped = fields.Boolean(load_default=False)
    boot_status = fields.String(
        load_default=BootStatus.KICKING.value,
        validate=OneOf(_BOOT_STATUS_VALUES),
    )
    operational_status = fields.String(
        load_default=OperationalStatus.PROVISIONING.value,
        validate=OneOf(_OPERATIONAL_STATUS_VALUES),
    )
    dns_domain_name = fields.String(load_default="rpc.local")

    # Optional -- omit and they stay NULL in the DB.
    drac_ip = fields.String(load_default=None, allow_none=True)
    drac_gw = fields.String(load_default=None, allow_none=True)
    drac_nm = fields.String(load_default=None, allow_none=True)
    dns_server_secondary = fields.String(load_default=None, allow_none=True)
    dns_server_tertiary = fields.String(load_default=None, allow_none=True)
    provision_zone_id = fields.Integer(load_default=None, allow_none=True)


class AddSwitchIn(_StrictIn):
    """Body of ``POST /v1/servers/<server_number>/switches``."""

    switch_name = fields.String(required=True, validate=Length(min=1))
    switch_port = fields.String(required=True, validate=Length(min=1))


# --- Query args ----------------------------------------------------------


class PxeQuery(Schema):
    """Query args for ``GET /pxe``.

    One of (server_number), (mac), or (switch_name + switch_port) must be
    supplied. Mutual-exclusivity is enforced in the route since OpenAPI
    can't model it directly.
    """

    server_number = fields.Integer(load_default=None)
    mac = fields.String(load_default=None)
    switch_name = fields.String(load_default=None)
    switch_port = fields.String(load_default=None)


class HardwareQuery(Schema):
    """Query args for ``GET /hardware``."""

    manufacturer = fields.String(required=True)
    product = fields.String(required=True)


class ProvisionQuery(Schema):
    """Query args for ``GET /provision/os/start``."""

    mac = fields.String(required=True)

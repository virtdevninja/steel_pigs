"""Enumerations for boot and operational state.

Validated at the API boundary (``/update/status``, ``/update/opstatus``).
Storage plugins persist these as free-form strings, so a third-party
inventory plugin can extend or replace these enums; route-level
validation keeps the public HTTP surface tight.

Values are lowercase by convention. Routes lowercase the inbound value
before comparing, so callers can submit any case.
"""

from enum import Enum


class BootStatus(str, Enum):
    """Permitted values for ``/update/status``."""

    KICKING = "kicking"
    PROVISION = "provision"
    ONLINE = "online"
    DONE = "done"


class OperationalStatus(str, Enum):
    """Permitted values for ``/update/opstatus`` and for the
    ``operational_status`` field of a server record."""

    PROVISIONING = "provisioning"
    PROVISION = "provision"
    KICKING = "kicking"
    ONLINE = "online"
    PRODUCTION = "production"

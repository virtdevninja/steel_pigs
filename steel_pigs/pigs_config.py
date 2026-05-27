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
"""Default plugin selection and runtime configuration.

Secrets and per-deployment values come from environment variables:

* ``STEEL_PIGS_SECRET_KEY`` -- Flask session / CSRF key. Required in
  production. If unset, a random key is generated at import time and a
  warning is logged; sessions will not survive a restart.
* ``STEEL_PIGS_DATABASE_URL`` -- SQLAlchemy URL for the bundled ``SQL``
  inventory plugin. Defaults to an in-memory sqlite database.

Plugin selection (which namespace/class to load for each role) stays in
this file -- swap the dicts below to point at your own plugins.
"""

import logging
import os
import secrets

log = logging.getLogger(__name__)


def _resolve_secret_key():
    key = os.environ.get("STEEL_PIGS_SECRET_KEY")
    if key:
        return key
    log.warning(
        "STEEL_PIGS_SECRET_KEY is not set; generating a random key. "
        "Sessions and CSRF tokens will not survive a restart."
    )
    return secrets.token_hex(32)


SECRET_KEY = _resolve_secret_key()


def _resolve_database_url():
    url = os.environ.get("STEEL_PIGS_DATABASE_URL", "sqlite:///steel_pigs.db")
    if ":memory:" in url:
        # Tests legitimately want in-memory; production almost never does.
        # The string match catches both sqlite:///:memory: and the
        # file::memory: shared-cache form.
        log.warning(
            "STEEL_PIGS_DATABASE_URL points at an in-memory SQLite database "
            "(%s); inventory will not survive a restart. Set the env var to a "
            "persistent URL for non-test deployments.",
            url,
        )
    return url


PROVIDER_PLUGIN = {
    "namespace": "steel_pigs.plugins.providers.sql",
    "class": "SQL",
    "engine": _resolve_database_url(),
}

VERSION_PROVIDER_PLUGIN = {
    "namespace": "steel_pigs.plugins.providers.static_version",
    "class": "StaticVersionProvider",
}

PXE_PROVIDER_PLUGIN = {
    "namespace": "steel_pigs.plugins.providers.static_pxe_provider",
    "class": "StaticPXEProvider",
}

FORMATTER_PROVIDER_PLUGIN = {
    "namespace": "steel_pigs.plugins.providers.noformat",
    "class": "NoFormatProvider",
}

PROVISION_PROVIDER_PLUGIN = {
    "namespace": "steel_pigs.plugins.providers.rpc_os_provision",
    "class": "RPCProvision",
}

AUTH_PROVIDER_PLUGIN = {
    "namespace": "steel_pigs.plugins.providers.env_token_auth",
    "class": "EnvTokenAuth",
}

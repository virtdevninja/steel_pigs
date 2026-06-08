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

import hmac
import logging
import os

from .authbase import AuthProviderBase

log = logging.getLogger(__name__)


class EnvTokenAuth(AuthProviderBase):
    """Single-token bearer auth.

    Reads the expected token from ``STEEL_PIGS_API_TOKEN`` at construction.
    Validates ``Authorization: Bearer <token>`` on each request using a
    constant-time compare. If the env var is unset, every request fails
    authentication -- there is no fallback-allow.

    For production deployments with more than one operator or any need
    for rotation, write a real auth plugin (LDAP, OIDC, your token
    service of choice). This bundled impl is the smallest thing that
    closes the unauth-everything gap.
    """

    def __init__(self, config):
        self._expected = os.environ.get("STEEL_PIGS_API_TOKEN") or ""
        if not self._expected:
            log.warning(
                "STEEL_PIGS_API_TOKEN is not set; EnvTokenAuth will reject "
                "every request. Set the env var or swap in a real auth plugin."
            )

    def authenticate_token(self, token):
        if not self._expected or not token:
            return None
        if hmac.compare_digest(token.strip(), self._expected):
            return "env-token"
        return None

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

import abc


class AuthProviderBase(abc.ABC):
    """Plugin contract for request authentication.

    Implementations get the bearer token off the ``Authorization`` header
    and return a string actor identity on success, or ``None`` to fail
    the request with 401. The actor id is threaded into the audit log.

    Plugin authors that need to look at more than the bearer token (e.g.,
    an OIDC plugin that consumes a session cookie) can grab the full
    request via ``flask.request`` -- the contract just guarantees the
    token string is also passed in.
    """

    @abc.abstractmethod
    def authenticate_token(self, token):
        """Return a string actor id if ``token`` is valid, else ``None``."""

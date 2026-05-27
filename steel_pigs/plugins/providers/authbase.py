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

    Implementations decide whether an inbound Flask ``request`` is
    authenticated, and if so return a string actor identity that gets
    threaded into the audit log. Returning ``None`` causes the
    ``@requires_auth`` decorator to respond with 401.
    """

    @abc.abstractmethod
    def authenticate(self, request):
        """Return a string actor id if authenticated, else None."""

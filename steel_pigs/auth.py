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

"""Auth helpers used by mutation routes.

``@requires_auth`` looks up the configured auth plugin via
``current_app.extensions["steel_pigs"].auth``, calls ``authenticate(request)``,
and either stores the actor id on ``flask.g`` for downstream code (the
audit log reads ``g.actor``) or returns a 401 with ``WWW-Authenticate:
Bearer``.
"""

from functools import wraps

from flask import current_app, g, jsonify, make_response, request


def _unauthorized():
    response = make_response(jsonify({"error": "Unauthorized"}), 401)
    response.headers["WWW-Authenticate"] = "Bearer"
    return response


def requires_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        plugins = current_app.extensions["steel_pigs"]
        actor = plugins.auth.authenticate(request)
        if actor is None:
            return _unauthorized()
        g.actor = actor
        return view(*args, **kwargs)

    return wrapper

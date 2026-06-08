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

"""Bearer auth wiring.

APIFlask integrates HTTPTokenAuth with the OpenAPI security scheme
publishing: routes decorated with ``@auth.login_required`` show up as
``security: BearerAuth`` in the generated spec, and an unauthenticated
request returns a 401 with ``WWW-Authenticate: Bearer``.

``verify_token`` delegates to the configured auth plugin. The error
handler emits an audit event for every 401 (missing header, wrong
token, expired token) so the audit log is complete regardless of how
auth failed.
"""

from apiflask import HTTPTokenAuth
from flask import current_app, g, jsonify, request

from . import audit

auth = HTTPTokenAuth(scheme="Bearer", security_scheme_name="BearerAuth")


@auth.verify_token
def _verify_token(token):
    plugins = current_app.extensions["steel_pigs"]
    actor = plugins.auth.authenticate_token(token)
    if actor is None:
        return None
    g.actor = actor
    return actor


@auth.error_handler
def _auth_error(status_code):
    audit.emit(
        action="auth_failed",
        resource=request.path,
        actor=None,
        request_id=g.get("request_id"),
    )
    response = jsonify({"message": "Unauthorized"})
    response.status_code = status_code
    response.headers["WWW-Authenticate"] = "Bearer"
    return response

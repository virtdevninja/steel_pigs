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

"""Structured JSON audit logging for mutations and auth failures.

Each call to :func:`emit` writes one JSON object to the
``steel_pigs.audit`` logger. The default root logger config routes it
to stdout; deployers attach handlers (syslog, fluentbit, file) for
durable storage.

Fields:

* ``timestamp``  -- UTC ISO-8601 with millisecond precision.
* ``actor``      -- string id returned by the auth plugin, or ``None``
                    for unauthenticated events.
* ``action``     -- short verb-y name (e.g. ``set_boot_status``).
* ``resource``   -- subject of the action (e.g. ``server/555121``).
* ``before``     -- pre-mutation state, or ``None``.
* ``after``      -- post-mutation state, or ``None``.
* ``request_id`` -- per-request id from the ``X-Request-ID`` header
                    if supplied, else a generated uuid4.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("steel_pigs.audit")


def _strip_control(value):
    """Strip CR/LF from strings (recursing into dicts and lists).

    ``json.dumps`` below already escapes embedded newlines, so the final
    log line is single-line regardless. Stripping at the source is
    defense-in-depth, makes the sanitizer pattern explicit to static
    analysis (CWE-117 / py/log-injection), and protects callers that
    might later swap json.dumps for a non-escaping serializer.
    """
    if isinstance(value, str):
        return value.replace("\r", "").replace("\n", "")
    if isinstance(value, dict):
        return {k: _strip_control(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_control(v) for v in value]
    return value


def emit(action, resource, *, actor=None, before=None, after=None, request_id=None):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "actor": _strip_control(actor),
        "action": _strip_control(action),
        "resource": _strip_control(resource),
        "before": _strip_control(before),
        "after": _strip_control(after),
        "request_id": _strip_control(request_id),
    }
    logger.info(json.dumps(event, default=str))

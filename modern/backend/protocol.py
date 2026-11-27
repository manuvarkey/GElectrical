# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey
#
# Adapted from GEstimator modern/backend/__main__.py at 6ba679b (request
# envelope, limits and error style).

"""Desktop JSON Lines protocol: envelope, limits, error codes and JSON
encoding (docs/architecture/backend.md section 7).

* Request: ``{"id": "r-17", "session": "s-1", "method": "drawing.move",
  "params": {...}}``
* Response: ``{"id": "r-17", "result": ...}`` or ``{"id": "r-17",
  "error": {"code": ..., "message": ..., "field": ..., "details": ...}}``
* Event (no ``id``): ``{"event": "changed", ...}``
"""

import json
import math
import re

# Limits (initial values from GEstimator)
MAX_LINE_LENGTH = 2_000_000
MAX_ID_LENGTH = 100
MAX_ARRAY_LENGTH = 10_000
MAX_DEPTH = 64

# Error codes
INVALID_REQUEST = 'INVALID_REQUEST'
VALIDATION_ERROR = 'VALIDATION_ERROR'
NOT_FOUND = 'NOT_FOUND'
STALE_REVISION = 'STALE_REVISION'
CONFLICT = 'CONFLICT'
FILE_ERROR = 'FILE_ERROR'
JOB_ERROR = 'JOB_ERROR'
CANCELLED = 'CANCELLED'
BACKEND_ERROR = 'BACKEND_ERROR'

ERROR_CODES = (INVALID_REQUEST, VALIDATION_ERROR, NOT_FOUND, STALE_REVISION, CONFLICT,
               FILE_ERROR, JOB_ERROR, CANCELLED, BACKEND_ERROR)

EVENTS = ('changed', 'progress', 'job_finished', 'session_closed', 'mcp_status', 'log')

_SESSION_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


class ServiceError(Exception):
    """Structured error returned to the caller (never a traceback)"""

    def __init__(self, code, message, field=None, details=None):
        super().__init__(message)
        if code not in ERROR_CODES:
            raise ValueError('Unknown error code %r' % code)
        self.code = code
        self.message = message
        self.field = field
        self.details = details

    def to_dict(self):
        error = {'code': self.code, 'message': self.message}
        if self.field is not None:
            error['field'] = self.field
        if self.details is not None:
            error['details'] = json_safe(self.details)
        return error


def invalid(message, field=None):
    return ServiceError(INVALID_REQUEST, message, field=field)


def validation(message, field=None, details=None):
    return ServiceError(VALIDATION_ERROR, message, field=field, details=details)


def not_found(message, field=None):
    return ServiceError(NOT_FOUND, message, field=field)


def check_session_id(value):
    if not isinstance(value, str) or not _SESSION_RE.match(value):
        raise invalid('Invalid session id', field='session')
    return value


def _check_size(value, depth=0):
    if depth > MAX_DEPTH:
        raise invalid('Request nesting too deep')
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_LENGTH:
            raise invalid('Array too long')
        for item in value:
            _check_size(item, depth + 1)
    elif isinstance(value, dict):
        if len(value) > MAX_ARRAY_LENGTH:
            raise invalid('Object too large')
        for item in value.values():
            _check_size(item, depth + 1)


def parse_request(line):
    """Parse and validate one request line; returns
    ``(id, session, method, params)``. Raises ServiceError (INVALID_REQUEST);
    the error carries ``request_id`` when the id could be read."""
    if len(line) > MAX_LINE_LENGTH:
        raise invalid('Request too large')
    try:
        request = json.loads(line)
    except (ValueError, RecursionError):
        raise invalid('Request is not valid JSON') from None
    if not isinstance(request, dict):
        raise invalid('Expected a request object')
    identity = request.get('id')
    if not isinstance(identity, str) or not identity or len(identity) > MAX_ID_LENGTH:
        raise invalid('Expected a request id', field='id')
    try:
        method = request.get('method')
        params = request.get('params', {})
        session = request.get('session')
        if not isinstance(method, str) or not method:
            raise invalid('Expected a method name', field='method')
        if not isinstance(params, dict):
            raise invalid('Expected params object', field='params')
        if session is not None:
            check_session_id(session)
        _check_size(params)
    except ServiceError as error:
        error.request_id = identity
        raise
    return identity, session, method, params


def json_safe(value):
    """Plain JSON value: tuples become lists, NumPy scalars and arrays
    become Python numbers and lists, non-finite floats become ``None``
    (JSON has no NaN), dict keys become strings."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(v) for v in value]
    # NumPy and other number-like objects
    if hasattr(value, 'tolist'):
        return json_safe(value.tolist())
    if hasattr(value, 'item'):
        return json_safe(value.item())
    return str(value)


def encode(message):
    """One protocol line (without the newline)"""
    return json.dumps(json_safe(message), ensure_ascii=False, allow_nan=False)

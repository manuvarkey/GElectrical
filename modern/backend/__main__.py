# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey
#
# Adapted from GEstimator modern/backend/__main__.py at 6ba679b (JSON Lines
# loop and error mapping), with multiplexed responses and events.

"""Desktop backend process: ``python -m modern.backend``.

JSON Lines on stdin/stdout (docs/architecture/backend.md section 7).
Requests are queued to the owner thread as they arrive, so several may be
outstanding; responses are written when each finishes (possibly out of
order) and events are written as they happen. Diagnostics go to stderr and
to a log file in the user data directory (feature A22).

The protocol stream is a private copy of the original stdout; file
descriptor 1 is redirected to stderr so that prints from libraries cannot
corrupt the protocol.

Other modes: ``--write-schemas DIR`` (JSON Schemas), ``--print-methods``
(Markdown method table), ``--write-docs`` (update the table in
docs/architecture/backend-protocol.md).
"""

import argparse
import logging
import logging.handlers
import os
import sys
import threading

from .protocol import ServiceError, BACKEND_ERROR, FILE_ERROR, encode, parse_request

log = logging.getLogger('modern.backend')

DOC_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        'docs', 'architecture', 'backend-protocol.md')


def setup_logging(log_file=None, level=None):
    level = getattr(logging, (level or os.environ.get('GELECTRICAL_LOG_LEVEL', 'INFO')).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3,
                                                                encoding='utf-8')
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            log.exception('Log file could not be opened: %s', log_file)
    logging.captureWarnings(True)


def default_log_file():
    from .services.settings import default_user_data_dir
    return os.path.join(default_user_data_dir(), 'logs', 'gelectrical-backend.log')


def protocol_stream():
    """Private text stream for protocol output; fd 1 goes to stderr"""
    sys.stdout.flush()
    stdout_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    return os.fdopen(stdout_fd, 'w', encoding='utf-8', newline='\n')


def serve(stdin, stdout, runtime_factory=None):
    """Run the JSON Lines loop until ``shutdown`` or end of input"""
    lock = threading.Lock()

    def write(message):
        line = encode(message)
        with lock:
            stdout.write(line + '\n')
            stdout.flush()

    def respond(identity, future):
        try:
            message = {'id': identity, 'result': future.result()}
            encode(message)  # fail here (BACKEND_ERROR) rather than in write()
        except ServiceError as exc:
            message = {'id': identity, 'error': exc.to_dict()}
        except OSError as exc:
            message = {'id': identity, 'error': {'code': FILE_ERROR, 'message': str(exc)}}
        except Exception:
            log.exception('Backend request %s failed', identity)
            message = {'id': identity, 'error': {'code': BACKEND_ERROR,
                                                 'message': 'Operation failed; see backend log'}}
        try:
            write(message)
        except Exception:
            log.exception('Response %s could not be written', identity)

    if runtime_factory is None:
        from .runtime import Runtime
        runtime_factory = Runtime
    runtime = runtime_factory(emit=write)
    try:
        for line in stdin:
            if not line.strip():
                continue
            try:
                identity, session, method, params = parse_request(line)
            except ServiceError as exc:
                write({'id': getattr(exc, 'request_id', None), 'error': exc.to_dict()})
                continue
            if method == 'shutdown':
                write({'id': identity, 'result': True})
                break
            future = runtime.submit(method, params, session=session, source='desktop')
            future.add_done_callback(lambda f, identity=identity: respond(identity, f))
    finally:
        runtime.close()


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m modern.backend', description=__doc__.split('\n\n')[0])
    parser.add_argument('--write-schemas', metavar='DIR', help='write JSON Schemas and exit')
    parser.add_argument('--print-methods', action='store_true', help='print the method table and exit')
    parser.add_argument('--write-docs', metavar='FILE', nargs='?', const=DOC_PATH,
                        help='update the method table in the protocol documentation and exit')
    parser.add_argument('--log-file', help='log file (default: user data directory)')
    parser.add_argument('--no-log-file', action='store_true', help='log to stderr only')
    args = parser.parse_args(argv)
    if args.write_schemas:
        from .schemas import write_schemas
        for name in write_schemas(args.write_schemas):
            print(name)
        return 0
    if args.write_docs:
        from .registry import write_method_table
        write_method_table(args.write_docs)
        return 0
    if args.print_methods:
        from .registry import method_table_markdown
        sys.stdout.write(method_table_markdown())
        return 0

    out = protocol_stream()
    sys.stdin.reconfigure(encoding='utf-8')
    setup_logging(None if args.no_log_file else (args.log_file or default_log_file()))
    sys.modules.setdefault('gi', None)  # the backend never loads GTK
    log.info('Backend starting (pid %d)', os.getpid())
    try:
        serve(sys.stdin, out)
    finally:
        log.info('Backend stopped')
        out.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())

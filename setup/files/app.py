#!/usr/bin/env python3
"""ShopApp - tiny demo web service used as the 'production app' in every lab.

GET /         -> banner
GET /health   -> writes a heartbeat file to the data dir (atomic tmp+rename)
                 200 OK when storage is writable, 500 with the OS error otherwise
"""
import configparser
import http.server
import logging
import os
import socketserver
import sys
import time

CONFIG = os.environ.get("SHOPAPP_CONFIG", "/etc/shopapp/config.ini")

cfg = configparser.ConfigParser()
try:
    with open(CONFIG) as fh:
        cfg.read_file(fh)
except OSError as exc:
    print(f"FATAL: cannot read config {CONFIG}: {exc}", file=sys.stderr, flush=True)
    sys.exit(2)

PORT = cfg.getint("server", "port", fallback=8080)
DATA_DIR = cfg.get("storage", "data_dir", fallback="/srv/shopdata")
LOG_FILE = cfg.get("logging", "file", fallback="/var/log/shopapp/app.log")
TRACE = cfg.getboolean("debug", "trace_requests", fallback=False)

try:
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
except OSError as exc:
    print(f"FATAL: cannot open log file {LOG_FILE}: {exc}", file=sys.stderr, flush=True)
    sys.exit(3)

_trace_handles = []  # BUG (intentional): handles are never closed when tracing is on


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if TRACE:
            fh = open(os.path.join(DATA_DIR, "trace.log"), "a")
            fh.write(f"{time.time()} {self.path}\n")
            fh.flush()
            _trace_handles.append(fh)

        if self.path == "/health":
            tmp = os.path.join(DATA_DIR, f".heartbeat.{os.getpid()}.{time.time_ns()}")
            try:
                with open(tmp, "w") as fh:
                    fh.write(str(time.time()))
                os.replace(tmp, os.path.join(DATA_DIR, "heartbeat"))
                self._send(200, "OK\n")
            except OSError as exc:
                logging.error("health check failed: %s", exc)
                print(f"ERROR health check failed: {exc}", file=sys.stderr, flush=True)
                self._send(500, f"ERROR: {exc}\n")
        else:
            self._send(200, "shopapp is running\n")

    def _send(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        logging.info("%s %s", self.address_string(), fmt % args)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    try:
        srv = Server(("0.0.0.0", PORT), Handler)
    except OSError as exc:
        print(f"FATAL: cannot bind port {PORT}: {exc}", file=sys.stderr, flush=True)
        sys.exit(4)
    logging.info("shopapp listening on :%s (data=%s trace=%s)", PORT, DATA_DIR, TRACE)
    print(f"shopapp listening on :{PORT}", flush=True)
    srv.serve_forever()

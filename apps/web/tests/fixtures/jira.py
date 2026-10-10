"""Controlled Jira HTTP contract fixture for Playwright; never used by the app runtime."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

tickets = {}
lock = Lock()


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            return self.respond(200, {"mode": "controlled_test_fixture"})
        key = self.path.split("?")[0].rsplit("/", 1)[-1]
        with lock:
            ticket = tickets.get(key)
        self.respond(200 if ticket else 404, ticket or {"error": "not_found"})

    def do_POST(self):
        if self.path != "/rest/api/3/issue":
            return self.respond(404, {})
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with lock:
            key = f"OPS-{len(tickets) + 1}"
            tickets[key] = {
                "key": key,
                "fields": {
                    "summary": body["fields"]["summary"],
                    "project": {"key": "OPS"},
                },
            }
        self.respond(201, {"key": key})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()

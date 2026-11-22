"""api / worker / scheduler の仮プロセス。/healthz に応答するだけ。
本体の土台（Issue「バックエンドの土台を作る」）ができたら置き換える。"""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        ok = self.path == "/healthz"
        self.send_response(200 if ok else 404)
        self.end_headers()
        self.wfile.write(f"ok {os.environ.get('SERVICE_NAME', '')}\n".encode() if ok else b"not found\n")

    def log_message(self, *args):
        pass


HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler).serve_forever()

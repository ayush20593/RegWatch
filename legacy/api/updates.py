from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data_path = Path(__file__).resolve().parents[1] / "compliance_updates.json"
        try:
            updates = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            updates = []

        body = json.dumps(updates, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

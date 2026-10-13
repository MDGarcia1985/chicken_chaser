"""File: src/chicken_chaser/operator.py
Purpose: Local status/stop controls and an inspected upstream WebUI integration.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: loopback only, per-run request token, no competing camera capture.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-005.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
import secrets
import threading
from pathlib import Path
import tempfile
from .contracts import ROOT


def page(token):
    """Purpose: Serve token-bound local controls. Design: token never persisted in repo.
    Workflow: GET /. Data Handoff: escaped static HTML plus generated hex token.
    """
    return (ROOT / "assets/index.html").read_text().replace("__TOKEN__",token).encode()


def apply_action(runtime, value):
    """Purpose: Validate operator boundary. Design: closed small command record.
    Workflow: authorized POST. Data Handoff: accepted boolean or ValueError.
    """
    if not isinstance(value,dict) or set(value)-{"action","mode"} or "action" not in value:
        raise ValueError("Invalid control record")
    if value.get("mode","turn") not in ("turn","follow"):
        raise ValueError("Unsupported mode")
    return {"accepted": runtime.action(value["action"],value.get("mode","turn"))}


def serve(runtime, port=7000):
    """Purpose: Provide desktop fallback without Arduino dependencies.
    Design: loopback HTTP plus Host/Origin and random token checks; bounded body.
    Workflow: dry-run CLI. Data Handoff: server owner; caller shuts down and closes.
    """
    token = secrets.token_hex(32)

    class Handler(BaseHTTPRequestHandler):
        """Purpose: Expose local status and explicit simulation controls.
        Design: same policy as WebUI binding. Workflow: HTTP requests.
        Data Handoff: JSON responses; no direct motor API.
        """
        def reply(self, code, value, content_type="application/json"):
            """Purpose: Send bounded response. Design: no caching control token/status.
            Workflow: request completion. Data Handoff: UTF-8 response bytes.
            """
            data = value if isinstance(value,bytes) else json.dumps(value,allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            self.wfile.write(data)

        def local(self):
            """Purpose: Reject DNS rebinding/cross-site requests. Design: loopback Host
            and same-origin only. Workflow: every request. Data Handoff: boolean.
            """
            host = self.headers.get("Host","")
            allowed = {f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            return host in allowed and (origin is None or origin in {f"http://{h}" for h in allowed})

        def do_GET(self):
            """Purpose: Display status. Design: trusted loopback origin only.
            Workflow: browser polling. Data Handoff: HTML or status JSON.
            """
            if not self.local():
                self.reply(403,{"error":"local origin required"})
            elif self.path == "/":
                self.reply(200,page(token),"text/html; charset=utf-8")
            elif self.path == "/api/status":
                self.reply(200,runtime.status())
            else:
                self.reply(404,{"error":"not found"})

        def do_POST(self):
            """Purpose: Execute explicit operator action. Design: token + bounded JSON,
            stop is always available via valid local request. Workflow: control click.
            Data Handoff: acceptance or 4xx; no command backlog.
            """
            if not self.local() or not secrets.compare_digest(self.headers.get("X-Control-Token",""),token):
                self.reply(403,{"error":"local control token required"})
                return
            if self.path != "/api/control":
                self.reply(404,{"error":"not found"})
                return
            try:
                length = int(self.headers.get("Content-Length","0"))
                if not 0 < length <= 1024:
                    raise ValueError("Body must be 1..1024 bytes")
                self.connection.settimeout(1)
                value = json.loads(self.rfile.read(length))
                self.reply(200,apply_action(runtime,value))
            except (ValueError,TypeError,TimeoutError):
                self.reply(400,{"error":"invalid control request"})

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1",port),Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server


def install_webui(runtime, webui_class):
    """Purpose: Use Arduino WebUI when installed API matches inspected signature.
    Design: reject incompatible versions instead of falling back to 0.0.0.0;
    use REST on same assets. Workflow: optional App Lab dry-run setup after probe.
    Data Handoff: WebUI and temporary assets owner, both must be retained until exit.
    No video capture is opened; preview remains explicitly unavailable.
    """
    params = inspect.signature(webui_class).parameters
    if not {"addr","port","assets_dir_path","cors_origins"}.issubset(params):
        raise RuntimeError("Installed WebUI lacks required loopback/security configuration")
    from fastapi import Request
    from fastapi.responses import JSONResponse
    token = secrets.token_hex(32)
    (ROOT / "build").mkdir(exist_ok=True)
    assets = tempfile.TemporaryDirectory(prefix="chicken-chaser-ui-",dir=ROOT / "build")
    Path(assets.name,"index.html").write_bytes(page(token))
    ui = webui_class(addr="127.0.0.1",port=7000,assets_dir_path=assets.name,cors_origins="")

    async def control(request: Request):
        """Purpose: Validate WebUI controls. Design: loopback Host, Origin and token.
        Workflow: POST route. Data Handoff: HTTP JSON result or rejection.
        """
        host = request.headers.get("host","")
        origin = request.headers.get("origin")
        if (host not in ("127.0.0.1:7000","localhost:7000") or
            (origin is not None and origin not in ("http://127.0.0.1:7000","http://localhost:7000")) or
            not secrets.compare_digest(request.headers.get("x-control-token",""),token)):
            return JSONResponse({"error":"local control token required"},status_code=403)
        try:
            if not 0 < int(request.headers.get("content-length","0")) <= 1024:
                raise ValueError("Oversized body")
            return apply_action(runtime,await request.json())
        except (ValueError,TypeError):
            return JSONResponse({"error":"invalid control request"},status_code=400)

    def status():
        """Purpose: Expose read-only WebUI status. Design: no clock query argument.
        Workflow: REST GET. Data Handoff: current operator status.
        """
        return runtime.status()

    ui.expose_api("GET","/api/status",status)
    ui.expose_api("POST","/api/control",control)
    return ui,assets

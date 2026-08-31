#!/usr/bin/env python3
"""Local terminal-style control panel for CGV PDF exports."""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
EXPORTER = ROOT / "md_to_pdf.py"
DEFAULT_PATH = "/Users/johnwry/Nextcloud/Documents/GitHub/curriculo/25.1Pedro/slides/manual.md"
BUNDLED_PYTHON = Path(
    "/Users/johnwry/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
LABEL_LOCATIONS = ["top-center", "center", "lower-quarter", "bottom-center"]
LOGO_LOCATIONS = ["bottom-right", "bottom-left", "top-right", "top-left"]


def export_python() -> str:
    configured = os.environ.get("CGV_PDF_PYTHON", "").strip()
    if configured:
        return configured
    if BUNDLED_PYTHON.exists():
        return str(BUNDLED_PYTHON)
    return sys.executable


def parse_front_matter(markdown: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER_RE.match(markdown)
    if not match:
        return {}, markdown

    metadata: dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        clean_value = value.strip().strip('"').strip("'")
        metadata[key.strip().lower()] = clean_value
    return metadata, markdown[match.end() :]


def page_html(status: dict | None = None, form: dict | None = None) -> bytes:
    values = {
        "manual_path": DEFAULT_PATH,
        "label_color": "#111111",
        "label_location": "lower-quarter",
        "logo_location": "bottom-right",
        "logo_background": "70%",
        "body_size": "12.5",
        "variant": "both",
    }
    if form:
        values.update({key: form.get(key, values.get(key, "")) for key in values})

    metadata = read_metadata(values["manual_path"])
    status_markup = render_status(status)
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CGV PDF Builder</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #070b0a;
      --panel: #101916;
      --panel-2: #07100d;
      --line: #255848;
      --text: #d8f8df;
      --muted: #8cb69b;
      --green: #80d35f;
      --amber: #e4d06d;
      --red: #ff7b72;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(180deg, rgba(128, 211, 95, 0.07), transparent 34rem),
        var(--bg);
      color: var(--text);
      font: 18px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
    }}
    main {{
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0;
      color: var(--green);
      font-size: clamp(32px, 5vw, 58px);
      line-height: 1;
      letter-spacing: 0;
    }}
    .prompt {{ color: var(--amber); }}
    .stamp {{ color: var(--muted); font-size: 15px; }}
    .terminal {{
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(16, 25, 22, 0.95), rgba(7, 16, 13, 0.95));
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.32);
      border-radius: 8px;
      overflow: hidden;
    }}
    .bar {{
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(128, 211, 95, 0.08);
    }}
    .dot {{ width: 13px; height: 13px; border-radius: 50%; background: var(--muted); }}
    .dot:nth-child(1) {{ background: #ff6b6b; }}
    .dot:nth-child(2) {{ background: #e4d06d; }}
    .dot:nth-child(3) {{ background: #80d35f; }}
    form {{ padding: 22px; }}
    .grid {{
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 18px;
    }}
    .field {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 18px;
    }}
    label {{ color: var(--muted); font-size: 15px; }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #050907;
      color: var(--text);
      min-height: 48px;
      padding: 10px 12px;
      font: inherit;
    }}
    input[type="color"] {{
      padding: 4px;
      min-height: 48px;
    }}
    .row {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-top: 8px;
    }}
    button {{
      border: 1px solid #5ea94b;
      border-radius: 6px;
      background: #152d17;
      color: var(--text);
      min-height: 48px;
      padding: 10px 16px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ background: #1d3a20; }}
    .side {{
      border-left: 1px solid var(--line);
      padding-left: 18px;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.5;
    }}
    .status {{
      border-top: 1px solid var(--line);
      padding: 18px 22px;
      background: rgba(0, 0, 0, 0.18);
    }}
    .ok {{ color: var(--green); }}
    .err {{ color: var(--red); }}
    .paths a {{ color: var(--amber); text-decoration: none; }}
    .paths a:hover {{ text-decoration: underline; }}
    @media (max-width: 820px) {{
      header, .grid, .row {{ display: block; }}
      .side {{ border-left: 0; border-top: 1px solid var(--line); padding: 18px 0 0; }}
      h1 {{ margin-bottom: 10px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <div class="prompt">$ cgv-pdfbuilder</div>
        <h1>export manual</h1>
      </div>
      <div class="stamp">local session</div>
    </header>
    <section class="terminal">
      <div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
      <form method="post" action="/export">
        <div class="grid">
          <div>
            <div class="field">
              <label for="manual_path">manual.md</label>
              <input id="manual_path" name="manual_path" value="{esc(values['manual_path'])}">
            </div>
            <div class="row">
              <div class="field">
                <label for="label_color">label color</label>
                <input id="label_color" type="color" name="label_color" value="{esc(values['label_color'])}">
              </div>
              <div class="field">
                <label for="label_location">label location</label>
                {select("label_location", LABEL_LOCATIONS, values["label_location"])}
              </div>
            </div>
            <div class="row">
              <div class="field">
                <label for="logo_location">logo location</label>
                {select("logo_location", LOGO_LOCATIONS, values["logo_location"])}
              </div>
              <div class="field">
                <label for="logo_background">logo background</label>
                <input id="logo_background" name="logo_background" value="{esc(values['logo_background'])}">
              </div>
            </div>
            <div class="row">
              <div class="field">
                <label for="body_size">body size</label>
                <input id="body_size" name="body_size" value="{esc(values['body_size'])}">
              </div>
              <div class="field">
                <label for="variant">export</label>
                {select("variant", ["both", "student", "teacher"], values["variant"])}
              </div>
            </div>
            <div class="actions">
              <button type="submit">run export</button>
            </div>
          </div>
          <aside class="side">
            <pre>{esc(metadata)}</pre>
          </aside>
        </div>
      </form>
      {status_markup}
    </section>
  </main>
</body>
</html>"""
    return body.encode("utf-8")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def select(name: str, options: list[str], value: str) -> str:
    items = []
    for option in options:
        selected = " selected" if option == value else ""
        items.append(f'<option value="{esc(option)}"{selected}>{esc(option)}</option>')
    return f'<select id="{esc(name)}" name="{esc(name)}">' + "".join(items) + "</select>"


def read_metadata(manual_path: str) -> str:
    path = Path(manual_path).expanduser()
    if not path.exists():
        return "source: not found"
    try:
        metadata, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"source: unreadable\nerror: {exc}"
    if not metadata:
        return f"source: loaded\nexport python: {export_python()}\nfront matter: none"
    lines = ["source: loaded", f"export python: {export_python()}"]
    lines.extend(f"{key}: {value}" for key, value in metadata.items())
    return "\n".join(lines)


def render_status(status: dict | None) -> str:
    if not status:
        return ""
    css = "ok" if status.get("ok") else "err"
    lines = [f'<div class="status {css}"><pre>{esc(status.get("message", ""))}</pre>']
    paths = status.get("paths") or []
    if paths:
        links = []
        for path in paths:
            links.append(f'<a href="/open?path={esc(path)}">{esc(path)}</a>')
        lines.append('<div class="paths">' + "<br>".join(links) + "</div>")
    lines.append("</div>")
    return "".join(lines)


def normalize_form(data: dict[str, list[str]]) -> dict[str, str]:
    return {key: values[0] for key, values in data.items() if values}


def run_export(form: dict[str, str]) -> dict:
    manual_path = form.get("manual_path", DEFAULT_PATH).strip()
    if not manual_path:
        return {"ok": False, "message": "manual.md path is empty"}
    source = Path(manual_path).expanduser()
    if not source.exists():
        return {"ok": False, "message": f"source not found:\n{source}"}

    cmd = [
        export_python(),
        "-B",
        str(EXPORTER),
        str(source),
        "--label-color",
        form.get("label_color", "#111111"),
        "--label-location",
        form.get("label_location", "lower-quarter"),
        "--logo-location",
        form.get("logo_location", "bottom-right"),
        "--logo-background",
        form.get("logo_background", "70%"),
        "--body-size",
        form.get("body_size", "12.5"),
    ]
    variant = form.get("variant", "both")
    if variant in {"student", "teacher"}:
        cmd.extend(["--single", variant])

    try:
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception as exc:
        return {"ok": False, "message": f"export failed to start:\n{exc}"}

    output = result.stdout.strip()
    error = result.stderr.strip()
    paths = [line for line in output.splitlines() if line.strip().endswith(".pdf")]
    if result.returncode:
        return {"ok": False, "message": f"export failed:\n{error or output}", "paths": paths}
    return {"ok": True, "message": "export complete", "paths": paths}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.respond_json({"ok": True})
            return
        if parsed.path == "/open":
            query = parse_qs(parsed.query)
            path = (query.get("path") or [""])[0]
            self.serve_file(path)
            return
        self.respond_html(page_html())

    def do_POST(self) -> None:
        if self.path != "/export":
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        form = normalize_form(data)
        status = run_export(form)
        self.respond_html(page_html(status, form))

    def serve_file(self, raw_path: str) -> None:
        path = Path(raw_path).expanduser()
        if not path.exists() or path.suffix.lower() != ".pdf":
            self.send_error(404)
            return
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("content-type", "application/pdf")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def respond_html(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def respond_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"http://127.0.0.1:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

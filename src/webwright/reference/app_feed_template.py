"""Implementation skeleton for YAML-driven app/feed runs.

Copy this file into `final_runs/run_<id>/final_script.py`, then replace only the
task-specific configuration, `fetch_source_items`, optional sorting, and item
metadata. The full behavioral contract lives in `app_feed.yaml`.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Task-specific configuration. Replace these values for the concrete task.
# ---------------------------------------------------------------------------

APP_TITLE = "Example Feed"
APP_SHORT_NAME = "Feed"
APP_QUERY = "Latest matching information items from configured public sources"
ITEM_LIMIT = 40
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class SourceConfig:
    name: str
    url: str
    kind: str
    note: str = ""


SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(
        name="Example Source",
        url="https://example.com/",
        kind="html",
        note="Replace this source list with the user's fixed sources.",
    ),
)


# ---------------------------------------------------------------------------
# Paths, timestamps, logging, and schema helpers.
# ---------------------------------------------------------------------------

RUN_DIR = Path(__file__).resolve().parent
APP_DIR = RUN_DIR / "app"
SCREENSHOTS_DIR = RUN_DIR / "screenshots"
LOG_PATH = RUN_DIR / "final_script_log.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def reset_log() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")


def log(step: int, message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"step {step} action: {message}\n")


def source_status_rows() -> list[dict[str, Any]]:
    return [
        {"name": source.name, "url": source.url, "status": "ok", "item_count": 0}
        for source in SOURCES
    ]


def empty_feed(*, generated_at: str | None = None) -> dict[str, Any]:
    return {
        "title": APP_TITLE,
        "generated_at": generated_at or utc_now(),
        "query": APP_QUERY,
        "sources": source_status_rows(),
        "items": [],
        "errors": [],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (metadata or {}).items():
        normalized[str(key)] = "" if value is None else str(value)
    return normalized


def make_item(
    *,
    title: str,
    url: str,
    source: str,
    summary: str,
    published_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "title": str(title).strip() or "Untitled item",
        "url": str(url).strip(),
        "source": str(source).strip(),
        "published_at": published_at,
        "summary": str(summary).strip(),
        "metadata": normalize_metadata(metadata),
    }


def validate_feed(feed: dict[str, Any]) -> None:
    required_top = {"title", "generated_at", "query", "sources", "items", "errors"}
    missing_top = required_top - set(feed)
    if missing_top:
        raise ValueError(f"feed missing keys: {sorted(missing_top)}")
    if not isinstance(feed["sources"], list):
        raise ValueError("feed.sources must be a list")
    if not isinstance(feed["items"], list):
        raise ValueError("feed.items must be a list")
    if not isinstance(feed["errors"], list):
        raise ValueError("feed.errors must be a list")

    source_required = {"name", "url", "status", "item_count"}
    for index, source in enumerate(feed["sources"]):
        missing = source_required - set(source)
        if missing:
            raise ValueError(f"source {index} missing keys: {sorted(missing)}")
        if source["status"] not in ("ok", "error"):
            raise ValueError(f"source {source['name']} has invalid status {source['status']!r}")

    item_required = {"title", "url", "source", "published_at", "summary", "metadata"}
    for index, item in enumerate(feed["items"]):
        missing = item_required - set(item)
        if missing:
            raise ValueError(f"item {index} missing keys: {sorted(missing)}")
        if not isinstance(item["metadata"], dict):
            raise ValueError(f"item {index} metadata must be an object")

    error_required = {"source", "message"}
    for index, error in enumerate(feed["errors"]):
        missing = error_required - set(error)
        if missing:
            raise ValueError(f"error {index} missing keys: {sorted(missing)}")


# ---------------------------------------------------------------------------
# Network and extraction helpers. Replace fetch_source_items for each task.
# Browser-backed tasks may add lazy Playwright helpers here. Do not import or
# launch a browser at module import time; keep all browser work inside /run.
# ---------------------------------------------------------------------------


def fetch_text(url: str, *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Webwright app/feed mode",
            "Accept": "text/html,application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def clean_html(raw_html: str) -> str:
    raw_html = re.sub(r"<script\b.*?</script>", " ", raw_html, flags=re.I | re.S)
    raw_html = re.sub(r"<style\b.*?</style>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", raw_html)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def absolutize_url(base_url: str, maybe_url: str) -> str:
    return urllib.parse.urljoin(base_url, maybe_url)


def fetch_source_items(source: SourceConfig) -> list[dict[str, Any]]:
    """Fetch one configured source and return normalized feed items.

    Replace this placeholder with task-specific logic. Keep the return value as
    a list of `make_item(...)` dictionaries and let exceptions bubble up so the
    caller can record the source as an error without failing the entire app.
    """

    text = clean_html(fetch_text(source.url))
    title = text[:90] or source.name
    return [
        make_item(
            title=f"{source.name}: example item",
            url=source.url,
            source=source.name,
            summary=title,
            metadata={"source_kind": source.kind, "note": source.note},
        )
    ]


def sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort items for display.

    Replace or extend this if the task requires latest-first, cheapest-first,
    highest-rated, or another explicit ordering. Do not invent ranking when the
    task requires a site-provided sort/filter.
    """

    return items


def collect_feed(*, demo: str | None = None) -> dict[str, Any]:
    generated_at = utc_now()
    feed = empty_feed(generated_at=generated_at)

    if demo == "empty":
        for source in feed["sources"]:
            source["item_count"] = 0
        validate_feed(feed)
        write_json(APP_DIR / "feed.json", feed)
        log(60, "demo empty response generated with 0 items")
        return feed

    if demo == "error":
        for source in feed["sources"]:
            source["status"] = "error"
            source["item_count"] = 0
        feed["errors"].append(
            {"source": "Demo", "message": "Controlled error-state rendering check."}
        )
        validate_feed(feed)
        write_json(APP_DIR / "feed.json", feed)
        log(61, "demo error response generated with visible errors")
        return feed

    log(10, "/run started live multisite feed fetch")
    all_items: list[dict[str, Any]] = []

    for source, status_row in zip(SOURCES, feed["sources"], strict=True):
        started = time.time()
        try:
            items = fetch_source_items(source)
            status_row["status"] = "ok"
            status_row["item_count"] = len(items)
            all_items.extend(items)
            log(
                20,
                f"source={source.name} url={source.url} status=ok "
                f"item_count={len(items)} elapsed={time.time() - started:.1f}s",
            )
        except Exception as exc:
            status_row["status"] = "error"
            status_row["item_count"] = 0
            feed["errors"].append({"source": source.name, "message": str(exc)})
            log(
                21,
                f"source={source.name} url={source.url} status=error message={exc}",
            )

    feed["items"] = sort_items(all_items)[:ITEM_LIMIT]
    validate_feed(feed)
    write_json(APP_DIR / "feed.json", feed)
    log(
        30,
        f"/run finished source_count={len(feed['sources'])} "
        f"final_item_count={len(feed['items'])} error_count={len(feed['errors'])}",
    )
    return feed


# ---------------------------------------------------------------------------
# Static PWA assets.
# ---------------------------------------------------------------------------


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__APP_TITLE__</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Local Webwright PWA</p>
        <h1 id="title">__APP_TITLE__</h1>
      </div>
      <div class="toolbar">
        <button id="refresh" type="button" aria-label="Refresh feed">Refresh</button>
        <div class="stamp" id="updated">Waiting for latest run</div>
      </div>
    </header>

    <section class="status-band" aria-live="polite">
      <div class="loader" id="loader"></div>
      <div>
        <div class="status-title" id="statusTitle">Loading cached feed</div>
        <div class="status-copy" id="query">Preparing local app...</div>
      </div>
    </section>

    <section>
      <h2>Sources</h2>
      <div class="sources" id="sources"></div>
    </section>

    <section class="errors-wrap" id="errorsWrap" hidden>
      <h2>Errors</h2>
      <div id="errors"></div>
    </section>

    <section>
      <h2>Feed</h2>
      <div class="feed" id="feed"></div>
      <div class="empty" id="empty" hidden>No items matched this run. Check source statuses above.</div>
    </section>
  </main>
  <script src="/app.js"></script>
</body>
</html>
"""


STYLES_CSS = """
:root {
  color-scheme: light;
  --ink: #17202a;
  --muted: #5b6472;
  --line: #d9dee7;
  --panel: #ffffff;
  --page: #f5f7fb;
  --accent: #0f766e;
  --warn: #b42318;
  --ok-bg: #e8f5ef;
  --err-bg: #fff1f0;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--page);
}
a { color: #0b5cad; text-decoration: none; }
a:hover { text-decoration: underline; }
button {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--ink);
  font: inherit;
  cursor: pointer;
}
button:hover { border-color: var(--accent); color: var(--accent); }
.shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 48px; }
.topbar { display: flex; align-items: end; justify-content: space-between; gap: 20px; border-bottom: 1px solid var(--line); padding-bottom: 18px; }
.eyebrow { margin: 0 0 6px; color: var(--accent); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
h1 { margin: 0; font-size: clamp(32px, 5vw, 56px); line-height: 1; letter-spacing: 0; }
h2 { margin: 28px 0 12px; font-size: 18px; letter-spacing: 0; }
.toolbar { display: flex; gap: 12px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
.stamp { color: var(--muted); font-size: 14px; text-align: right; }
.status-band { margin-top: 22px; display: flex; gap: 14px; align-items: center; padding: 16px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }
.loader { width: 18px; height: 18px; border-radius: 50%; border: 3px solid #c4ccd8; border-top-color: var(--accent); animation: spin 1s linear infinite; flex: 0 0 auto; }
.loader.done { animation: none; border-color: var(--accent); background: var(--accent); }
@keyframes spin { to { transform: rotate(360deg); } }
.status-title { font-weight: 700; }
.status-copy { color: var(--muted); margin-top: 2px; }
.sources { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.source { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 112px; }
.source strong { display: block; margin-bottom: 8px; }
.pill { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 4px 8px; font-size: 12px; font-weight: 700; }
.pill.ok { background: var(--ok-bg); color: #116149; }
.pill.error { background: var(--err-bg); color: var(--warn); }
.count { margin-top: 10px; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
.errors-wrap { background: var(--err-bg); border: 1px solid #ffc9c4; border-radius: 8px; padding: 0 16px 14px; }
.error-item { color: var(--warn); padding: 8px 0; border-top: 1px solid #ffd7d3; }
.error-item:first-child { border-top: 0; }
.feed { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-height: 230px; display: flex; flex-direction: column; gap: 10px; }
.card h3 { margin: 0; font-size: 17px; line-height: 1.25; letter-spacing: 0; overflow-wrap: anywhere; }
.summary { color: var(--muted); line-height: 1.45; margin: 0; }
.meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: auto; }
.tag { background: #eef2f7; border: 1px solid #dce3ed; border-radius: 6px; padding: 5px 7px; font-size: 12px; color: #384253; overflow-wrap: anywhere; }
.card-footer { display: flex; justify-content: space-between; gap: 12px; align-items: center; color: var(--muted); font-size: 13px; }
.empty { background: var(--panel); border: 1px dashed #aab4c2; border-radius: 8px; padding: 24px; color: var(--muted); text-align: center; }
@media (max-width: 900px) {
  .sources, .feed { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 620px) {
  .shell { width: min(100% - 20px, 1180px); padding-top: 18px; }
  .topbar { align-items: start; flex-direction: column; }
  .toolbar { align-items: start; justify-content: flex-start; }
  .stamp { text-align: left; }
  .sources, .feed { grid-template-columns: 1fr; }
}
"""


APP_JS = """
const title = document.getElementById('title');
const updated = document.getElementById('updated');
const statusTitle = document.getElementById('statusTitle');
const query = document.getElementById('query');
const loader = document.getElementById('loader');
const sourcesEl = document.getElementById('sources');
const feedEl = document.getElementById('feed');
const errorsWrap = document.getElementById('errorsWrap');
const errorsEl = document.getElementById('errors');
const emptyEl = document.getElementById('empty');
const refresh = document.getElementById('refresh');

function text(value) {
  return value === null || value === undefined || value === '' ? 'Unavailable' : String(value);
}

function escapeHtml(value) {
  return text(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function setLoading(isLoading) {
  loader.classList.toggle('done', !isLoading);
  refresh.disabled = isLoading;
}

function render(feed, {cached = false} = {}) {
  title.textContent = feed.title || '__APP_TITLE__';
  updated.textContent = feed.generated_at ? `Updated ${new Date(feed.generated_at).toLocaleString()}` : 'Updated just now';
  statusTitle.textContent = `${cached ? 'Showing cached' : 'Collected'} ${(feed.items || []).length} items`;
  query.textContent = feed.query || '';

  sourcesEl.innerHTML = '';
  for (const source of feed.sources || []) {
    const el = document.createElement('article');
    el.className = 'source';
    const status = source.status === 'ok' ? 'ok' : 'error';
    el.innerHTML = `
      <strong>${escapeHtml(source.name)}</strong>
      <span class="pill ${status}">${status.toUpperCase()}</span>
      <div class="count">${escapeHtml(source.item_count || 0)} items</div>
      <div class="count"><a href="${escapeAttr(source.url)}" target="_blank" rel="noreferrer">Source link</a></div>
    `;
    sourcesEl.appendChild(el);
  }

  errorsEl.innerHTML = '';
  const errors = feed.errors || [];
  errorsWrap.hidden = errors.length === 0;
  for (const error of errors) {
    const el = document.createElement('div');
    el.className = 'error-item';
    el.textContent = `${text(error.source)}: ${text(error.message)}`;
    errorsEl.appendChild(el);
  }

  feedEl.innerHTML = '';
  const items = feed.items || [];
  emptyEl.hidden = items.length !== 0;
  for (const item of items) {
    const metadata = item.metadata || {};
    const card = document.createElement('article');
    card.className = 'card';
    const tags = Object.entries(metadata)
      .slice(0, 8)
      .map(([key, value]) => `<span class="tag">${escapeHtml(key)}: ${escapeHtml(value)}</span>`)
      .join('');
    card.innerHTML = `
      <div class="card-footer"><span>${escapeHtml(item.source)}</span><span>${escapeHtml(item.published_at)}</span></div>
      <h3>${escapeHtml(item.title)}</h3>
      <p class="summary">${escapeHtml(item.summary)}</p>
      <div class="meta">${tags}</div>
      <div class="card-footer"><a href="${escapeAttr(item.url)}" target="_blank" rel="noreferrer">Open original</a></div>
    `;
    feedEl.appendChild(card);
  }
}

async function fetchJson(endpoint) {
  const response = await fetch(endpoint, {cache: 'no-store'});
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json();
}

async function renderCachedFeed() {
  try {
    const cached = await fetchJson('/feed.json');
    if ((cached.items && cached.items.length) || (cached.sources && cached.sources.length) || (cached.errors && cached.errors.length)) {
      render(cached, {cached: true});
      query.textContent = `${cached.query || ''} - refreshing in background`;
      return true;
    }
  } catch (error) {
    console.warn('No cached feed available', error);
  }
  return false;
}

async function run({useCache = true} = {}) {
  const params = new URLSearchParams(window.location.search);
  const demo = params.get('demo');
  const endpoint = demo ? `/run?demo=${encodeURIComponent(demo)}` : '/run';
  const hasCachedFeed = demo || !useCache ? false : await renderCachedFeed();
  setLoading(true);
  try {
    const feed = await fetchJson(endpoint);
    render(feed);
    setLoading(false);
  } catch (error) {
    setLoading(false);
    if (hasCachedFeed && feedEl.children.length) {
      statusTitle.textContent = 'Showing cached feed; refresh failed';
      query.textContent = String(error);
    } else {
      statusTitle.textContent = 'Run failed';
      query.textContent = String(error);
      render({
        title: '__APP_TITLE__',
        generated_at: new Date().toISOString(),
        query: 'Fetch failed',
        sources: [],
        items: [],
        errors: [{source: 'local app', message: String(error)}]
      });
    }
  }
}

refresh.addEventListener('click', () => run({useCache: false}));
run();
"""


ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="24" fill="#0f766e"/>
  <path d="M28 42h72v44H28z" fill="#ffffff"/>
  <path d="M38 52h52v8H38zm0 16h32v8H38z" fill="#0f766e"/>
  <path d="M18 54h10v8H18zm0 18h10v8H18zm82-18h10v8h-10zm0 18h10v8h-10z" fill="#ffffff"/>
</svg>
"""


def render_asset(template: str) -> str:
    return template.replace("__APP_TITLE__", APP_TITLE)


def web_manifest() -> dict[str, Any]:
    return {
        "name": APP_TITLE,
        "short_name": APP_SHORT_NAME,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f5f7fb",
        "theme_color": "#0f766e",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }


def write_app_files() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "index.html").write_text(render_asset(INDEX_HTML), encoding="utf-8")
    (APP_DIR / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (APP_DIR / "app.js").write_text(render_asset(APP_JS), encoding="utf-8")
    write_json(APP_DIR / "manifest.webmanifest", web_manifest())
    (APP_DIR / "icon.svg").write_text(ICON_SVG, encoding="utf-8")
    if not (APP_DIR / "feed.json").exists():
        write_json(APP_DIR / "feed.json", empty_feed())
    log(2, f"app files generated at {APP_DIR}")


# ---------------------------------------------------------------------------
# Local HTTP server.
# ---------------------------------------------------------------------------


class FeedHandler(BaseHTTPRequestHandler):
    server_version = "WebwrightAppFeed/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        log(90, "http " + fmt % args)

    def send_json(self, payload: dict[str, Any], status: int = 200, *, body: bool = True) -> None:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if body:
            self.wfile.write(encoded)

    def send_static(self, target: Path, *, body: bool = True) -> None:
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".webmanifest": "application/manifest+json; charset=utf-8",
            ".svg": "image/svg+xml; charset=utf-8",
        }.get(target.suffix, "application/octet-stream")
        encoded = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if body:
            self.wfile.write(encoded)

    def resolve_static_path(self, request_path: str) -> Path | None:
        rel = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
        target = (APP_DIR / rel).resolve()
        app_root = APP_DIR.resolve()
        if target != app_root and app_root not in target.parents:
            return None
        return target

    def handle_request(self, *, body: bool) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/healthz":
            self.send_json({"ok": True, "title": APP_TITLE, "generated_at": utc_now()}, body=body)
            return
        if parsed.path == "/run":
            query = urllib.parse.parse_qs(parsed.query)
            demo = (query.get("demo") or [None])[0]
            try:
                self.send_json(collect_feed(demo=demo), body=body)
            except Exception as exc:
                log(31, f"/run failed message={exc}")
                self.send_json(
                    {
                        "title": APP_TITLE,
                        "generated_at": utc_now(),
                        "query": APP_QUERY,
                        "sources": source_status_rows(),
                        "items": [],
                        "errors": [{"source": "server", "message": str(exc)}],
                    },
                    status=500,
                    body=body,
                )
            return

        target = self.resolve_static_path(parsed.path)
        if target is None:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_static(target, body=body)

    def do_GET(self) -> None:
        self.handle_request(body=True)

    def do_HEAD(self) -> None:
        self.handle_request(body=False)


def serve(host: str, port: int) -> None:
    reset_log()
    write_app_files()
    httpd = ThreadingHTTPServer((host, port), FeedHandler)
    actual_port = httpd.server_address[1]
    url = f"http://{host}:{actual_port}/"
    log(1, f"server_url={url}")
    print(url, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log(99, "server stopped by KeyboardInterrupt")
    finally:
        httpd.server_close()


def run_once(*, demo: str | None = None, output_json: Path | None = None) -> dict[str, Any]:
    """Execute the reusable collection task once without starting the app server."""

    reset_log()
    write_app_files()
    feed = collect_feed(demo=demo)
    if output_json is not None:
        write_json(output_json, feed)
        log(40, f"run-once output_json={output_json}")
    log(
        41,
        f"run-once finished source_count={len(feed['sources'])} "
        f"item_count={len(feed['items'])} error_count={len(feed['errors'])}",
    )
    return feed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Webwright collection task once or start the local "
            "app/feed PWA. --run-once writes app/feed.json and prints JSON; "
            "the default starts a localhost UI whose /run endpoint executes "
            "the same collection task."
        )
    )
    parser.add_argument("--host", default="127.0.0.1", help="Local host/IP to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Local port to bind. Default: 0 chooses a free port")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Execute the collection task once, write app/feed.json, print JSON, and exit",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional extra JSON output path for --run-once",
    )
    parser.add_argument(
        "--demo",
        choices=("empty", "error"),
        help="Controlled demo state for verification; use only with --run-once or /run?demo=...",
    )
    parser.add_argument(
        "--write-app-only",
        action="store_true",
        help="Generate app files and feed.json, then exit without starting the server",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.demo and not args.run_once:
        raise SystemExit("--demo is only supported with --run-once; for the app use /run?demo=empty or /run?demo=error")
    if args.output_json and not args.run_once:
        raise SystemExit("--output-json is only supported with --run-once")
    if args.write_app_only:
        reset_log()
        write_app_files()
        print(APP_DIR)
        return 0
    if args.run_once:
        feed = run_once(demo=args.demo, output_json=args.output_json)
        print(json.dumps(feed, indent=2, ensure_ascii=False))
        return 0
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

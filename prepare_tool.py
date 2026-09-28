#!/usr/bin/env python3
"""Prepare a single-file HTML tool for Tool4That.

Usage:
  py prepare_tool.py SOURCE.html SLUG --name "Tool Name" --description "One or two sentences." [--icon "🔢"]

It refuses pages that aren't self-contained or safe. Otherwise it writes SLUG/index.html with:
  - a strict Content Security Policy that pins every inline <script> by SHA-256 (no 'unsafe-inline' scripts)
  - a description, canonical address, link-preview tags, and an emoji icon
  - a small "More free tools at Tool4That" link back to the hub
Re-running is safe: everything it adds sits between tool4that marker comments and is replaced.
Next: add the tool to tools.json, then run build_hub.py. Standard library only.
"""
import argparse, base64, hashlib, html, json, re, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))["site"].rstrip("/")

BLOCKERS = [
    (r'<script\b[^>]*\bsrc\s*=\s*["\']?(?:https?:)?//', "loads a script from another site"),
    (r'<link\b(?=[^>]*rel\s*=\s*["\']?stylesheet)(?=[^>]*href\s*=\s*["\']?(?:https?:)?//)', "loads a stylesheet from another site"),
    (r'@import\s+(?:url\()?\s*["\']?(?:https?:)?//', "imports CSS from another site"),
    (r'<(?:img|iframe|video|audio|source|embed|object)\b[^>]*\bsrc\s*=\s*["\']?(?:https?:)?//', "loads media from another site"),
    (r'\bfetch\s*\(|XMLHttpRequest|new\s+WebSocket|EventSource\s*\(|sendBeacon', "makes network requests"),
    (r'<[a-z][^<>]*\son[a-z]+\s*=\s*["\']', "uses inline event handlers (onclick=...), which the policy blocks"),
    (r'href\s*=\s*["\']\s*javascript:', "uses javascript: links"),
    (r'\beval\s*\(|new\s+Function\s*\(|set(?:Timeout|Interval)\s*\(\s*["\']', "runs code from strings"),
    (r'window\.(?:claude|storage|fs)\b', "uses claude.ai-only artifact features"),
    (r'new\s+(?:Shared)?Worker\s*\(', "starts a web worker (blocked by the policy)"),
]
MARK = re.compile(r"<!-- tool4that:(head|foot) -->[\s\S]*?<!-- /tool4that:\1 -->\n?")


def executable_scripts(page):
    """Bodies of inline scripts the browser will run (skips src= scripts and data blocks like JSON-LD)."""
    out = []
    for m in re.finditer(r"<script\b([^>]*)>([\s\S]*?)</script\s*>", page, re.I):
        attrs, body = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue
        t = re.search(r"\btype\s*=\s*[\"']?([^\"'\s>]+)", attrs, re.I)
        if t and t.group(1).lower() not in ("text/javascript", "application/javascript", "module"):
            continue
        out.append(body)
    return out


def sha256_csp(body):
    # Browsers hash the script text after the HTML parser normalizes CRLF/CR to LF.
    norm = body.replace("\r\n", "\n").replace("\r", "\n")
    return "'sha256-" + base64.b64encode(hashlib.sha256(norm.encode("utf-8")).digest()).decode() + "'"


def main():
    ap = argparse.ArgumentParser(description="Prepare a single-file HTML tool for Tool4That.")
    ap.add_argument("source"); ap.add_argument("slug")
    ap.add_argument("--name", required=True); ap.add_argument("--description", required=True)
    ap.add_argument("--icon", default="🧰", help="one emoji for the browser tab icon")
    ap.add_argument("--force", action="store_true", help="write the page even if checks fail (review the warnings!)")
    a = ap.parse_args()

    page = MARK.sub("", Path(a.source).read_text(encoding="utf-8"))
    page = re.sub(r'<meta\s+http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*>\s*', "", page, flags=re.I)
    problems = [why for rx, why in BLOCKERS if re.search(rx, page, re.I)]
    for why in problems:
        print(f"CHECK FAILED: the page {why}.")
    if problems and not a.force:
        sys.exit("Not written. Make the page self-contained, or re-run with --force after reviewing.")
    if not re.search(r"<head\b[^>]*>", page, re.I) or not re.search(r"</body\s*>", page, re.I):
        sys.exit("Not written: the page needs <head> and </body>.")

    slug = a.slug.strip("/")
    url = f"{SITE}/{slug}/"
    hashes = sorted({sha256_csp(b) for b in executable_scripts(page)})
    csp = "default-src 'none'; " + (f"script-src {' '.join(hashes)}; " if hashes else "") + \
          "style-src 'unsafe-inline'; img-src data:; font-src data:; base-uri 'none'; form-action 'none'"
    icon = "data:image/svg+xml," + urllib.parse.quote(
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>{a.icon}</text></svg>", safe="")
    e = lambda s: html.escape(s, quote=True)
    tags = [f'<meta http-equiv="Content-Security-Policy" content="{csp}">', '<meta name="referrer" content="no-referrer">']
    if not re.search(r'<meta\s+name\s*=\s*["\']description', page, re.I):
        tags.append(f'<meta name="description" content="{e(a.description)}">')
    tags += [f'<link rel="canonical" href="{url}">']
    if not re.search(r'rel\s*=\s*["\'](?:shortcut\s+)?icon', page, re.I):
        tags.append(f'<link rel="icon" href="{icon}">')
    tags += [f'<meta property="og:type" content="website">', f'<meta property="og:site_name" content="Tool4That">',
             f'<meta property="og:title" content="{e(a.name)}">', f'<meta property="og:description" content="{e(a.description)}">',
             f'<meta property="og:url" content="{url}">', f'<meta property="og:image" content="{SITE}/og-image.png">',
             '<meta name="twitter:card" content="summary_large_image">']
    block = "<!-- tool4that:head -->\n" + "\n".join(tags) + "\n<!-- /tool4that:head -->\n"
    cm = re.search(r"<meta\s+charset[^>]*>\s*", page, re.I) or re.search(r"<head\b[^>]*>\s*", page, re.I)
    page = page[:cm.end()] + block + page[cm.end():]
    home = "../" * len(slug.split("/"))
    foot = ('<!-- tool4that:foot --><p style="text-align:center;margin:28px 0 22px;font:14px/1.4 system-ui,-apple-system,Segoe UI,Arial,sans-serif">'
            f'<a href="{home}">More free tools at Tool4That</a></p><!-- /tool4that:foot -->\n')
    body_end = list(re.finditer(r"</body\s*>", page, re.I))[-1]
    page = page[:body_end.start()] + foot + page[body_end.start():]

    out = ROOT / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
    print(f"Wrote {out.relative_to(ROOT)}: {len(hashes)} script(s) pinned, {len(page.encode()):,} bytes.")
    print('Next: add it to tools.json (leave "sha256" and "updated" empty), then run build_hub.py.')


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Rebuild the Tool4That hub from tools.json: index.html, 404.html, robots.txt, sitemap.xml.

Usage:  python3 build_hub.py
Each tool's size and SHA-256 are computed from its file; "updated" changes only when the file changes.
Standard library only.
"""
import datetime, hashlib, html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG_PATH = ROOT / "tools.json"
cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
SITE = cfg["site"].rstrip("/")
TODAY = datetime.date.today().isoformat()
e = html.escape

ICONS = {
    "check": '<path d="M9 16.5l4.6 4.6L23 11.4" fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>',
    "wrench": '<path d="M20.5 7.5a5 5 0 0 0-6.3 6.3l-6.4 6.4a1.8 1.8 0 0 0 2.5 2.5l6.4-6.4a5 5 0 0 0 6.3-6.3l-3 3-2.6-.9-.9-2.6z" fill="#fff"/>',
    "terminal": '<path d="M8.5 10.5l5.5 5.5-5.5 5.5" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M16.5 22h7.5" stroke="#fff" stroke-width="3" stroke-linecap="round"/>',
    "search": '<circle cx="14" cy="14" r="6.5" fill="none" stroke="#fff" stroke-width="3"/><path d="M19 19l5.5 5.5" stroke="#fff" stroke-width="3.2" stroke-linecap="round"/>',
    "subnet": '<text x="16" y="20.5" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="12" fill="#fff">/24</text>',
}
def mark(icon="four", size=32):
    glyph = ICONS.get(icon) or '<text x="16" y="23.5" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="21" fill="#fff">4</text>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="{size}" height="{size}" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#0A7552"/>{glyph}</svg>'
FAVICON = "data:image/svg+xml," + mark().replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'"
STYLE = """
:root { --paper:#EEF2EF; --sheet:#FAFBF9; --ink:#13223A; --ink-2:#3D5068; --muted:#5E6F7F; --rule:#C6D1CC; --go:#0A7552; --go-2:#3CC48F; --go-soft:#D6EEE3; --focus:#1D5FD1;
  --font: "Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Ubuntu,"Noto Sans",Arial,sans-serif; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.5 var(--font); }
a { color: var(--focus); }
.wrap { max-width: 1040px; margin: 0 auto; padding-left: 20px; padding-right: 20px; }
.hero { background: var(--ink); color: #fff; padding: 44px 0 52px; }
.logo { display: flex; align-items: center; gap: 12px; margin: 0 0 26px; font-size: 26px; font-weight: 800; letter-spacing: -0.01em; }
.logo b { color: var(--go-2); }
.hero h1 { margin: 0; font-size: clamp(30px, 5vw, 46px); line-height: 1.1; letter-spacing: -0.02em; max-width: 20ch; }
.lede { margin: 16px 0 0; font-size: 18px; color: #D6DEE8; max-width: 60ch; }
.points { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0 0; padding: 0; list-style: none; }
.points li { border: 1.5px solid #3D5068; border-radius: 999px; padding: 5px 14px; font-size: 14px; color: #E6ECF3; }
.points li::before { content: "\\2713  "; color: var(--go-2); font-weight: 700; }
main { padding: 34px 0 20px; }
h2 { font-size: 22px; margin: 0 0 14px; }
.cat { font-size: 17px; margin: 26px 0 4px; color: var(--ink-2); }
h2 + .cat { margin-top: 6px; }
.cat-note { margin: 0 0 12px; font-size: 14px; color: var(--muted); max-width: 75ch; }
.tools { list-style: none; margin: 0 0 34px; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.tool { background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.tool-head { display: flex; gap: 12px; align-items: center; }
.tool-head svg { flex: none; }
.tool h3 { margin: 0; font-size: 19px; line-height: 1.2; }
.tool h3 a { color: var(--ink); text-decoration: none; }
.tool h3 a:hover { text-decoration: underline; }
.tagline { margin: 2px 0 0; color: var(--go); font-weight: 700; font-size: 14.5px; }
.tool p.desc { margin: 0; color: var(--ink-2); font-size: 15px; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }
.badges li { background: var(--go-soft); color: var(--go); border-radius: 4px; padding: 2px 8px; font-size: 12.5px; font-weight: 700; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: auto; }
.btn { display: inline-block; border: 1.5px solid var(--ink); border-radius: 5px; padding: 8px 16px; font-weight: 700; font-size: 15px; text-decoration: none; color: var(--ink); background: #fff; }
.btn.primary { background: var(--ink); color: #fff; }
.btn:hover { filter: brightness(1.08); }
.meta { margin: 0; font-size: 12.5px; color: var(--muted); }
.meta code { display: block; margin-top: 3px; font: 11.5px/1.4 ui-monospace, "SF Mono", Consolas, "DejaVu Sans Mono", monospace; overflow-wrap: anywhere; color: var(--ink-2); }
.soon { border-style: dashed; justify-content: center; align-items: center; text-align: center; color: var(--muted); min-height: 140px; }
.how ul { margin: 0 0 28px; padding-left: 20px; max-width: 75ch; }
.how li { margin: 8px 0; }
.how code { font: 13.5px ui-monospace, Consolas, "DejaVu Sans Mono", monospace; background: var(--sheet); border: 1px solid var(--rule); border-radius: 3px; padding: 1px 5px; }
footer { border-top: 1px solid var(--rule); padding: 18px 0 30px; font-size: 13px; color: var(--muted); }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
@media (prefers-color-scheme: dark) {
  :root { --paper:#0F1826; --sheet:#152234; --ink:#E6ECF3; --ink-2:#B9C6D6; --muted:#93A3B5; --rule:#2A3B52; --go-soft:#123A2C; --focus:#7FB0FF; }
  .hero { background: #0B1320; }
  .btn { background: var(--sheet); color: var(--ink); border-color: var(--ink-2); }
  .btn.primary { background: var(--go); border-color: var(--go); color: #fff; }
  .badges li, .tagline { color: var(--go-2); }
}
"""

def head(title, desc, url, image):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="no-referrer">
<meta name="color-scheme" content="light dark">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(cfg['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>{STYLE}</style>
</head>
"""

def tool_card(t):
    f = ROOT / t["file"]
    data = f.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != t.get("sha256"):
        t["sha256"], t["updated"] = sha, TODAY
    kb = max(1, round(len(data) / 1024))
    badges = "".join(f"<li>{e(b)}</li>" for b in t.get("badges", []))
    return f"""      <li class="tool">
        <div class="tool-head">{mark(t.get('icon', 'four'), 44)}<div><h3><a href="{e(t['slug'])}/">{e(t['name'])}</a></h3><p class="tagline">{e(t['tagline'])}</p></div></div>
        <p class="desc">{e(t['description'])}</p>
        <ul class="badges" aria-label="Tags">{badges}</ul>
        <div class="actions"><a class="btn primary" href="{e(t['slug'])}/">Open</a><a class="btn" href="{e(t['file'])}" download="{e(t['download_as'])}">Download .html</a></div>
        <p class="meta">Updated {t['updated']} &middot; {kb} KB &middot; SHA-256<code>{sha}</code></p>
      </li>
"""

groups = []
for t in cfg["tools"]:
    c = t.get("category", "")
    g = next((g for g in groups if g[0] == c), None)
    if g is None:
        groups.append((c, [t]))
    else:
        g[1].append(t)
notes = cfg.get("category_notes", {})
sections = ""
for c, ts in groups:
    if c:
        sections += f'    <h3 class="cat">{e(c)}</h3>\n' + (f'    <p class="cat-note">{e(notes[c])}</p>\n' if notes.get(c) else "")
    sections += '    <ul class="tools">\n' + "".join(tool_card(t) for t in ts) + "    </ul>\n"
title = f"{cfg['name']}: free tools that run in your browser"
desc = "Need a tool for that? Free single-file tools that run in your browser, with no sign-up and no tracking: military TSP planning and networking practice."
index = head(title, desc, SITE + "/", SITE + "/og-image.png") + f"""<body>
<header class="hero">
  <div class="wrap">
    <p class="logo">{mark(size=40)}<span>Tool<b>4</b>That</span></p>
    <h1>Need a tool for that? There's a {e(cfg['name'])}.</h1>
    <p class="lede">Free, single-file tools that run entirely in your browser. Open them here, or download one and use it offline.</p>
    <ul class="points"><li>No sign-ups</li><li>No tracking</li><li>Nothing uploaded</li><li>Free</li></ul>
  </div>
</header>
<main class="wrap">
  <section aria-labelledby="h-tools">
    <h2 id="h-tools">Tools</h2>
{sections}
  </section>
  <section class="how" aria-labelledby="h-how">
    <h2 id="h-how">How these tools work</h2>
    <ul>
      <li><b>One file each.</b> Open a tool here, or download it and run it from your computer, even offline.</li>
      <li><b>Private by design.</b> Your data stays in your browser. Each tool says exactly what it keeps.</li>
      <li><b>Check your download.</b> Each tool lists its SHA-256 fingerprint. Compare it with <code>sha256sum FILE</code> (Linux), <code>shasum -a 256 FILE</code> (Mac), or <code>certutil -hashfile FILE SHA256</code> (Windows).</li>
      <li><b>Built with AI.</b> Tools are made with AI assistance and tested before release.</li>
    </ul>
  </section>
</main>
<footer>
  <div class="wrap">Independent projects, free to use. Not affiliated with any government agency. Planning aids, not professional advice.</div>
</footer>
</body>
</html>
"""
(ROOT / "index.html").write_text(index, encoding="utf-8", newline="\n")

notfound = head(f"Page not found | {cfg['name']}", "That page doesn't exist.", SITE + "/", SITE + "/og-image.png").replace('<link rel="canonical"', '<meta name="robots" content="noindex">\n<link rel="canonical"') + f"""<body>
<header class="hero"><div class="wrap"><p class="logo">{mark(size=40)}<span>Tool<b>4</b>That</span></p><h1>That page isn't here.</h1>
<p class="lede"><a href="{SITE}/" style="color:#fff">Back to all tools</a></p></div></header>
</body>
</html>
"""
(ROOT / "404.html").write_text(notfound, encoding="utf-8", newline="\n")
(ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8", newline="\n")
urls = [(SITE + "/", max([TODAY] + [t["updated"] for t in cfg["tools"]]))] + [(f"{SITE}/{t['slug']}/", t["updated"]) for t in cfg["tools"]]
(ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n", encoding="utf-8", newline="\n")
(ROOT / ".nojekyll").touch()
CFG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8", newline="\n")
for t in cfg["tools"]:
    print(f"{t['slug']:<24} {t['updated']}  {t['sha256']}")
print(f"hub rebuilt for {SITE}")

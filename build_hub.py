#!/usr/bin/env python3
"""Rebuild the Tool4That hub from tools.json: index.html, all/, one page per category and per series, 404.html, robots.txt, sitemap.xml.

Usage:  python3 build_hub.py
Each tool's size and SHA-256 are computed from its file; "updated" changes only when the file changes.
An extra that is a second .html download (e.g. an offline edition) gets its own size, SHA-256, and date the same way.
A series (tools.json "series") groups tools inside a category and gets its own page at /<series-slug>/.
Standard library only.
"""
import datetime, hashlib, html, json, sys
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
    "dollar": '<text x="16" y="23" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="20" fill="#fff">$</text>',
    "chart": '<rect x="7" y="17" width="4.5" height="8" fill="#fff"/><rect x="13.8" y="11" width="4.5" height="14" fill="#fff"/><rect x="20.5" y="7" width="4.5" height="18" fill="#fff"/>',
    "subnet": '<text x="16" y="20.5" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="12" fill="#fff">/24</text>',
    "lock": '<path d="M11.2 15v-3.4a4.8 4.8 0 0 1 9.6 0V15" fill="none" stroke="#fff" stroke-width="2.8"/><rect x="8.5" y="14.5" width="15" height="11" rx="2" fill="#fff"/><circle cx="16" cy="19.4" r="1.8" fill="#0A7552"/><rect x="15.2" y="19.8" width="1.6" height="3.4" fill="#0A7552"/>',
    "path": '<path d="M6 25h5.5v-6h5.5v-6H23V7" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
    "screen": '<rect x="6.5" y="8" width="19" height="13" rx="1.6" fill="none" stroke="#fff" stroke-width="2.6"/><path d="M12.5 25h7M16 21v4" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>',
    "map": '<path d="M6.5 9.5l6.3-2.5 6.4 2.5 6.3-2.5v15.5l-6.3 2.5-6.4-2.5-6.3 2.5z" fill="none" stroke="#fff" stroke-width="2.4" stroke-linejoin="round"/><path d="M12.8 7v15.5M19.2 9.5V25" stroke="#fff" stroke-width="2.4"/>',
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
footer a { color: inherit; }
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
.tiles { list-style: none; margin: 0 0 10px; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.tile a { display: flex; gap: 16px; align-items: center; padding: 22px; background: var(--sheet); border: 1px solid var(--rule); border-radius: 10px; text-decoration: none; color: var(--ink); min-height: 100%; }
.tile a:hover { border-color: var(--go); box-shadow: 0 6px 24px rgba(0,0,0,.08); }
.tile svg { flex: none; }
.tile-body { display: grid; gap: 4px; }
.tile-t { font-size: 20px; font-weight: 800; line-height: 1.15; }
.tile-s { color: var(--ink-2); font-size: 15px; }
.tile-n { color: var(--go); font-weight: 700; font-size: 14px; margin-top: 4px; }
.all-link { margin: 4px 0 30px; font-size: 14px; color: var(--ink-2); }
.hero.small { padding: 26px 0 30px; }
.hero.small h1 { font-size: clamp(26px, 4vw, 36px); }
.crumb { margin: 0 0 14px; font-size: 14px; }
.crumb a { color: #B9C6D6; text-decoration: none; }
.crumb a:hover { color: #fff; text-decoration: underline; }
.logo a { color: inherit; text-decoration: none; display: inline-flex; align-items: center; gap: 12px; }
.cat { font-size: 17px; margin: 26px 0 4px; color: var(--ink-2); }
h2 + .cat { margin-top: 6px; }
.cat-note { margin: 0 0 12px; font-size: 14px; color: var(--muted); max-width: 75ch; }
.section-h { font-size: 25px; font-weight: 800; letter-spacing: -0.015em; margin: 40px 0 2px; padding-bottom: 9px; border-bottom: 2px solid var(--go); }
main section > .section-h:first-of-type { margin-top: 4px; }
.section-intro { margin: 10px 0 16px; font-size: 15.5px; color: var(--ink-2); max-width: 72ch; }
.tools { list-style: none; margin: 0 0 34px; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.tool { background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.tool-head { display: flex; gap: 12px; align-items: center; }
.tool-head svg { flex: none; }
.tool .tool-name { margin: 0; font-size: 19px; line-height: 1.2; }
.tool .tool-name a { color: var(--ink); text-decoration: none; }
.tool .tool-name a:hover { text-decoration: underline; }
.series-h { font-size: 20px; margin: 30px 0 4px; }
section > .series-h:first-child { margin-top: 0; }
.series-h a { color: var(--ink); }
.count { margin-left: 10px; font-size: 14px; font-weight: 600; color: var(--muted); }
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

def refresh(t):
    data = (ROOT / t["file"]).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != t.get("sha256"):
        t["sha256"], t["updated"] = sha, TODAY
    t["_kb"] = max(1, round(len(data) / 1024))

def html_extras(t): return [x for x in t.get("extras", []) if x["file"].lower().endswith(".html")]
def size(kb): return f"{kb} KB" if kb < 1024 else f"{kb / 1024:.1f} MB"
# A card with a second .html download lists one meta line per file; SHA&#8209;256 uses a non-breaking hyphen, so the
# label stays on one line next to its fingerprint.

def tool_card(t, base, lvl=3):
    badges = "".join(f"<li>{e(b)}</li>" for b in t.get("badges", []))
    extras = "".join(f'<a class="btn" href="{base}{e(x["file"])}" download="{e(x.get("download_as") or Path(x["file"]).name)}">{e(x["label"])}</a>' for x in t.get("extras", []))
    label = t.get("download_label", "Download .html")
    note = f'        <p class="desc">{e(t["download_note"])}</p>\n' if t.get("download_note") else ""
    if html_extras(t):
        meta = '</p>\n        <p class="meta">'.join(f'{e(lab)} &middot; Updated {x["updated"]} &middot; {size(x["_kb"])} &middot; SHA&#8209;256<code>{x["sha256"]}</code>'
                       for lab, x in [(label, t)] + [(x["label"], x) for x in html_extras(t)])
    else:
        meta = f"Updated {t['updated']} &middot; {t['_kb']} KB &middot; SHA-256<code>{t['sha256']}</code>"
    return f"""      <li class="tool">
        <div class="tool-head">{mark(t.get('icon', 'four'), 44)}<div><h{lvl} class="tool-name"><a href="{base}{e(t['slug'])}/">{e(t['name'])}</a></h{lvl}><p class="tagline">{e(t['tagline'])}</p></div></div>
        <p class="desc">{e(t['description'])}</p>
        <ul class="badges" aria-label="Tags">{badges}</ul>
        <div class="actions"><a class="btn primary" href="{base}{e(t['slug'])}/">Open</a><a class="btn" href="{base}{e(t['file'])}" download="{e(t['download_as'])}">{e(label)}</a>{extras}</div>
{note}        <p class="meta">{meta}</p>
      </li>
"""

CATS = cfg["categories"]
SERIES = cfg.setdefault("series", [])
SECTIONS = cfg.setdefault("sections", [])
CAT_SLUGS, SER_SLUGS = {c["slug"] for c in CATS}, {s["slug"] for s in SERIES}
SEC_KEYS = {(sec["category"], sec["slug"]) for sec in SECTIONS}
problems = []
for sec in SECTIONS:
    if sec.get("category") not in CAT_SLUGS: problems.append(f'section "{sec.get("slug")}": unknown category "{sec.get("category")}"')
for s in SERIES:
    if s.get("category") not in CAT_SLUGS: problems.append(f'series "{s["slug"]}": unknown category "{s.get("category")}"')
    if "/" in s["slug"] or s["slug"] in CAT_SLUGS | {"all"}: problems.append(f'series "{s["slug"]}": slug must be one folder name, not a category or "all"')
    if s.get("section") and (s.get("category"), s["section"]) not in SEC_KEYS: problems.append(f'series "{s["slug"]}": unknown section "{s.get("section")}" in its category')
def sectioned_cat(cat): return any(sec["category"] == cat for sec in SECTIONS)
for t in cfg["tools"]:
    if t["slug"] in CAT_SLUGS | SER_SLUGS | {"all"}: problems.append(f'tool "{t["slug"]}": slug is a reserved folder name')
    if t.get("category") not in CAT_SLUGS: problems.append(f'tool "{t["slug"]}": unknown category "{t.get("category")}"')
    if t.get("series") and t["series"] not in SER_SLUGS: problems.append(f'tool "{t["slug"]}": unknown series "{t["series"]}"')
    elif t.get("series") and next(s for s in SERIES if s["slug"] == t["series"])["category"] != t.get("category"): problems.append(f'tool "{t["slug"]}": its series belongs to another category')
    if t.get("section") and (t.get("category"), t["section"]) not in SEC_KEYS: problems.append(f'tool "{t["slug"]}": unknown section "{t.get("section")}" in its category')
    if sectioned_cat(t.get("category")) and not t.get("series"):
        if not t.get("section"): problems.append(f'tool "{t["slug"]}": category "{t.get("category")}" uses sections, so this loose tool needs a "section"')
    for f in [t["file"]] + [x["file"] for x in t.get("extras", [])]:
        if not (ROOT / f).is_file(): problems.append(f'tool "{t["slug"]}": file not found: {f}')
for s in SERIES:
    if sectioned_cat(s.get("category")) and not s.get("section"): problems.append(f'series "{s["slug"]}": category "{s.get("category")}" uses sections, so this series needs a "section"')
if problems:
    sys.exit("tools.json problems, nothing written:\n  " + "\n  ".join(problems))
for t in cfg["tools"]:
    refresh(t)
    for x in html_extras(t):
        refresh(x)
def tools_in(slug): return [t for t in cfg["tools"] if t.get("category") == slug]
def in_series(slug): return [t for t in cfg["tools"] if t.get("series") == slug]
def series_in(cat): return [s for s in SERIES if s["category"] == cat and in_series(s["slug"])]
def loose_in(cat, sec=None): return [t for t in cfg["tools"] if t.get("category") == cat and not t.get("series") and (sec is None or t.get("section") == sec)]
def series_in_sec(cat, sec): return [s for s in SERIES if s["category"] == cat and s.get("section") == sec and in_series(s["slug"])]
def sections_in(cat): return [sec for sec in SECTIONS if sec["category"] == cat and (loose_in(cat, sec["slug"]) or series_in_sec(cat, sec["slug"]))]
NAME = e(cfg["name"])
LOGO = lambda base: f'<p class="logo"><a href="{base}">{mark(size=40)}<span>Tool<b>4</b>That</span></a></p>'
FOOT = """<footer>
  <div class="wrap">Independent projects, free to use. Not affiliated with any government agency. Planning aids, not professional advice.<br>Tool4That started on GitHub at <a href="https://tool4that.github.io/">tool4that.github.io</a>, which stays online as the backup copy of this site. Main site: <a href="https://freeapp4that.store/">freeapp4that.store</a>.</div>
</footer>
</body>
</html>
"""
HOW = """  <section class="how" aria-labelledby="h-how">
    <h2 id="h-how">How these tools work</h2>
    <ul>
      <li><b>One file each.</b> Open a tool here, or download it and run it from your computer, even offline.</li>
      <li><b>Private by design.</b> Your data stays in your browser. Each tool says exactly what it keeps.</li>
      <li><b>Check your download.</b> Each tool lists its SHA-256 fingerprint. Compare it with <code>sha256sum FILE</code> (Linux), <code>shasum -a 256 FILE</code> (Mac), or <code>certutil -hashfile FILE SHA256</code> (Windows).</li>
      <li><b>Built with AI.</b> Tools are made with AI assistance and tested before release.</li>
    </ul>
  </section>
"""
total = len(cfg["tools"])

# ---- home: pick a category
def tile(c):
    n = len(tools_in(c["slug"]))
    secs = sections_in(c["slug"])
    groups = secs if secs else series_in(c["slug"])
    names = "".join(f" &middot; {e(g['title'])}" for g in groups)
    return (f'      <li class="tile"><a href="{e(c["slug"])}/">{mark(c.get("icon", "four"), 48)}<span class="tile-body"><span class="tile-t">{e(c["title"])}</span>'
            f'<span class="tile-s">{e(c["tagline"])}</span><span class="tile-n">{n} tool{"s" if n != 1 else ""}{names} &rarr;</span></span></a></li>\n')
title = f"{cfg['name']}: free tools that run in your browser"
desc = cfg.get("description", "Need a tool for that? Free single-file tools that run in your browser, with no sign-up and no tracking.")
home = head(title, desc, SITE + "/", SITE + "/og-image.png") + f"""<body>
<header class="hero">
  <div class="wrap">
    {LOGO("./")}
    <h1>Need a tool for that? There's a {NAME}.</h1>
    <p class="lede">Free, single-file tools that run entirely in your browser. Open them here, or download one and use it offline.</p>
    <ul class="points"><li>No sign-ups</li><li>No tracking</li><li>Nothing uploaded</li><li>Free</li></ul>
  </div>
</header>
<main class="wrap">
  <section aria-labelledby="h-pick">
    <h2 id="h-pick">Pick a category</h2>
    <ul class="tiles">
{"".join(tile(c) for c in CATS)}    </ul>
    <p class="all-link">Or <a href="all/">browse all {total} tools on one page</a>.</p>
  </section>
""" + HOW + "</main>\n" + FOOT
(ROOT / "index.html").write_text(home, encoding="utf-8", newline="\n")

# ---- one page per category, plus an all-tools page
def note(x): return f'    <p class="cat-note">{e(x["note"])}</p>\n' if x.get("note") else ""
def cards(ts, base, lvl): return '    <ul class="tools">\n' + "".join(tool_card(t, base, lvl) for t in ts) + "    </ul>\n"
def series_block(s, base, lvl):
    n = len(in_series(s["slug"]))
    return (f'    <h{lvl} class="series-h" id="s-{e(s["slug"])}"><a href="{base}{e(s["slug"])}/">{e(s["title"])}</a><span class="count">{n} tool{"s" if n != 1 else ""}</span></h{lvl}>\n'
            f'    <p class="cat-note">{e(s["description"])}</p>\n' + cards(in_series(s["slug"]), base, lvl + 1))
def listing(c, base, lvl=2, sectioned=False):
    """A category's tools: loose tools first (names at heading level lvl), then one group per series (heading lvl, names lvl+1).
    When sectioned, group everything under its section (heading lvl), with loose tools and series one level below."""
    secs = sections_in(c["slug"]) if sectioned else []
    if not secs:
        loose = loose_in(c["slug"])
        out = note(c) + (cards(loose, base, lvl) if loose else "")
        for s in series_in(c["slug"]):
            out += series_block(s, base, lvl)
        return out
    out = note(c)
    for sec in secs:
        out += f'    <h{lvl} class="section-h" id="sec-{e(sec["slug"])}">{e(sec["title"])}</h{lvl}>\n'
        if sec.get("intro"): out += f'    <p class="section-intro">{e(sec["intro"])}</p>\n'
        loose = loose_in(c["slug"], sec["slug"])
        if loose: out += cards(loose, base, lvl + 1)
        for s in series_in_sec(c["slug"], sec["slug"]):
            out += series_block(s, base, lvl + 1)
    return out
for c in CATS:
    page = head(f"{c['title']} | {cfg['name']}", c["description"], f"{SITE}/{c['slug']}/", SITE + "/og-image.png") + f"""<body>
<header class="hero small">
  <div class="wrap">
    {LOGO("../")}
    <p class="crumb"><a href="../">&larr; All categories</a></p>
    <h1>{e(c['title'])}</h1>
    <p class="lede">{e(c['description'])}</p>
  </div>
</header>
<main class="wrap">
  <section aria-label="{e(c['title'])} tools">
{listing(c, "../", 2, sectioned=True)}  </section>
</main>
""" + FOOT
    (ROOT / c["slug"]).mkdir(exist_ok=True)
    (ROOT / c["slug"] / "index.html").write_text(page, encoding="utf-8", newline="\n")
for s in SERIES:
    if not in_series(s["slug"]):
        continue
    c = next(c for c in CATS if c["slug"] == s["category"])
    page = head(f"{s['title']} | {cfg['name']}", s["description"], f"{SITE}/{s['slug']}/", SITE + "/og-image.png") + f"""<body>
<header class="hero small">
  <div class="wrap">
    {LOGO("../")}
    <p class="crumb"><a href="../{e(c['slug'])}/">&larr; {e(c['title'])}</a></p>
    <h1>{e(s['title'])}</h1>
    <p class="lede">{e(s['description'])}</p>
  </div>
</header>
<main class="wrap">
  <section aria-label="{e(s['title'])} tools">
{note(s)}{cards(in_series(s["slug"]), "../", 2)}  </section>
</main>
""" + FOOT
    (ROOT / s["slug"]).mkdir(exist_ok=True)
    (ROOT / s["slug"] / "index.html").write_text(page, encoding="utf-8", newline="\n")
allpage = head(f"All tools | {cfg['name']}", f"Every {cfg['name']} tool on one page: " + ", ".join(c["title"].lower() for c in CATS) + ".", SITE + "/all/", SITE + "/og-image.png") + f"""<body>
<header class="hero small">
  <div class="wrap">
    {LOGO("../")}
    <p class="crumb"><a href="../">&larr; Pick a category</a></p>
    <h1>All tools</h1>
    <p class="lede">Every tool on one page.</p>
  </div>
</header>
<main class="wrap">
""" + "".join(f'  <section aria-labelledby="h-{e(c["slug"])}">\n    <h2 id="h-{e(c["slug"])}"><a href="../{e(c["slug"])}/">{e(c["title"])}</a></h2>\n' + listing(c, "../", 3) + "  </section>\n" for c in CATS) + "</main>\n" + FOOT
(ROOT / "all").mkdir(exist_ok=True)
(ROOT / "all" / "index.html").write_text(allpage, encoding="utf-8", newline="\n")

notfound = head(f"Page not found | {cfg['name']}", "That page doesn't exist.", SITE + "/", SITE + "/og-image.png").replace('<link rel="canonical"', '<meta name="robots" content="noindex">\n<link rel="canonical"') + f"""<body>
<header class="hero"><div class="wrap">{LOGO(SITE + "/")}<h1>That page isn't here.</h1>
<p class="lede"><a href="{SITE}/" style="color:#fff">Back to all tools</a></p></div></header>
</body>
</html>
"""
(ROOT / "404.html").write_text(notfound, encoding="utf-8", newline="\n")
# web archives (the Internet Archive's Wayback Machine crawlers) may not capture the site; search engines may
ARCHIVE_BOTS = ["ia_archiver", "archive.org_bot"]
(ROOT / "robots.txt").write_text("".join(f"User-agent: {b}\nDisallow: /\n\n" for b in ARCHIVE_BOTS) + f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8", newline="\n")
latest = max([TODAY] + [t["updated"] for t in cfg["tools"]])
urls = [(SITE + "/", latest), (SITE + "/all/", latest)] + [(f"{SITE}/{c['slug']}/", max([t["updated"] for t in tools_in(c["slug"])] or [TODAY])) for c in CATS] + [(f"{SITE}/{s['slug']}/", max(t["updated"] for t in in_series(s["slug"]))) for s in SERIES if in_series(s["slug"])] + [(f"{SITE}/{t['slug']}/", t["updated"]) for t in cfg["tools"]]
(ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n", encoding="utf-8", newline="\n")
(ROOT / ".nojekyll").touch()
for t in cfg["tools"]:
    t.pop("_kb", None)
    for x in t.get("extras", []):
        x.pop("_kb", None)
CFG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8", newline="\n")
for t in cfg["tools"]:
    print(f"{t['slug']:<28} {t['updated']}  {t['sha256']}")
    for x in html_extras(t):
        print(f"{'  + ' + Path(x['file']).name:<28} {x['updated']}  {x['sha256']}")
print(f"hub rebuilt for {SITE}: {len(CATS)} categories, {sum(1 for s in SERIES if in_series(s['slug']))} series, {total} tools")

#!/usr/bin/env python3
"""Prepare a single-file HTML tool for Tool4That.

Usage:
  py prepare_tool.py SOURCE.html SLUG --name "Tool Name" --description "One or two sentences." [--icon "🔢"]
      [--allow-script URL]          let the page load a library from this exact address (e.g. pdf.js on cdnjs)
      [--accept-runtime-fallback]   accept guarded claude.ai features that fall back when absent
      [--frame-guard]               refuse to run inside another site's frame (tools that read personal data)
      [--allow-connect URL]         let the page fetch data from this exact https address prefix (e.g. an OCR language model)
      [--allow-wasm]                let the page run WebAssembly ('wasm-unsafe-eval'; e.g. an OCR engine)
      [--allow-worker-blob]         let the page start a web worker from a blob: address (e.g. tesseract.js)
      [--allow-connect-data]        add data: to connect-src, so an engine can decode its own embedded WebAssembly (data: never reaches the network)
      [--allow-script-blob]         add blob: to script-src, so a page can run libraries it decodes from its own embedded data blocks, each pinned by --pin-block (an offline edition)
      [--pin-block SHA256]          with --allow-script-blob (required, repeatable): the SHA-256 of one file the page carries as a data block
      [--out NAME]                  write SLUG/NAME (e.g. pfat-offline.html, a second download) instead of SLUG/index.html
      [--category C] [--series S] [--section X]   where the tool sits, when tools.json doesn't list it yet (add_tools.py
                                    passes them; a new Cyber tool prepared by hand needs --category cyber for its site bar)
  py prepare_tool.py --refresh-nav [FILE ...]
      bring the site bar and footer link of published tool pages (every tool page in tools.json when no FILE is
      named) up to date with tools.json, in place, after a tool is added, renamed, or moved; build_hub.py refuses to
      build until they are
  py prepare_tool.py --check-codec
      confirm that design/progress-code.js's encode part equals CODE_ENC (the progress code encoder every Cyber
      tool page's site bar carries) byte for byte

It refuses pages that aren't self-contained or safe. With --allow-script-blob it also reads every element the way a
browser does, decodes every data block (exactly <script type="application/octet-stream" id="vendor-NAME">), and accepts
the page only when each block is one of the --pin-block files, each pinned file and each vendor-* id is present exactly
once, every other element keeps clear of vendor-* ids and octet-stream, and every other non-running script block is JSON-LD.
Otherwise it writes SLUG/index.html (or SLUG/NAME with --out) with:
  - a strict Content Security Policy that pins every inline <script> by SHA-256 (no 'unsafe-inline' scripts)
  - a description, canonical address, link-preview tags, and an emoji icon
  - a small "More free tools at Tool4That" link back to the hub
  - for a tool in a category with a "nav_label" (Cybersecurity: "Cyber"), the site bar right after <body> (see nav_block)
    and a footer link to the category page in place of the hub link
Re-running is safe: everything it adds sits between tool4that marker comments and is replaced.
Next: add the tool to tools.json, then run build_hub.py. Standard library only.
"""
import argparse, base64, hashlib, html, json, re, sys, urllib.parse
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
SITE = CFG["site"].rstrip("/")

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
SCRIPT = re.compile(r"<script\b([^>]*)>([\s\S]*?)</script\s*>", re.I)
SCRIPT_TYPE = re.compile(r"\btype\s*=\s*[\"']?([^\"'\s>]+)", re.I)
RUNS = ("text/javascript", "application/javascript", "module")
MARK = re.compile(r"<!-- tool4that:(head|foot|nav) -->[\s\S]*?<!-- /tool4that:\1 -->\n?")
NAV_MARK = re.compile(r"<!-- tool4that:nav -->[\s\S]*?<!-- /tool4that:nav -->\n?")
FOOT_MARK = re.compile(r"<!-- tool4that:foot -->[\s\S]*?<!-- /tool4that:foot -->\n?")
CSP_META = re.compile(r'(<meta http-equiv="Content-Security-Policy" content=")([^"]*)(">)')
# where the site bar goes: right after the real <body ...> tag (one inside a comment, script, or style doesn't count),
# and after any skip links that open the page, so a skip link stays the first stop on the keyboard
RAW_TEXT = re.compile(r"<!--[\s\S]*?(?:-->|$)|<(script|style|textarea|title)\b[^>]*>[\s\S]*?(?:</\1\s*>|$)", re.I)
BODY_TAG = re.compile(r"<body\b[^>]*>", re.I)
SKIP_LINKS = re.compile(r'(?:\s*<a\b[^>]*\bclass\s*=\s*["\'][^"\']*\bskip\b[^"\']*["\'][^>]*>[^<]*</a>)*', re.I)


def nav_at(page):
    """Where the site bar goes in the page, or None when the page has no <body> tag."""
    m = BODY_TAG.search(RAW_TEXT.sub(lambda x: " " * len(x.group(0)), page))
    return SKIP_LINKS.match(page, m.end()).end() if m else None

# ---- The site bar -------------------------------------------------------------------------------------------------
# A category with a "nav_label" in tools.json (only Cybersecurity, labelled "Cyber") gets a slim bar at the top of
# every one of its tool pages (here) and hub pages (build_hub.py calls nav_block too): on the left a breadcrumb trail
# that starts at the category page (the current page isn't repeated; the category page itself has none), on the
# right a "<label> tools" menu button that opens over the page and lists "All <label> tools" and then every tool of
# the category, grouped as the category page groups them (sections, then series, then tools), with the current one
# marked. Nothing outside the category appears. Hub pages run no JavaScript, so the menu is a plain <details> that
# hides its panel once focus moves outside the Menu (NAV_CSS_HUB); tool pages add NAV_SCRIPT (Escape closes
# and returns focus, a tap or click outside or Tab past the end closes, aria-expanded kept right, keys pressed in the
# bar stay away from the tool's shortcuts, links point at SITE from a downloaded copy, and the bar stays first in
# <body> when a tool inserts something before it). All of it sits in one <!-- tool4that:nav --> block with one style
# block scoped under #t4t-nav (ids and classes t4t-nav-*), so the tool's CSS never reaches it and it never restyles
# the tool. The closed bar sits low (z-index 1), under a tool's own overlays (menus, panes, dialogs); the open one
# rises to 90, over the tools' sticky headers. NAV_SCRIPT is the same text on every page, so it adds the same hash
# to each page's policy, and a change to the Menu's list alone never changes a page's hashes (see refresh_nav).
#
# NAV_MORE: the Menu's closing group, below the tools. Each item is ("link", label, site path), shown on hub and tool
# pages, or ("button", label, action), shown on tool pages only and run by NAV_SCRIPT's ACT table (ACT.<action>).
# A link names a tool page of the category: it shows once tools.json lists that tool, carries aria-current="page" on
# that tool's own page, and the tool list above leaves that tool out, so the Menu names each page once. The copy-code
# button is followed by a status line (role="status", there from the start so screen readers announce it) and a
# hidden read-only box that shows the code when the clipboard is unavailable.
NAV_MORE = [("link", "My Cyber progress", "my-cyber-progress/"), ("button", "Copy my progress code", "copy-code")]
NAV_OUT = ('<li class="t4t-nav-out"><span class="t4t-nav-say" role="status"></span><textarea class="t4t-nav-code" readonly hidden'
           ' rows="3" aria-label="Your progress code"></textarea></li>')

# The Cyber progress code's encoder (format CY1; design/progress-code.js documents it and holds the decoder that My
# Cyber progress carries). The site bar embeds it byte for byte, so its bytes, and with them the bar's policy hash,
# are the same on every page; `prepare_tool.py --check-codec` confirms design/progress-code.js's encode part matches.
# ES5 only (var, no eval), and free of the words the Study Map's page check refuses, since My Cyber progress carries it.
CODE_ENC = r"""
var T4T_CODE=(function(){var A='0123456789ABCDEFGHJKMNPQRSTVWXYZ',has=Object.prototype.hasOwnProperty;
function mul(x){var r=0,y=30;while(y){if(y&1)r^=x;y>>=1;x<<=1;if(x&32)x^=37;}return r;}
function check(s){var r=0,i;for(i=0;i<s.length;i++)r=mul(r)^A.indexOf(s.charAt(i));return A.charAt(mul(r));}
function trim(s){return String(s).replace(/0+$/,'');}
function seg(g,s){return typeof g==='number'&&g===Math.floor(g)&&g>=1&&g<=63&&typeof s==='string'&&/^[012]*$/.test(s)&&trim(s).length<=4095;}
function gam(b,v){var s=v.toString(2),i;for(i=1;i<s.length;i++)b.push(0);for(i=0;i<s.length;i++)b.push(s.charAt(i)==='1'?1:0);}
function dense(s){var b=[],i,c;for(i=0;i<s.length;i++){c=s.charAt(i);b.push(c==='0'?0:1);if(c!=='0')b.push(c==='2'?1:0);}return b;}
function runs(s){var b=[],i=0,j,c,p=-1;while(i<s.length){c=+s.charAt(i);j=i;while(j<s.length&&+s.charAt(j)===c)j++;if(p<0)b.push(c>>1,c&1);else b.push(c>3-p-c?1:0);gam(b,j-i);p=c;i=j;}return b;}
function encode(rec){var b=[],gs=[],k,i,s,d,r,p=0,o='';
for(k in rec)if(has.call(rec,k)&&/^[1-9]\d?$/.test(k)&&seg(+k,rec[k])&&trim(rec[k]))gs.push(+k);
gs.sort(function(x,y){return x-y;});
if(gs.length)gam(b,gs.length+1);
for(i=0;i<gs.length;i++){s=trim(rec[gs[i]]);gam(b,gs[i]-p);p=gs[i];gam(b,s.length);d=dense(s);r=runs(s);b.push(r.length<d.length?1:0);b=b.concat(r.length<d.length?r:d);}
while(b.length%5)b.push(0);
for(i=0;i<b.length;i+=5)o+=A.charAt(b[i]*16+b[i+1]*8+b[i+2]*4+b[i+3]*2+b[i+4]);
return 'CY1-'+o+check('1'+o);}
function group(c){return c.slice(0,4)+c.slice(4).replace(/(.{5})(?=.)/g,'$1 ');}
function rec(key,raw){var o;try{o=JSON.parse(raw);}catch(e){return null;}
return o&&o.v===1&&typeof o.k==='string'&&'t4t.done.'+o.k===key&&seg(o.g,o.s)?{g:o.g,s:trim(o.s)}:null;}
function held(raw){var o,h,k,out={};try{o=JSON.parse(raw);}catch(e){return out;}h=o&&o.v===1?o.held:null;
if(h&&typeof h==='object')for(k in h)if(has.call(h,k)&&/^[1-9]\d?$/.test(k)&&seg(+k,h[k])&&trim(h[k]))out[k]=trim(h[k]);return out;}
function max(a,b){var o='',i,x,y,n=Math.max(a.length,b.length);for(i=0;i<n;i++){x=a.charAt(i)||'0';y=b.charAt(i)||'0';o+=x>y?x:y;}return trim(o);}
function collect(ls){var r={},by={},bad={},clash=false,i,k,v,h,g,n=ls.length;
for(i=0;i<n;i++){k=ls.key(i);if(k==null||k==='t4t.done.held'||!/^t4t\.done\.[a-z0-9.-]+$/.test(k))continue;v=rec(k,ls.getItem(k));if(!v)continue;
if(has.call(by,v.g)){clash=true;bad[v.g]=1;}else{by[v.g]=k;r[v.g]=v.s;}}
for(g in bad)if(has.call(bad,g))delete r[g];
h=held(ls.getItem('t4t.done.held'));for(g in h)if(has.call(h,g)&&!has.call(bad,g))r[g]=has.call(r,g)?max(r[g],h[g]):h[g];
return {rec:r,clash:clash};}
return {A:A,check:check,trim:trim,encode:encode,group:group,rec:rec,held:held,max:max,collect:collect};})();
"""

# GATHER: each Cyber tool save from before the progress code, and the record (t4t.done.<k>) that tool writes once it
# opens after the update. When a save is here without its record, Copy my progress code says to open My Cyber progress
# once, which gathers that earlier work. It changes only when a tool with an older save joins (out with --refresh-nav).
GATHER = {
    "defense-ladder-v1": "t4t.done.defense-ladder",
    "lockdown-drills-windows11-v1": "t4t.done.lockdown-drills.windows-11",
    "lockdown-drills-windows-server-v1": "t4t.done.lockdown-drills.windows-server",
    "lockdown-drills-debian-family-v1": "t4t.done.lockdown-drills.debian-family",
    "lockdown-drills-ubuntu-v1": "t4t.done.lockdown-drills.debian-family",
    "lockdown-drills-linux-mint-v1": "t4t.done.lockdown-drills.debian-family",
    "lockdown-drills-freebsd-v1": "t4t.done.lockdown-drills.freebsd",
    "lockdown-drills-cisco-v1": "t4t.done.lockdown-drills.cisco-ios",
    "lockdown-range-windows-v3": "t4t.done.lockdown-range.windows",
    "lockdown-range-linux-v3": "t4t.done.lockdown-range.linux",
    "lockdown-range-cisco-v2": "t4t.done.lockdown-range.cisco-ios",
    "netdrills.cli2.done": "t4t.done.net-drills.ios-cli-lab",
    "netdrills.tickets.due": "t4t.done.net-drills.trouble-tickets",
}

NAV_CSS = (
    "#t4t-nav,#t4t-nav *,#t4t-nav *::before,#t4t-nav *::after{all:revert;box-sizing:border-box}"
    "#t4t-nav{--t4t-nav-bg:#F4F6F8;--t4t-nav-panel:#FFFFFF;--t4t-nav-ink:#17212B;--t4t-nav-muted:#4A5868;--t4t-nav-line:#B9C4CF;"
    "--t4t-nav-link:#1F5C9E;--t4t-nav-hover:#EBF0F5;--t4t-nav-cur:#DFE9F5;color-scheme:light;"
    "display:block;position:relative;z-index:1;margin:0;padding:0;background:var(--t4t-nav-bg);color:var(--t4t-nav-ink);"
    "border-bottom:1px solid var(--t4t-nav-line);font:400 .875rem/1.4 system-ui,-apple-system,\"Segoe UI\",Roboto,Arial,sans-serif;"
    "text-align:left;letter-spacing:normal;text-transform:none;user-select:auto;-webkit-user-select:auto}"
    # raised only while open (two rules: a browser without :has still reads the class NAV_SCRIPT sets)
    "#t4t-nav.t4t-nav-open{z-index:90}"
    "#t4t-nav:has(details[open]){z-index:90}"
    "@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]) #t4t-nav{--t4t-nav-bg:#121A23;--t4t-nav-panel:#18222D;"
    "--t4t-nav-ink:#E2E9F0;--t4t-nav-muted:#A3B1C0;--t4t-nav-line:#3A4B5D;--t4t-nav-link:#8CC4F2;--t4t-nav-hover:#202D3B;--t4t-nav-cur:#26384B;color-scheme:dark}}"
    ":root[data-theme=\"dark\"] #t4t-nav{--t4t-nav-bg:#121A23;--t4t-nav-panel:#18222D;--t4t-nav-ink:#E2E9F0;--t4t-nav-muted:#A3B1C0;"
    "--t4t-nav-line:#3A4B5D;--t4t-nav-link:#8CC4F2;--t4t-nav-hover:#202D3B;--t4t-nav-cur:#26384B;color-scheme:dark}"
    "#t4t-nav .t4t-nav-in{display:flex;align-items:center;gap:12px;min-height:44px;padding:6px 16px}"
    "#t4t-nav .t4t-nav-trail{display:block;flex:1 1 auto;min-width:0}"
    "#t4t-nav .t4t-nav-trail ol{display:flex;align-items:center;min-width:0;margin:0;padding:0;list-style:none}"
    "#t4t-nav .t4t-nav-trail li{display:flex;align-items:center;min-width:0;white-space:nowrap}"
    "#t4t-nav .t4t-nav-trail li+li::before{content:\"\\203A\";content:\"\\203A\"/\"\";margin:0 8px;color:var(--t4t-nav-muted)}"
    "#t4t-nav .t4t-nav-trail a{display:block;min-width:0;overflow:hidden;text-overflow:ellipsis;padding:5px 2px}"
    "#t4t-nav a{color:var(--t4t-nav-link);text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px;border-radius:3px}"
    "#t4t-nav a:hover{text-decoration-thickness:2px}"
    "#t4t-nav a:focus-visible,#t4t-nav summary:focus-visible,#t4t-nav button:focus-visible,#t4t-nav textarea:focus-visible{outline:3px solid var(--t4t-nav-link);outline-offset:2px}"
    "#t4t-nav details{display:block;flex:none;margin:0 0 0 auto}"
    "#t4t-nav summary{display:flex;align-items:center;gap:6px;min-height:32px;padding:4px 12px;border:1px solid var(--t4t-nav-line);"
    "border-radius:6px;background:var(--t4t-nav-panel);color:var(--t4t-nav-ink);font-weight:600;cursor:pointer;list-style:none}"
    "#t4t-nav summary::-webkit-details-marker{display:none}"
    "#t4t-nav summary::after{content:\"\\25BE\";content:\"\\25BE\"/\"\";font-size:.8em}"
    "#t4t-nav details[open]>summary::after{content:\"\\25B4\";content:\"\\25B4\"/\"\"}"
    "#t4t-nav .t4t-nav-panel{display:block;position:absolute;top:calc(100% - 2px);right:8px;width:max-content;min-width:14rem;"
    "max-width:min(22rem,calc(100vw - 16px));max-height:calc(100vh - 64px);max-height:calc(100dvh - 64px);overflow:auto;"
    "overscroll-behavior:contain;margin:0;padding:6px;background:var(--t4t-nav-panel);color:var(--t4t-nav-ink);"
    "border:1px solid var(--t4t-nav-line);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.2)}"
    "#t4t-nav .t4t-nav-panel ul{display:block;margin:0;padding:0;list-style:none}"
    "#t4t-nav .t4t-nav-panel li{display:block;margin:0;padding:0}"
    "#t4t-nav .t4t-nav-panel a,#t4t-nav .t4t-nav-panel button{display:block;width:100%;margin:0;padding:6px 10px;border:0;"
    "border-radius:5px;background:none;color:var(--t4t-nav-ink);font:inherit;text-align:left;text-decoration:none;cursor:pointer}"
    "#t4t-nav .t4t-nav-panel a:hover,#t4t-nav .t4t-nav-panel button:hover{background:var(--t4t-nav-hover);text-decoration:underline}"
    "#t4t-nav .t4t-nav-panel a[aria-current]{font-weight:700;background:var(--t4t-nav-cur);box-shadow:inset 3px 0 0 var(--t4t-nav-link)}"
    "#t4t-nav .t4t-nav-panel .t4t-nav-all,#t4t-nav .t4t-nav-ser>a{font-weight:600}"
    "#t4t-nav .t4t-nav-h{display:block;margin:10px 10px 2px;font-size:.8em;font-weight:700;color:var(--t4t-nav-muted)}"
    "#t4t-nav .t4t-nav-ser ul a{padding-left:24px}"
    "#t4t-nav .t4t-nav-more{margin-top:6px;padding-top:6px;border-top:1px solid var(--t4t-nav-line)}"
    # the copy-code status line and code box fill the panel's width without widening it (width 0, min-width 100%)
    "#t4t-nav .t4t-nav-say:not(:empty){display:block;width:0;min-width:100%;padding:2px 10px 6px;font-size:.8125rem;"
    "line-height:1.4;color:var(--t4t-nav-muted)}"
    "#t4t-nav .t4t-nav-code{display:block;width:0;min-width:100%;margin:2px 0 4px;padding:6px 8px;border:1px solid var(--t4t-nav-line);"
    "border-radius:5px;background:var(--t4t-nav-bg);color:var(--t4t-nav-ink);font:400 .8125rem/1.5 ui-monospace,\"SF Mono\",Consolas,"
    "\"DejaVu Sans Mono\",monospace;white-space:pre-wrap;overflow-wrap:normal;word-break:normal;resize:none}"
    "#t4t-nav .t4t-nav-code[hidden]{display:none}"
    "@media (max-width:480px){#t4t-nav .t4t-nav-trail li{display:none}#t4t-nav .t4t-nav-trail li:last-child{display:flex}"
    "#t4t-nav .t4t-nav-trail li:last-child::before{content:\"\\2039\";content:\"\\2039\"/\"\";margin:0 6px 0 0;color:var(--t4t-nav-muted)}}"
    # Cyber PUG's own toolbar cancels the page's 20px/16px padding with a negative margin, so the bar does the same
    "body[data-doc=\"pug\"]>#t4t-nav{margin:-20px -16px 20px}"
    "@media print{#t4t-nav{display:none!important}}"
)
# Hub pages only (they run no script). On a device with a mouse or trackpad ((hover:hover)), the open panel shows only
# while focus is inside the Menu. The hub wraps the <details> in <div class="t4t-nav-mw" tabindex="-1"> (HUB_MENU), so
# a press on the button or anywhere in the panel puts focus inside the wrapper in every browser, including those that
# never focus a button on a click (the tabindex sits on the wrapper because Chromium's Shift+Tab skips everything
# inside a <details> that carries one). Once focus moves on (Tab past the last item, or a click elsewhere on the page)
# the panel hides, so it never covers the focused element, and a click on blank page never brings it back. The
# <details> stays open meanwhile (only a script could close it), so while the panel hides, the button reads as closed
# (its arrow points down) and lets a press through to the <details> around it: the press puts focus in the wrapper,
# which shows the panel again, so one press always opens the Menu (a press on the button itself would close the hidden
# panel and need a second press). Keyboard focus that comes back to the button shows it too. On a touch screen
# ((hover:none)) the panel simply shows while the Menu is open, as a plain <details>; so does a browser without these
# selectors.
HUB_MENU = '<div class="t4t-nav-mw" tabindex="-1">'
NAV_CSS_HUB = (
    "#t4t-nav .t4t-nav-mw{display:block;flex:none;margin:0 0 0 auto;outline:none}"
    "@media (hover:hover){"
    "#t4t-nav .t4t-nav-mw:not(:focus-within) details[open] .t4t-nav-panel{display:none}"
    "#t4t-nav .t4t-nav-mw:not(:focus-within) details[open]>summary::after{content:\"\\25BE\";content:\"\\25BE\"/\"\"}"
    "#t4t-nav .t4t-nav-mw:not(:focus-within) details[open]>summary{pointer-events:none}"
    "#t4t-nav .t4t-nav-mw:not(:focus-within) details[open]{cursor:pointer}}"
)

NAV_SCRIPT = (
    "(function(){var w=document.getElementById('t4t-nav'),d=w&&w.querySelector('details'),s=d&&d.querySelector('summary');if(!s)return;"
    "var b=w.getAttribute('data-t4t-nav-base');"
    "function online(){var l=document.querySelectorAll('#t4t-nav a[href],a.t4t-nav-home'),i;"
    "for(i=0;i<l.length;i++)l[i].href=new URL(l[i].getAttribute('href'),b).href;}"
    "if(location.protocol==='file:'&&b){online();document.addEventListener('DOMContentLoaded',online);}"
    "var say=w.querySelector('.t4t-nav-say'),box=w.querySelector('.t4t-nav-code');"
    "function tell(t){if(say)say.textContent=t;}"
    "function sync(){s.setAttribute('aria-expanded',d.open?'true':'false');w.classList.toggle('t4t-nav-open',d.open);"
    "if(!d.open){tell('');if(box){box.hidden=true;box.value='';}}}"
    "function shut(f){if(d.open){d.open=false;sync();if(f)s.focus();}}"
    "sync();d.addEventListener('toggle',sync);"
    "w.addEventListener('keydown',function(e){if(e.key==='Escape'&&d.open){e.preventDefault();shut(true);}e.stopPropagation();});"
    "w.addEventListener('keyup',function(e){e.stopPropagation();});"
    "function away(e){if(d.open&&!d.contains(e.target))shut(false);}"
    "document.addEventListener('pointerdown',away,true);document.addEventListener('click',away,true);"
    "w.addEventListener('focusout',function(e){if(d.open&&e.relatedTarget&&!d.contains(e.relatedTarget))shut(false);});"
    + CODE_ENC
    + "var GATHER=" + json.dumps(GATHER, separators=(",", ":")) + ";"
    "var ACT={};"
    # Copy my progress code: every valid t4t.done.* record (and t4t.done.held) as one grouped code on the clipboard,
    # or, when the clipboard is unavailable, selected in the box for Ctrl+C; the status line says what it carries
    "ACT['copy-code']=function(){var ls=null,c,g,s,i,ok=0,mi=0,n=0,gap=false,fix,tail,code,done,cb=navigator.clipboard,"
    "own=Object.prototype.hasOwnProperty,off='This window keeps saved work switched off, so your code here starts empty. Open a regular window to copy your full code.';"
    "try{ls=window.localStorage;}catch(e){}"
    "if(!ls){tell(off);return;}"
    "try{c=T4T_CODE.collect(ls);for(g in GATHER)if(own.call(GATHER,g)){s=ls.getItem(g);if(s!==null&&s!=='null'&&ls.getItem(GATHER[g])===null)gap=true;}}"
    "catch(e){tell(off);return;}"
    "for(g in c.rec)if(own.call(c.rec,g)&&c.rec[g]){n++;s=c.rec[g];for(i=0;i<s.length;i++){if(s.charAt(i)==='2')ok++;else if(s.charAt(i)==='1')mi++;}}"
    "code=T4T_CODE.group(T4T_CODE.encode(c.rec));"
    "fix=c.clash&&gap?'repair your saved results and gather your earlier work into the code':c.clash?'repair your saved results':gap?'gather your earlier work into the code':'';"
    "tail=(fix?' Open My Cyber progress once to '+fix+'.':'')+(location.protocol==='file:'?' This copy keeps its own progress. "
    "Paste the code into My Cyber progress (it opens online) to see it there.':'');"
    "done=ok+mi?'Copied: '+(ok+mi)+' result'+(ok+mi===1?'':'s')+' from '+n+' tool'+(n===1?'':'s')+' ('+ok+' right, '+mi+' to retry).'"
    ":'Copied. Your code fills in as you answer questions and pass checks.';"
    "function show(){if(!d.open||!box)return;tell('Selected. Press Ctrl+C (Command+C on a Mac) to copy; on a phone, tap and hold, then Copy.'+tail);"
    "box.value=code;box.hidden=false;box.removeAttribute('readonly');box.focus();box.select();"
    "try{box.setSelectionRange(0,box.value.length);}catch(e){}box.scrollTop=0;box.setAttribute('readonly','');}"
    "tell('');if(box)box.hidden=true;"
    "if(!cb||!cb.writeText){show();return;}"
    "try{cb.writeText(code).then(function(){if(d.open)tell(done+tail);},show);}catch(e){show();}};"
    "w.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('[data-t4t-nav-act]'),f=t&&ACT[t.getAttribute('data-t4t-nav-act')];"
    "if(f){e.preventDefault();f(t);}});"
    "function place(){var r=document.body.firstElementChild;while(r&&r!==w&&r.matches('a.skip'))r=r.nextElementSibling;"
    "if(r!==w)document.body.insertBefore(w,r);}"
    "place();new MutationObserver(place).observe(document.body,{childList:true});})();"
)


def nav_category(cfg, cat):
    """The category's entry when it carries a site bar ("nav_label"), else None."""
    c = next((c for c in cfg["categories"] if c["slug"] == cat), None)
    return c if c and c.get("nav_label") else None


def nav_groups(cfg, cat, tools):
    """The category's tools grouped as build_hub.py's category page groups them: [(section title or None,
    [(series or None, [tools])])], sections in order (only those with tools), loose tools before series."""
    series = [s for s in cfg.get("series", []) if s["category"] == cat]
    in_ser = lambda s: [t for t in tools if t.get("series") == s["slug"]]
    secs = [x for x in cfg.get("sections", []) if x["category"] == cat]
    def group(sec):
        loose = [t for t in tools if not t.get("series") and (sec is None or t.get("section") == sec)]
        return ([(None, loose)] if loose else []) + [(s, in_ser(s)) for s in series if (sec is None or s.get("section") == sec) and in_ser(s)]
    if not secs:
        return [(None, group(None))]
    return [(x["title"], g) for x in secs for g in [group(x["slug"])] if g]


def nav_block(cfg, cat, here, current, tool_page=False, extra_tool=None):
    """The site bar for one page, as a <!-- tool4that:nav --> block.
    cat: the category slug; here: the site path of the page's folder ("lockdown-range/windows/", "cyber/");
    current: ("tool", slug), ("series", slug), or ("category", slug); tool_page: add NAV_SCRIPT and the address a
    downloaded copy points its links at; extra_tool: a tool tools.json doesn't list yet (from add_tools.py)."""
    c = nav_category(cfg, cat)
    e = lambda s: html.escape(s, quote=True)
    label, up = c["nav_label"], "../" * here.count("/")
    tools = [extra_tool if extra_tool and t["slug"] == extra_tool["slug"] else t for t in cfg["tools"]]
    if extra_tool and extra_tool not in tools:
        tools.append(extra_tool)
    tools = [t for t in tools if t.get("category") == cat]
    cur = lambda kind, slug: ' aria-current="page"' if current == (kind, slug) else ""
    link = lambda path, text, attrs="": f'<a{attrs} href="{e(up + path)}">{e(text)}</a>'
    trail = []
    if current[0] != "category":
        trail.append(link(cat + "/", label))
    if current[0] == "tool":
        t = next(t for t in tools if t["slug"] == current[1])
        s = next((s for s in cfg.get("series", []) if s["slug"] == t.get("series")), None)
        if s:
            trail.append(link(s["slug"] + "/", s["title"]))
    out = ["<li>" + link(cat + "/", f"All {label} tools", ' class="t4t-nav-all"' + cur("category", cat)) + "</li>"]
    # a tool that NAV_MORE links to appears there, in the closing group, in place of the tool list
    more_links = {arg for kind, _, arg in NAV_MORE if kind == "link"}
    listed = {t["slug"] + "/" for t in tools}
    for title, groups in nav_groups(cfg, cat, [t for t in tools if t["slug"] + "/" not in more_links]):
        items = []
        for s, ts in groups:
            lis = "".join(f'<li>{link(t["slug"] + "/", t["name"], cur("tool", t["slug"]))}</li>' for t in ts)
            items.append(f'<li class="t4t-nav-ser">{link(s["slug"] + "/", s["title"], cur("series", s["slug"]))}<ul>{lis}</ul></li>' if s else lis)
        body = "<ul>" + "".join(items) + "</ul>"
        out.append(f'<li><span class="t4t-nav-h">{e(title)}</span>{body}</li>' if title else f"<li>{body}</li>")
    more = []
    for kind, text, arg in NAV_MORE:
        if kind == "link" and arg in listed:
            more.append(f"<li>{link(arg, text, cur('tool', arg.rstrip('/')))}</li>")
        elif kind == "button" and tool_page:
            more.append(f'<li><button type="button" data-t4t-nav-act="{e(arg)}">{e(text)}</button></li>' + (NAV_OUT if arg == "copy-code" else ""))
    if more:
        out.append('<li class="t4t-nav-more"><ul>' + "".join(more) + "</ul></li>")
    base = f' data-t4t-nav-base="{e(SITE + "/" + here)}"' if tool_page else ""
    bar = (f'<div class="t4t-nav" id="t4t-nav"{base}><style>{NAV_CSS}{"" if tool_page else NAV_CSS_HUB}</style><div class="t4t-nav-in">'
           + (f'<nav class="t4t-nav-trail" aria-label="{e(label)}"><ol>' + "".join(f"<li>{x}</li>" for x in trail) + "</ol></nav>" if trail else "")
           + ("" if tool_page else HUB_MENU) + f'<details class="t4t-nav-menu"><summary>{e(label)} tools</summary>'
           + f'<nav class="t4t-nav-panel" aria-label="{e(label)} tools"><ul>' + "".join(out) + "</ul></nav></details>"
           + ("" if tool_page else "</div>") + "</div>"
           + (f"<script>{NAV_SCRIPT}</script>" if tool_page else "") + "</div>")
    return "<!-- tool4that:nav -->" + bar + "<!-- /tool4that:nav -->\n"


def tool_place(cfg, slug, a=None):
    """(category, the tool as the bar should list it, or None when tools.json has it) for a tool page; the command
    line's --category/--series/--section win, since add_tools.py writes them to tools.json after preparing."""
    t = next((t for t in cfg["tools"] if t["slug"] == slug), None)
    if a is None or not a.category:
        return (t or {}).get("category"), None
    return a.category, {**(t or {}), "slug": slug, "name": a.name, "category": a.category, "series": a.series, "section": a.section}


def foot_block(cfg, slug, cat):
    """The footer link: to the category page for a tool with the site bar (NAV_SCRIPT points it online from a
    downloaded copy), otherwise to the hub."""
    home, nav = "../" * len(slug.split("/")), nav_category(cfg, cat) if cat else None
    back = f'<a class="t4t-nav-home" href="{home}{cat}/">More free {html.escape(nav["nav_label"])} tools</a>' if nav else f'<a href="{home}">More free tools at Tool4That</a>'
    return ('<!-- tool4that:foot --><p style="text-align:center;margin:28px 0 22px;font:14px/1.4 system-ui,-apple-system,Segoe UI,Arial,sans-serif">'
            f'{back}</p><!-- /tool4that:foot -->\n')


def page_hashes(page):
    return sorted({sha256_csp(b) for b in executable_scripts(page)})


def nav_refresh(cfg, t, page):
    """A published page of tool t with its site bar and footer link as tools.json has them now, and its policy's
    script hashes brought along: the same bytes a full re-prepare with the tool's usual options gives, without the
    source or those options. A page without the bar whose tool has none comes back as it is. Raises ValueError for a
    page prepare_tool.py didn't write, or one whose policy no longer matches its scripts."""
    cat, nav = t.get("category"), nav_category(cfg, t.get("category"))
    if not nav and not NAV_MARK.search(page):
        return page
    if "<!-- tool4that:head -->" not in page or not FOOT_MARK.search(page) or not CSP_META.search(page):
        raise ValueError("isn't a page prepare_tool.py wrote (its tool4that head, policy, or foot is missing); prepare it from source")
    pinned = [x for d in CSP_META.search(page).group(2).split("; ") if d.startswith("script-src ") for x in d.split()[1:]]
    if sorted(x for x in pinned if x.startswith("'sha256-")) != page_hashes(page):
        raise ValueError("its policy's script hashes don't match its scripts; prepare it from source")
    new = NAV_MARK.sub("", page)
    if nav:
        at = nav_at(new)
        if at is None:
            raise ValueError("has no <body> tag")
        new = new[:at] + nav_block(cfg, cat, t["slug"] + "/", ("tool", t["slug"]), tool_page=True) + new[at:]
    new = FOOT_MARK.sub(lambda m: foot_block(cfg, t["slug"], cat), new, count=1)
    m = CSP_META.search(new)
    parts = m.group(2).split("; ")
    i = next((i for i, d in enumerate(parts) if d.startswith("script-src ")), None)
    rest = [x for x in parts[i].split()[1:] if not x.startswith("'sha256-")] if i is not None else []
    tokens = page_hashes(new) + rest
    if i is None and tokens:
        parts.insert(1, "")
        i = 1
    if i is not None:
        parts[i:i + 1] = ["script-src " + " ".join(tokens)] if tokens else []
    return new[:m.start(2)] + "; ".join(parts) + new[m.end(2):]


def tool_files(cfg):
    """(published .html file, its tool) for every tool page in tools.json: each main file and each .html extra."""
    return [(f, t) for t in cfg["tools"] for f in [t["file"]] + [x["file"] for x in t.get("extras", []) if x["file"].lower().endswith(".html")]]


def refresh_nav(files):
    """--refresh-nav [FILE ...]: bring the site bar and footer of published tool pages up to date in place (every
    tool page in tools.json when no FILE is named). Re-run safe; pages already up to date are left untouched."""
    pages = dict(tool_files(CFG))
    named = []
    for f in files:
        try:
            named.append(Path(f).resolve().relative_to(ROOT).as_posix())
        except ValueError:
            named.append(f)
    bad = [f for f in named if f not in pages]
    if bad:
        sys.exit("Not a tool page in tools.json: " + ", ".join(bad))
    done, same, failed = 0, 0, 0
    for f in named or list(pages):
        old = (ROOT / f).read_text(encoding="utf-8")
        try:
            new = nav_refresh(CFG, pages[f], old)
        except ValueError as err:
            print(f"NOT WRITTEN {f}: {err}")
            failed += 1
            continue
        if new == old:
            same += 1
            continue
        (ROOT / f).write_text(new, encoding="utf-8", newline="\n")
        print(f"Refreshed {f}: {len(new.encode()):,} bytes.")
        done += 1
    print(f"{done} page(s) refreshed, {same} already up to date" + (f", {failed} not written" if failed else "") + ". Next: run build_hub.py.")
    sys.exit(1 if failed else 0)


# ---- The progress code and My Cyber progress ----------------------------------------------------------------------
CODEC = ROOT / "design" / "progress-code.js"
PROGRESS_SLUG = "my-cyber-progress"
DONE_BLOCK = re.compile(r"/\*@t4t-done\*/([\s\S]*?)/\*@/t4t-done\*/")
PROGRESS_BLOCK = re.compile(r"/\*@progress-code\*/([\s\S]*?)/\*@/progress-code\*/")
CP_DATA = re.compile(r'<script type="application/json" id="cp-data">([\s\S]*?)</script\s*>', re.I)
SLOT_RANGE = re.compile(r"^(.*)\.(\d+)-(\d+)$")


def codec_part(text, name):
    """The text between /*@name*/ and /*@/name*/, or None unless the text holds exactly one such part."""
    found = re.findall(r"/\*@" + name + r"\*/([\s\S]*?)/\*@/" + name + r"\*/", text)
    return found[0] if len(found) == 1 else None


def codec_parts():
    """(encode, decode): the two marked parts of design/progress-code.js, read only when needed, byte for byte."""
    if not CODEC.is_file():
        sys.exit("design/progress-code.js is missing: it holds the progress code decoder")
    text = CODEC.read_bytes().decode("utf-8")
    enc, dec = codec_part(text, "encode"), codec_part(text, "decode")
    if enc is None or dec is None:
        sys.exit("design/progress-code.js needs exactly one /*@encode*/ part and one /*@decode*/ part")
    return enc, dec


def check_codec():
    """--check-codec: exit 0 when design/progress-code.js's encode part equals CODE_ENC byte for byte."""
    enc, _ = codec_parts()
    if enc == CODE_ENC:
        print(f"Codec matches: design/progress-code.js's encode part equals CODE_ENC ({len(CODE_ENC.encode()):,} bytes).")
        sys.exit(0)
    at = next((i for i, (a, b) in enumerate(zip(enc, CODE_ENC)) if a != b), min(len(enc), len(CODE_ENC)))
    sys.exit(f"Codec differs at character {at}: design/progress-code.js has {enc[at:at + 40]!r}, CODE_ENC has "
             f"{CODE_ENC[at:at + 40]!r}. Make the two the same text.")


def slot_ids(items):
    """A slot list expanded: "a.N-M" stands for a.N to a.M, "~" (or a registry entry marked "retired") for a retired
    slot (None); registry entries ({"id": ...}) are read too."""
    out = []
    for x in items:
        if isinstance(x, dict):
            out.append(None if x.get("retired") else x.get("id"))
        elif x == "~":
            out.append(None)
        elif isinstance(x, str) and SLOT_RANGE.match(x):
            a, n, m = SLOT_RANGE.match(x).groups()
            out += [f"{a}.{i}" for i in range(int(n), int(m) + 1)]
        else:
            out.append(x)
    return out


def done_record(block):
    """{"g", "k", "ids" (expanded)} from a tool's /*@t4t-done*/ block: its first JSON object that starts {"g": and holds
    an integer "g" and the slot list "ids" ("k" is None when the object lacks it), or None."""
    at = block.find('{"g":')
    if at < 0:
        return None
    try:
        o, _ = json.JSONDecoder().raw_decode(block, at)
    except ValueError:
        return None
    if not isinstance(o.get("g"), int) or not isinstance(o.get("ids"), list):
        return None
    return {"g": o["g"], "k": o.get("k"), "ids": slot_ids(o["ids"])}


def done_segment(block):
    """(g, expanded slot ids) from a tool's /*@t4t-done*/ block (see done_record), or None."""
    r = done_record(block)
    return (r["g"], r["ids"]) if r else None


def page_entries(data):
    """{g: {"k", "href", "ids" (expanded)}} from My Cyber progress's page data: every object holding an integer "g" and
    a list "ids" (or "slots"), first one per g, those in a top-level "segments" list first; "href" is the tool's site
    path ("lockdown-range/windows/")."""
    out = {}
    def walk(x):
        if isinstance(x, dict):
            ids = x.get("ids", x.get("slots"))
            if isinstance(x.get("g"), int) and isinstance(ids, list) and x["g"] not in out:
                out[x["g"]] = {"k": x.get("k"), "href": x.get("href"), "ids": slot_ids(ids)}
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    if isinstance(data, dict):
        walk(data.get("segments"))
    walk(data)
    return out


def page_segments(data):
    """{g: expanded slot ids} from My Cyber progress's page data (see page_entries)."""
    return {g: e["ids"] for g, e in page_entries(data).items()}


def progress_problems(cfg):
    """Why My Cyber progress and the Cyber tools are out of step (build_hub.py refuses to build while any holds), or []
    while tools.json doesn't list the page yet:
      - design/progress-code.js's encode part must equal CODE_ENC (the encoder the site bar carries), and the page's
        /*@progress-code*/ block must hold CODE_ENC and design/progress-code.js's decode part, each between its
        /*@encode*/ or /*@decode*/ markers;
      - every segment in the page data must belong to a tool in tools.json (its "href", else its "k" with the first dot
        read as a slash), and that tool's page and each of its .html extras (Defense Ladder's grade downloads) must
        carry one /*@t4t-done*/ block with the same g, the same k, and the same slot list;
      - no other page of the category may carry a /*@t4t-done*/ block."""
    t = next((t for t in cfg["tools"] if t["slug"] == PROGRESS_SLUG), None)
    if not t:
        return []
    enc, dec = codec_parts()
    f = t["file"]
    page = (ROOT / f).read_bytes().decode("utf-8")
    out = []
    if enc != CODE_ENC:
        out.append("design/progress-code.js: its encode part differs from CODE_ENC in prepare_tool.py "
                   "(py -I prepare_tool.py --check-codec shows where)")
    blocks = PROGRESS_BLOCK.findall(page)
    if len(blocks) != 1:
        out.append(f"{f}: carries {len(blocks)} /*@progress-code*/ blocks (exactly one expected)")
    else:
        if codec_part(blocks[0], "encode") != CODE_ENC:
            out.append(f"{f}: its progress code encoder differs from CODE_ENC in prepare_tool.py")
        if codec_part(blocks[0], "decode") != dec:
            out.append(f"{f}: its progress code decoder differs from design/progress-code.js")
    m = CP_DATA.search(page)
    try:
        segs = page_entries(json.loads(m.group(1))) if m else None
    except ValueError:
        segs = None
    if segs is None:
        out.append(f'{f}: its <script type="application/json" id="cp-data"> page data is missing or unreadable')
        segs = {}
    files = dict(tool_files(cfg))
    by_slug = {x["slug"]: x for x in cfg["tools"]}
    claimed = set()
    for g in sorted(segs):
        s = segs[g]
        tag = f" ({s['k']})" if s["k"] else ""
        slug = (s["href"] or "").strip("/") or (s["k"] or "").replace(".", "/", 1)
        tool = by_slug.get(slug)
        if not slug:
            out.append(f"{f}: segment {g} has neither an href nor a k, so no tool page carries it")
            continue
        if not tool or tool is t:
            out.append(f"{f}: segment {g}{tag} names {slug}, which tools.json doesn't list as a tool page")
            continue
        for name in [n for n, x in files.items() if x is tool]:
            claimed.add(name)
            if not (ROOT / name).is_file():
                out.append(f"{name}: is missing, but {f} lists it as segment {g}{tag}; prepare it again from its current source")
                continue
            found = DONE_BLOCK.findall((ROOT / name).read_bytes().decode("utf-8"))
            r = done_record(found[0]) if len(found) == 1 else None
            if not found:
                out.append(f"{name}: carries no /*@t4t-done*/ block, but {f} lists it as segment {g}{tag}; "
                           "prepare it again from its current source")
            elif len(found) != 1:
                out.append(f"{name}: carries {len(found)} /*@t4t-done*/ blocks (exactly one expected)")
            elif r is None:
                out.append(f'{name}: its /*@t4t-done*/ block holds no {{"g":…,"k":…,"ids":[…]}} slot list')
            elif r["g"] != g or r["k"] != s["k"]:
                out.append(f"{name}: its /*@t4t-done*/ block is segment {r['g']}" + (f" ({r['k']})" if r["k"] else " without a k")
                           + f", but {f} lists this page as "
                           f"segment {g}{tag}")
            elif r["ids"] != s["ids"]:
                out.append(f"{name}: its slot list for segment {g} ({len(r['ids'])} slots) differs from {f}'s ({len(s['ids'])} slots)")
    for name, tool in files.items():
        if name in claimed or name == f or tool.get("category") != t.get("category") or not (ROOT / name).is_file():
            continue
        found = DONE_BLOCK.findall((ROOT / name).read_bytes().decode("utf-8"))
        if found:
            r = done_record(found[0])
            what = (f"segment {r['g']}" + (f" ({r['k']})" if r["k"] else "")) if r else "a segment"
            out.append(f"{name}: carries a /*@t4t-done*/ block for {what}, but {f} lists no segment for this page"
                       + (f" (segment {r['g']} is missing from {f})" if r and r["g"] not in segs else ""))
    return out


def executable_scripts(page):
    """Bodies of inline scripts the browser will run (skips src= scripts and data blocks like JSON-LD)."""
    out = []
    for m in SCRIPT.finditer(page):
        attrs, body = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue
        t = SCRIPT_TYPE.search(attrs)
        if t and t.group(1).lower() not in RUNS:
            continue
        out.append(body)
    return out


DATA_BLOCK = re.compile(r'<script type="application/octet-stream" id="(vendor-[a-z]+)">')
JS_TYPES = {"application/ecmascript", "application/javascript", "application/x-ecmascript", "application/x-javascript",
            "text/ecmascript", "text/javascript", "text/javascript1.0", "text/javascript1.1", "text/javascript1.2",
            "text/javascript1.3", "text/javascript1.4", "text/javascript1.5", "text/jscript", "text/livescript",
            "text/x-ecmascript", "text/x-javascript", "module"}


class PageTags(HTMLParser):
    """Every start tag of every element as a browser reads it: attribute names in lower case, values unescaped, the
    first of any repeated attribute kept, and each script's text kept as written."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self._body = [], None

    def handle_starttag(self, tag, attrs):
        first = {}
        for k, v in attrs:
            first.setdefault(k, v or "")
        self.tags.append({"tag": tag, "attrs": first, "raw": self.get_starttag_text(), "body": [] if tag == "script" else None})
        self._body = self.tags[-1]["body"]

    def handle_data(self, data):
        if self._body is not None:
            self._body.append(data)

    def handle_endtag(self, tag):
        self._body = None


def script_runs(attrs):
    """The browser's rule: type trimmed of whitespace (or text/ + language when type is absent); an empty or absent
    type, a JavaScript type, or module runs, and every other type is data."""
    if "type" in attrs:
        kind = attrs["type"].strip(" \t\n\r\f").lower()
    elif attrs.get("language"):
        kind = "text/" + attrs["language"].strip(" \t\n\r\f").lower()
    else:
        kind = ""
    return kind == "" or kind in JS_TYPES, kind


def data_block_problems(page, pins):
    """With blob: in script-src, page code can run what it decodes from a data block, so the refusal checks above
    (which read the page text) see only the base64. The page's loader takes the element carrying a vendor-* id, so
    every place encoded code could sit counts, read the way the browser reads it:
      - each data block is exactly <script type="application/octet-stream" id="vendor-NAME"> holding base64 that decodes
        to a pinned file, each pin appears exactly once, and each vendor-* id belongs to one data block;
      - every other element of any kind keeps clear of vendor-* ids and of octet-stream in its attributes;
      - every other non-running script block is JSON-LD;
      - this check and the script hashing above agree on which scripts run;
      - outside the data blocks' own tags, vendor- and octet-stream appear only inside the page's running scripts."""
    p = PageTags()
    p.feed(page)
    p.close()
    out, seen, ids, running, inside = [], [], [], [], {"vendor-": 0, "octet-stream": 0}
    for t in p.tags:
        attrs, raw = t["attrs"], t["raw"]
        el = attrs.get("id", "")
        block = t["tag"] == "script" and DATA_BLOCK.fullmatch(raw)
        label = f"<{t['tag']}> " + (f"id {el}" if el else "without an id")
        if block:
            for k in inside:
                inside[k] += raw.lower().count(k)
            ids.append(block.group(1))
            body = "".join(t["body"])
            try:
                data = base64.b64decode(re.sub(r"\s+", "", body), validate=True)
            except ValueError:
                out.append(f"carries a data block ({label}) that holds something other than base64")
                continue
            h = hashlib.sha256(data).hexdigest()
            seen.append(h)
            if h not in pins:
                out.append(f"carries a data block ({label}, sha256 {h}) outside the --pin-block list")
            continue
        if el.strip(" \t\n\r\f").lower().startswith("vendor-"):
            out.append(f"carries an element ({label}) with a data block's id; with --allow-script-blob, vendor-* ids belong to the data blocks alone")
        elif any("octet-stream" in v.lower() for v in attrs.values()):
            out.append(f"carries an element ({label}) marked octet-stream outside the exact data-block form {DATA_BLOCK.pattern}")
        if t["tag"] != "script":
            continue
        runs, kind = script_runs(attrs)
        if runs:
            if "src" not in attrs:
                running.append("".join(t["body"]))
            continue
        if "octet-stream" in kind:
            out.append(f"carries a data block ({label}) outside the exact form {DATA_BLOCK.pattern}")
        elif kind != "application/ld+json":
            out.append(f"carries a script block of type {kind} ({label}); with --allow-script-blob, data blocks are application/octet-stream and pinned")
    if running != executable_scripts(page):
        out.append("holds scripts that a browser reads differently from the script hashing (an attribute or tag form it reads another way)")
    for k, n in inside.items():
        n += sum(b.lower().count(k) for b in running)
        if page.lower().count(k) != n:
            out.append(f"mentions {k} outside its data blocks and running scripts ({page.lower().count(k) - n} time(s)), in a form this check reads differently from a browser")
    out += [f"carries the data-block id {i} {ids.count(i)} times (exactly once expected)" for i in sorted(set(ids)) if ids.count(i) != 1]
    out += [f"carries the pinned file {h} {seen.count(h)} times (exactly once expected)" for h in sorted(pins) if seen.count(h) != 1]
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
    ap.add_argument("--allow-script", action="append", default=[], metavar="URL", help="allow scripts from this exact https address prefix")
    ap.add_argument("--accept-runtime-fallback", action="store_true", help="accept guarded window.claude use that falls back when absent")
    ap.add_argument("--frame-guard", action="store_true", help="add a guard that refuses to run inside another site's frame")
    ap.add_argument("--allow-connect", action="append", default=[], metavar="URL", help="allow fetching data from this exact https address prefix")
    ap.add_argument("--allow-wasm", action="store_true", help="allow WebAssembly ('wasm-unsafe-eval'); still no eval of JavaScript")
    ap.add_argument("--allow-worker-blob", action="store_true", help="allow a web worker started from a blob: address")
    ap.add_argument("--allow-connect-data", action="store_true", help="add data: to connect-src (an engine decoding its own embedded WebAssembly); data: never reaches the network")
    ap.add_argument("--allow-script-blob", action="store_true", help="add blob: to script-src (libraries the page decodes from its own embedded data blocks, each checked against --pin-block)")
    ap.add_argument("--pin-block", action="append", default=[], metavar="SHA256", help="with --allow-script-blob: the SHA-256 of one file the page carries as a data block (repeat for each)")
    ap.add_argument("--out", default="index.html", metavar="NAME", help="file name to write inside SLUG/ (default index.html)")
    ap.add_argument("--category", help="the tool's category slug (add_tools.py passes it; otherwise read from tools.json)")
    ap.add_argument("--series", help="with --category: the tool's series slug")
    ap.add_argument("--section", help="with --category: the tool's section slug")
    a = ap.parse_args()
    pins = {h.lower() for h in a.pin_block}
    if any(not re.fullmatch(r"[0-9a-f]{64}", h) for h in pins):
        sys.exit("--pin-block takes a SHA-256 in hex (64 characters).")
    if a.allow_script_blob and not pins:
        sys.exit("--allow-script-blob needs the SHA-256 of each embedded file it may run: add one --pin-block SHA256 per data block.")
    if pins and not a.allow_script_blob:
        sys.exit("--pin-block goes with --allow-script-blob.")
    if not re.fullmatch(r"[\w.-]+\.html", a.out) or a.out.startswith("."):
        sys.exit(f"--out must be a plain .html file name: {a.out}")

    page = MARK.sub("", Path(a.source).read_text(encoding="utf-8"))
    page = re.sub(r'<meta\s+http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*>\s*', "", page, flags=re.I)
    problems = [why for rx, why in BLOCKERS if re.search(rx, page, re.I)]
    if a.accept_runtime_fallback:
        problems = [w for w in problems if "claude.ai-only" not in w]
    if a.allow_script_blob:
        problems += data_block_problems(page, pins)
    for u in a.allow_script:
        if not re.match(r"https://[\w.-]+/", u):
            sys.exit(f"--allow-script must be an https:// address: {u}")
    for u in a.allow_connect:
        if not re.match(r"https://[\w.-]+/", u):
            sys.exit(f"--allow-connect must be an https:// address: {u}")
    for why in problems:
        print(f"CHECK FAILED: the page {why}.")
    if problems and not a.force:
        sys.exit("Not written. Make the page self-contained, or re-run with --force after reviewing.")
    if not re.search(r"<head\b[^>]*>", page, re.I) or not re.search(r"</body\s*>", page, re.I):
        sys.exit("Not written: the page needs <head> and </body>.")

    slug = a.slug.strip("/")
    url = f"{SITE}/{slug}/"
    if a.frame_guard:
        guard = ("<script>if(window.top!==window.self){document.addEventListener('DOMContentLoaded',function(){var m=document.createElement('main');"
                 "m.setAttribute('style','max-width:520px;margin:12vh auto;padding:28px;font:16px/1.5 system-ui,sans-serif;text-align:center');"
                 "var h=document.createElement('h1');h.textContent='Open this tool in its own tab';var p=document.createElement('p');"
                 "p.textContent=\"To protect your data, this tool doesn't run inside another website.\";var a=document.createElement('a');"
                 "a.href=location.href.split('#')[0];a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open it directly';"
                 "m.append(h,p,a);document.body.replaceChildren(m);});throw new Error('framed');}</script>\n")
        bm = re.search(r"<body\b[^>]*>\s*", page, re.I)
        page = page[:bm.end()] + guard + page[bm.end():]
    cat, extra_tool = tool_place(CFG, slug, a)
    if not cat:
        print(f"Note: {slug} isn't in tools.json yet, so it gets no site bar. For a Cyber tool, pass --category cyber "
              "(plus --series or --section), or prepare it again once tools.json lists it.")
    nav = nav_category(CFG, cat) if cat else None
    if nav:
        # the site bar, script included, goes in before the hashes are worked out, so the policy pins its script
        at, before = nav_at(page), len(executable_scripts(page))
        if at is None:
            sys.exit("Not written: the page needs <body>.")
        page = page[:at] + nav_block(CFG, cat, slug + "/", ("tool", slug), tool_page=True, extra_tool=extra_tool) + page[at:]
        if len(executable_scripts(page)) != before + 1:
            sys.exit("Not written: the site bar's script didn't land as one script of its own (check the page's <body> tag).")
    hashes = page_hashes(page)
    scripts = " ".join(hashes + (["'wasm-unsafe-eval'"] if a.allow_wasm else []) + sorted(a.allow_script) + (["blob:"] if a.allow_script_blob else []))
    csp = "default-src 'none'; " + (f"script-src {scripts}; " if scripts else "") + \
          (f"connect-src {' '.join((['data:'] if a.allow_connect_data else []) + sorted(a.allow_connect))}; " if a.allow_connect or a.allow_connect_data else "") + \
          ("worker-src blob:; " if a.allow_worker_blob else "") + \
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
    foot = foot_block(CFG, slug, cat)
    body_end = list(re.finditer(r"</body\s*>", page, re.I))[-1]
    page = page[:body_end.start()] + foot + page[body_end.start():]

    out = ROOT / slug / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
    print(f"Wrote {out.relative_to(ROOT)}: {len(hashes)} script(s) pinned, " + (f"{len(pins)} data block(s) pinned, " if pins else "") + f"{len(page.encode()):,} bytes.")
    if a.out == "index.html":
        print('Next: add it to tools.json (leave "sha256" and "updated" empty), then run build_hub.py.')
    else:
        print(f"Next: list {slug}/{a.out} under the tool's \"extras\" in tools.json, then run build_hub.py.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--refresh-nav"]:
        refresh_nav(sys.argv[2:])
    elif sys.argv[1:] == ["--check-codec"]:
        check_codec()
    else:
        main()

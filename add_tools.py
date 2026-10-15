#!/usr/bin/env python3
"""Prepare and register tools from a manifest in one step: the standard way to add or update tools.

Usage:
  py add_tools.py MANIFEST.json SOURCE_DIR [--only SLUG]... [--dry-run]

  MANIFEST.json  a file in manifests/: slug, card text, and prep options for each tool of a series, section, or category
  SOURCE_DIR     a folder OUTSIDE this repository with the source pages (.html) and references (.txt)
  --only SLUG    process only this tool (repeatable)
  --dry-run      show which file matches which tool, change nothing

For each manifest tool whose source page is found in SOURCE_DIR (matched by the manifest's "match"
patterns against file names first, then page titles), it:
  1. cleans a copy: removes Google Fonts tags, applies the manifest's exact text replacements, and
     links the series strip (<span class="jack">Name</span>) to the other tools of the series;
  2. runs prepare_tool.py on it, which writes SLUG/index.html (hash-pinned CSP, preview tags, hub link);
  3. copies its reference .txt into SLUG/, when the manifest asks for one and it is found;
  4. adds or updates its tools.json entry (build_hub.py then fills in size, SHA-256, and date).
Tools with no source page are skipped and left as they are. Next: build_hub.py. Standard library only.
"""
import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = ROOT / "tools.json"
CARD = ("name", "tagline", "description", "badges", "file", "download_as", "icon", "category", "series", "section")
GFONT_LINK = re.compile(r'[ \t]*<link\b[^>]*\bhref\s*=\s*["\']https?://fonts\.(?:googleapis|gstatic)\.com[^>]*>[ \t]*\r?\n?', re.I)
GFONT_IMPORT = re.compile(r'@import\s+(?:url\()?\s*["\']?https?://fonts\.googleapis\.com[^;]*;', re.I)
JACK = re.compile(r'<span class="jack( on)?"((?:\s+style="[^"]*")?)>([^<]+)</span>')
JACK_STYLE = ('<style>a.jack{color:inherit;text-decoration:none}a.jack:hover,a.jack:focus-visible'
              '{color:var(--ink);text-decoration:underline;text-underline-offset:3px}</style>\n')
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def hay(path):
    """(file name, page title or first lines), lower-cased: what "match" patterns are tested against."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<title[^>]*>([\s\S]*?)</title>", text, re.I) if path.suffix.lower() in (".html", ".htm") else None
    return path.name.lower(), " ".join((m.group(1) if m else text[:300]).split()).lower()


def hit(spec, s):
    return any(re.search(p, s) for p in spec["match"]) and not any(re.search(p, s) for p in spec.get("exclude", []))


def find(spec, files):
    by_name = [f for f, (name, _) in files.items() if hit(spec, name)]
    return by_name or [f for f, (_, title) in files.items() if hit(spec, title)]


def clean(text, s, specs, live):
    notes, errs, p = [], [], s["prep"]
    if p.get("strip_google_fonts", True):
        text, n1 = GFONT_LINK.subn("", text)
        text, n2 = GFONT_IMPORT.subn("", text)
        if n1 + n2:
            notes.append(f"removed {n1 + n2} Google Fonts tag(s)")
    for old, new in p.get("replace", []):
        n = text.count(old)
        if n == 1:
            text = text.replace(old, new)
        elif not (n == 0 and new in text):
            errs.append(f"replace: expected this text once, found it {n} time(s): {old[:70]}")
    if p.get("link_series_strip") and s.get("series"):
        parent = s["slug"].rpartition("/")[0]
        mates = [m for m in specs if m.get("series") == s["series"]]
        linked = 0

        def link(mo):
            nonlocal linked
            style, label = mo.group(2), mo.group(3)
            lab = " ".join(label.split()).lower()
            tgt = next((m for m in mates if m["name"].lower() == lab), None) or next((m for m in mates if hit(m, lab)), None)
            if tgt is None:
                return mo.group(0)
            if tgt["slug"] == s["slug"]:
                return f'<span class="jack on"{style} aria-current="page">{label}</span>'
            if tgt["slug"] not in live or tgt["slug"].rpartition("/")[0] != parent:
                return mo.group(0)
            linked += 1
            return f'<a class="jack"{style} href="../{tgt["slug"].rpartition("/")[2]}/">{label}</a>'

        text = JACK.sub(link, text)
        if linked and "a.jack{" not in text:
            i = text.lower().find("</head>")
            text = text[:i] + JACK_STYLE + text[i:]
        notes.append(f"linked {linked} series-strip item(s)" if linked else "no series strip linked")
    return text, notes, errs


def main():
    ap = argparse.ArgumentParser(description="Prepare and register tools from a manifest.")
    ap.add_argument("manifest"); ap.add_argument("source_dir")
    ap.add_argument("--only", action="append", default=[], metavar="SLUG")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    src = Path(a.source_dir).resolve()
    if not src.is_dir():
        sys.exit(f"Source folder not found: {src}")
    if src == ROOT or ROOT in src.parents:
        sys.exit("Keep sources outside this repository, e.g. ../tool4that-src/<series>.")
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    cats, sers = {c["slug"] for c in cfg["categories"]}, {s["slug"] for s in cfg.get("series", [])}
    secs = {s["slug"] for s in cfg.get("sections", [])}

    d = man.get("defaults", {})
    specs = []
    for t in man["tools"]:
        s = {**d, **t, "prep": {**d.get("prep", {}), **t.get("prep", {})}}
        s["reference"] = None if t.get("reference") is False else ({**d.get("reference", {}), **t.get("reference", {})} or None)
        s.setdefault("category", man.get("category")); s.setdefault("series", man.get("series"))
        s.setdefault("section", man.get("section"))
        s.setdefault("file", s["slug"] + "/index.html")
        s.setdefault("download_as", s["slug"].rpartition("/")[2] + ".html")
        if s["category"] not in cats:
            sys.exit(f'{s["slug"]}: category "{s["category"]}" is not in tools.json.')
        if s.get("series") and s["series"] not in sers:
            sys.exit(f'{s["slug"]}: series "{s["series"]}" is not in tools.json; add it under "series" first.')
        if s.get("section") and s["section"] not in secs:
            sys.exit(f'{s["slug"]}: section "{s["section"]}" is not in tools.json; add it under "sections" first.')
        specs.append(s)
    unknown = set(a.only) - {s["slug"] for s in specs}
    if unknown:
        sys.exit("--only: not in this manifest: " + ", ".join(sorted(unknown)))
    todo = [s for s in specs if not a.only or s["slug"] in a.only]

    listing = lambda exts: {f: hay(f) for f in sorted(src.iterdir())
                            if f.is_file() and f.suffix.lower() in exts and not f.name.startswith(("_", "."))}
    pages, refs = listing((".html", ".htm")), listing((".txt",))
    plan, problems = [], []
    for s in todo:
        hits = find(s, pages)
        if len(hits) > 1:
            problems.append(f'{s["slug"]}: {len(hits)} pages match ({", ".join(h.name for h in hits)}); keep one, or tighten "match"')
            continue
        ref = None
        if hits and s["reference"]:
            rh = find(s, refs)
            if len(rh) > 1:
                problems.append(f'{s["slug"]}: {len(rh)} .txt files match ({", ".join(h.name for h in rh)}); keep one')
            ref = rh[0] if len(rh) == 1 else None
        plan.append((s, hits[0] if hits else None, ref))
    claimed = {}
    for s, page, ref in plan:
        for f in (page, ref):
            if f:
                claimed.setdefault(f, []).append(s["slug"])
    problems += [f'{f.name} matches more than one tool ({", ".join(w)}); rename it or tighten "match"' for f, w in claimed.items() if len(w) > 1]

    print(f"{Path(a.manifest).name}  <-  {src}")
    for s, page, ref in plan:
        if page:
            print(f'  {s["slug"]:<32} {page.name}  [title: {pages[page][1][:60]}]' + (f"  + {ref.name}" if ref else ("  (no .txt reference found)" if s["reference"] else "")))
        else:
            print(f'  {s["slug"]:<32} (no source page found: skipped, left as it is)')
    unused = [f.name for f in list(pages) + list(refs) if f not in claimed]
    if unused and not a.only:
        print("  Not used: " + ", ".join(unused))
    if problems:
        sys.exit("Stopped, nothing changed:\n  " + "\n  ".join(problems))
    plan = [p for p in plan if p[1]]
    if a.dry_run or not plan:
        print("Dry run: nothing changed." if a.dry_run else "Nothing to do.")
        return

    live = {t["slug"] for t in cfg["tools"]} | {s["slug"] for s, _, _ in plan}
    failed = 0
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        for s, page, ref in plan:
            text, notes, errs = clean(page.read_text(encoding="utf-8"), s, specs, live)
            if errs:
                failed += 1
                print(f'  FAILED {s["slug"]}: ' + "; ".join(errs))
                continue
            staged = Path(tmp) / page.name
            staged.write_text(text, encoding="utf-8", newline="")
            cmd = [sys.executable, str(ROOT / "prepare_tool.py"), str(staged), s["slug"], "--name", s["name"],
                   "--description", s.get("page_description") or s["description"], "--icon", s.get("emoji", "🧰")]
            for u in s["prep"].get("allow_script", []):
                cmd += ["--allow-script", u]
            cmd += ["--accept-runtime-fallback"] if s["prep"].get("accept_runtime_fallback") else []
            cmd += ["--frame-guard"] if s["prep"].get("frame_guard") else []
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            if r.returncode:
                failed += 1
                print(f'  FAILED {s["slug"]}:\n    ' + (r.stdout + r.stderr).strip().replace("\n", "\n    "))
                continue
            card = {k: s[k] for k in CARD if s.get(k) is not None}
            entry = next((t for t in cfg["tools"] if t["slug"] == s["slug"]), None)
            if entry is None:
                same = [i for i, t in enumerate(cfg["tools"]) if s.get("series") and t.get("series") == s["series"]] \
                    or [i for i, t in enumerate(cfg["tools"]) if t.get("category") == s["category"]] or [len(cfg["tools"]) - 1]
                entry = {"slug": s["slug"], **card}
                cfg["tools"].insert(max(same) + 1, entry)
            else:
                entry.update(card)
            if ref:
                dest = f'{s["slug"]}/{s["reference"].get("file", "reference.txt")}'
                (ROOT / dest).write_bytes(ref.read_bytes())
                entry["extras"] = [{"label": s["reference"].get("label", "Reference .txt"), "file": dest,
                                    "download_as": s["reference"].get("download_as") or s["download_as"].rsplit(".", 1)[0] + "-reference.txt"}]
                notes.append(f"copied {ref.name}")
            entry.setdefault("sha256", ""); entry.setdefault("updated", "")
            print(f'  OK     {s["slug"]}: ' + r.stdout.strip().splitlines()[0].split(": ", 1)[-1].rstrip(".") + ("; " + "; ".join(notes) if notes else ""))
    CFG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"tools.json updated ({len(plan) - failed} tool(s)). Next: py build_hub.py   (Linux/macOS: python3 build_hub.py)")
    if failed:
        sys.exit(f"{failed} tool(s) failed: fix the source page (see messages above), then re-run.")


if __name__ == "__main__":
    main()

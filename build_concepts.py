#!/usr/bin/env python3
"""Check concepts.json and confirm every place it lists against the published tool pages.

Usage:
  py build_concepts.py [--check] [--strict] [--links]

  --check             accepted for older instructions; this script never writes anything
  --strict            exit with an error if any place can't be confirmed (default: list it)
  --links             also request every reference URL and list the ones that fail (needs internet)

concepts.json lists domains, concepts (layers, prerequisites, references), and the places where each
concept is learned or practiced. This script checks the data (unique ids, known tools, kinds, and layers;
prerequisites that exist and don't loop), then confirms every place against the tool's published page in
this repository (SLUG/index.html plus its extras .txt): each "where" step and at least one "find" term must
appear, case-insensitive, as whole words. Places it can't confirm are listed; the Study Map
(../tool4that-src/curriculum/build_study_map.py, which imports this module) leaves them out, so it never
points at something a tool doesn't have. Concepts with nothing hands-on are listed as gaps.
Standard library only; reads UTF-8.
"""
import argparse, html, json, re, sys, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "concepts.json"
KINDS = ("learn", "drill", "build", "fix", "lab")
HANDS_ON = {"drill", "build", "fix", "lab"}
LAYERS = ("1", "2", "3", "4", "5", "6", "7", "host")
SOURCES = ("standard", "vendor")
PLATFORMS = ("general", "windows", "linux", "freebsd", "cisco")
BADGES = (("Cisco IOS", "cisco"), ("FreeBSD", "freebsd"), ("Linux", "linux"), ("Windows Server", "windows"), ("Windows", "windows"))
SEP = "\u203a"
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def norm(text):
    """Text as matched: entities decoded, JS quote escapes and curly quotes straightened, spaces collapsed, lower case."""
    text = html.unescape(text).replace("\\'", "'").replace('\\"', '"')
    for a, b in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u00a0", " ")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).lower()


def found(term, text):
    """True if the term appears in the normalized text, as a whole word wherever it starts or ends with a letter or digit."""
    t = norm(term).strip()
    pre = r"(?<![a-z0-9])" if t[:1].isalnum() else ""
    post = r"(?![a-z0-9])" if t[-1:].isalnum() else ""
    return bool(t) and re.search(pre + re.escape(t) + post, text) is not None


def as_list(v):
    return [v] if isinstance(v, str) else list(v or [])


def tool_platform(tool, overrides):
    if tool["slug"] in overrides:
        return overrides[tool["slug"]]
    return next((p for b, p in BADGES if b in tool.get("badges", [])), "general")


def tool_group(tool, cfg):
    for key, items in (("series", cfg.get("series", [])), ("section", cfg.get("sections", []))):
        hit = next((x for x in items if x["slug"] == tool.get(key)), None)
        if hit:
            return hit["title"]
    cat = next((c for c in cfg["categories"] if c["slug"] == tool.get("category")), None)
    return cat["title"] if cat else tool.get("category", "")


def validate(data, tools):
    errs = []
    doms = [d.get("id") for d in data.get("domains", [])]
    if not doms or len(set(doms)) != len(doms) or not all(isinstance(d, str) and ID.match(d) for d in doms):
        errs.append("domains: each needs a unique lower-case id")
    errs += [f'domain {d.get("id")}: needs a title' for d in data.get("domains", []) if not d.get("title")]
    for slug, plat in data.get("platforms", {}).items():
        if slug not in tools:
            errs.append(f'platforms: "{slug}" is not a tool in tools.json')
        if plat not in PLATFORMS:
            errs.append(f'platforms: "{plat}" must be one of: {", ".join(PLATFORMS)}')
    ids = set()
    for c in data.get("concepts", []):
        cid, at = c.get("id"), f'concept {c.get("id")}'
        if not isinstance(cid, str) or not ID.match(cid):
            errs.append(f"{at}: id must be a lower-case slug")
        elif cid in ids:
            errs.append(f"{at}: duplicate id")
        ids.add(cid)
        errs += [f"{at}: needs a {k}" for k in ("name", "summary") if not str(c.get(k, "")).strip()]
        if c.get("domain") not in doms:
            errs.append(f'{at}: domain "{c.get("domain")}" is not in domains')
        errs += [f'{at}: layer "{x}" must be one of: {", ".join(LAYERS)}' for x in c.get("layers", []) if x not in LAYERS]
        for r in c.get("refs", []):
            if not r.get("title") or not str(r.get("url", "")).startswith("https://"):
                errs.append(f"{at}: each reference needs a title and an https:// url")
            if r.get("src") not in SOURCES:
                errs.append(f'{at}: reference src must be one of: {", ".join(SOURCES)}')
        for i, loc in enumerate(c.get("locations", []), 1):
            lw = f"{at}, place {i}"
            if loc.get("tool") not in tools:
                errs.append(f'{lw}: tool "{loc.get("tool")}" is not in tools.json')
            kinds = as_list(loc.get("kind"))
            if not kinds or any(k not in KINDS for k in kinds):
                errs.append(f'{lw}: kind must be one or more of: {", ".join(KINDS)}')
            if not loc.get("where") and not loc.get("find"):
                errs.append(f"{lw}: needs a where or a find, so it can be confirmed")
    for c in data.get("concepts", []):
        errs += [f'concept {c.get("id")}: prerequisite "{p}" is not a concept' for p in c.get("prereqs", []) if p not in ids]
    graph = {c.get("id"): [p for p in c.get("prereqs", []) if p in ids] for c in data.get("concepts", [])}
    state = {}

    def visit(n, trail):
        state[n] = 1
        for p in graph.get(n, []):
            if state.get(p) == 1:
                errs.append("prerequisite loop: " + " -> ".join(trail + [n, p]))
            elif not state.get(p):
                visit(p, trail + [n])
        state[n] = 2

    for n in graph:
        if not state.get(n):
            visit(n, [])
    return errs


def confirm(data, cfg, keep):
    tools = {t["slug"]: t for t in cfg["tools"]}
    cache = {}

    def page(slug):
        if slug not in cache:
            t = tools[slug]
            files = [t["file"]] + [x["file"] for x in t.get("extras", [])]
            parts = [(ROOT / f).read_text(encoding="utf-8", errors="replace") for f in files if (ROOT / f).is_file()]
            cache[slug] = norm("\n".join(parts)) if parts else None
        return cache[slug]

    out, ok, left = [], 0, []
    for c in data["concepts"]:
        places = []
        for loc in c.get("locations", []):
            text = page(loc["tool"])
            steps = [s.strip() for s in loc.get("where", "").split(SEP) if s.strip()]
            terms = as_list(loc.get("find"))
            item = {"tool": loc["tool"], "kind": as_list(loc["kind"])}
            if steps:
                item["where"] = f" {SEP} ".join(steps)
            if loc.get("note"):
                item["note"] = loc["note"]
            if text is None:
                why = f'no page at {tools[loc["tool"]]["file"]}'
            else:
                missing = [s for s in steps if not found(s, text)]
                hits = [x for x in terms if found(x, text)]
                if missing:
                    why = "not found: " + ", ".join(f'"{s}"' for s in missing)
                elif terms and not hits:
                    why = "none found: " + ", ".join(f'"{x}"' for x in terms)
                else:
                    why = None
                    if hits and not steps:
                        item["look"] = hits[0]
            if why:
                seen = [x for x in [c["name"]] + c.get("aka", []) if text and found(x, text)]
                left.append(f'{c["id"]} @ {loc["tool"]}: {why}' + (f'; the page mentions {", ".join(repr(x) for x in seen[:5])}' if seen else ""))
                if not keep:
                    continue
                item["unchecked"] = True
                if terms and not steps:
                    item["look"] = terms[0]
            else:
                ok += 1
            places.append(item)
        out.append({"id": c["id"], "name": c["name"], "domain": c["domain"], "layers": c.get("layers", []),
                    "aka": c.get("aka", []), "summary": c["summary"], "prereqs": c.get("prereqs", []),
                    "refs": [{k: r[k] for k in ("title", "url", "src")} for r in c.get("refs", [])], "locations": places})
    return out, ok, left


def check_links(concepts):
    urls = sorted({r["url"] for c in concepts for r in c["refs"]})
    bad = 0
    print(f"checking {len(urls)} reference URLs:")
    for u in urls:
        status = None
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(u, method=method, headers={"User-Agent": "Mozilla/5.0 (Tool4That link check)"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    status = r.status
                break
            except urllib.error.HTTPError as e:
                status = e.code
                if e.code not in (403, 405, 429):
                    break
            except Exception as e:
                status = type(e).__name__
                break
        good = isinstance(status, int) and status < 400
        bad += not good
        print(f'  {"ok  " if good else "FAIL"} {status}  {u}')
    if bad:
        print(f"{bad} URL(s) failed. A 403 or 429 often means the site blocks scripts: open it in a browser before removing it.")


def main():
    ap = argparse.ArgumentParser(description="Check concepts.json and confirm every place against the tool pages.")
    ap.add_argument("--check", action="store_true", help="accepted for older instructions; nothing is ever written")
    ap.add_argument("--strict", action="store_true", help="exit with an error if any place can't be confirmed")
    ap.add_argument("--links", action="store_true", help="request every reference URL (needs internet)")
    a = ap.parse_args()

    cfg = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
    data = json.loads(DATA.read_text(encoding="utf-8"))
    tools = {t["slug"]: t for t in cfg["tools"]}
    errs = validate(data, tools)
    if errs:
        sys.exit("concepts.json has problems:\n  " + "\n  ".join(errs))
    concepts, ok, left = confirm(data, cfg, False)
    total = sum(len(c.get("locations", [])) for c in data["concepts"])
    print(f'concepts.json: {len(concepts)} concepts in {len(data["domains"])} domains, {total} places, '
          f'{sum(len(c["refs"]) for c in concepts)} references')
    print(f"confirmed {ok} of {total} places against the tool pages")
    if left:
        print(f"left out {len(left)} (fix where/find in concepts.json, or delete the place if the tool doesn't cover the concept):")
        print("  " + "\n  ".join(left))
    gaps = [c["id"] for c in concepts if not any(HANDS_ON & set(p["kind"]) for p in c["locations"])]
    if gaps:
        print(f"no hands-on place yet ({len(gaps)}): " + ", ".join(gaps))
    if a.links:
        check_links(concepts)
    if a.strict and left:
        sys.exit("--strict: places were left out.")
    print("Next: py ..\\tool4that-src\\curriculum\\build_study_map.py --repo .")


if __name__ == "__main__":
    main()

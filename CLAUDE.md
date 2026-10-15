# Tool4That: notes for Claude

Static site published twice from this **public** repository: the primary at https://freeapp4that.store/ (Cloudflare Pages, deploys on push, honors `_headers` and `_redirects`) and the backup at https://tool4that.github.io/ (GitHub Pages). Never set a custom domain in GitHub Pages settings, or the backup address would redirect to the primary. Canonical addresses point at the primary.

## Layout
- `index.html` (the category chooser), `all/index.html`, one `<category>/index.html` per category, one `<series>/index.html` per series (`net-drills/`, `lockdown-drills/`, `lockdown-range/`), `404.html`, `robots.txt`, `sitemap.xml`: **generated** by `build_hub.py` from `tools.json`. Don't hand-edit them; edit `tools.json` or the templates inside `build_hub.py`, then rebuild.
- `tools.json`: `categories` (slug, title, tagline, description, icon, note), `series` (slug, title, category, description, note: a named group of tools inside a category, with its own page), `sections` (slug, title, category, intro: an in-page grouping inside a category, one level *above* its series, with no page of its own, e.g. Learning and Practice under Cybersecurity), and `tools` (each with a `category` slug, an optional `series` slug, an optional `section` slug, and optional `extras`: more download buttons, e.g. a reference `.txt`). Category and series slugs and `all` are reserved folder names, so a tool slug can't reuse them. A series with no tools gets no page. **If a category defines any sections, every loose tool and every series in it must name a `section`** (a tool in a series inherits the series' section); `build_hub.py` refuses to build otherwise. A category with no sections renders exactly as before.
- `manifests/<group>.json` + `add_tools.py`: the standard way to prepare and register tools (see "Add or update tools").
- `concepts.json` + `build_concepts.py` + `design/concept-index.html`: the Concept Index (`concept-index/`), a generated tool that maps each cybersecurity concept to where it is learned and practiced (see "Concept Index").
- `<slug>/index.html`: one self-contained tool per folder, built elsewhere (see "Tool sources").
- `.nojekyll`: GitHub serves the files exactly as committed.
- `.gitattributes` (`* -text`): byte-exact commits, so each tool card's SHA-256 matches the served file.

## Rules
- **Never edit a tool's `index.html` here.** Its inline scripts are pinned by SHA-256 in its Content Security Policy, so any edit breaks the page. Rebuild from source, then copy it in.
- **After adding or updating a tool,** run `py build_hub.py` (Windows) or `python3 build_hub.py`, then commit.
- **After adding, renaming, or rebuilding a cybersecurity tool,** rebuild the Concept Index too (see "Concept Index"): a tool's labels may have changed.
- **`build_hub.py`, `prepare_tool.py`, and `add_tools.py` read and write UTF-8 with LF explicitly.** Keep it that way, so runs on Windows don't rewrite files with Windows line endings or garble text.
- **Hub pages run no JavaScript** (`default-src 'none'`). Keep it that way.
- **No analytics, trackers, or third-party scripts.**
- **Never commit personal data:** LES files, screenshots, real pay figures, names, IDs. Everything here is public.
- **Commit identity:** user.name "Tool4That", with the GitHub noreply email.
- **Before pushing,** show `git status` and wait for approval. Never force-push.

## Add or update tools
1. **Put the source pages outside this repository**, e.g. `../tool4that-src/<group>/` (one self-contained HTML file per tool; a tool's reference `.txt` goes beside it). File names or page titles must match the tool's `match` patterns in its manifest.
2. **Describe the tools in a manifest** (`manifests/finance.json`, `manifests/learning.json`, `manifests/net-drills.json`, `manifests/lockdown-drills.json`, `manifests/lockdown-range.json`): slug, card text, badges, icons, `match` patterns, a `section` for tools outside any series (manifest-wide or per tool), and prep options (`strip_google_fonts`, exact-text `replace` pairs, `link_series_strip`, `allow_script`, `accept_runtime_fallback`, `frame_guard`). For a new series, add it to `series` in `tools.json` first.
3. **Prepare and register them in one step:**
   ```
   py add_tools.py manifests/<group>.json ..\tool4that-src\<group> --dry-run
   py add_tools.py manifests/<group>.json ..\tool4that-src\<group>
   ```
   `--dry-run` only shows which file matches which tool. The real run cleans each page (drops Google Fonts tags, applies the replacements, links the series strip), runs `prepare_tool.py` (hash-pinned CSP, canonical address, preview tags, icon, link back to the hub), copies the reference `.txt`, and adds or updates the `tools.json` entry. Tools whose source isn't in the folder are left as they are; `--only <slug>` limits the run to one tool. If `prepare_tool.py` refuses a page (e.g. inline `onclick=` handlers, outside requests), fix the **source** and re-run.
4. **Rebuild the hub** with `py build_hub.py`. It validates `tools.json` and computes the sizes and SHA-256s.
5. **Test it.** Serve the folder (`py -m http.server 8000`), open the hub, category, series, and tool pages, confirm they work, and check DevTools shows no console errors (policy violations appear there).
   - Manual alternative to steps 2-3 for a one-off: `py prepare_tool.py SOURCE.html <slug> --name "Name" --description "One or two sentences." --icon "🔢"`, then add the `tools.json` entry by hand (leave `sha256` and `updated` empty).
6. **Publish.** Show `git status` and the diff, commit and push after approval, then check that the live page loads and its SHA-256 matches `tools.json`.
7. **Optionally redraw the hub preview image.** Edit `design/og-hub.html`, then render it at 1200×630, e.g. with headless Edge:
   ```
   & "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --headless=new --screenshot="$PWD\og-image.png" --window-size=1200,630 "$PWD\design\og-hub.html"
   ```

## Concept Index
`concept-index/` is generated, never hand-built. `build_concepts.py` reads `concepts.json` (domains; concepts with layers, prerequisites, and references; and the places where each concept is learned or practiced) and `tools.json`, then confirms every place against the published tool pages here (`<slug>/index.html` plus its extras `.txt`): each `where` step and at least one `find` term must appear, case-insensitive, as whole words. Places it can't confirm are left out and listed, so the index never points at something a tool doesn't have. It writes `../tool4that-src/learning/concept-index.html` from the template `design/concept-index.html`; `manifests/learning.json` puts it in the Learning section.
```
py build_concepts.py
py add_tools.py manifests/learning.json ..\tool4that-src\learning
py build_hub.py
```
- **A place was left out:** search that tool's page for the concept, then fix the place's `where` (the tool's own labels, joined with ` › `) or `find` (terms that must appear) in `concepts.json`. If the tool doesn't cover the concept, delete the place. Never add a place you haven't found in the tool.
- **Concepts with no hands-on place** are listed as gaps: candidates for new drills.
- `--check` validates without writing, `--strict` stops on any left-out place, `--links` requests every reference URL (needs internet), and `--keep-unverified` is for previews only: never publish its output.

## Tool sources (kept outside this repository, in `../tool4that-src/`)
- Net Drills (`net-drills/`): `manifests/net-drills.json` (links the series strip between drills). The four sources in `../tool4that-src/net-drills/` are the maintained copies; IOS CLI Lab, Config Audit, and Trouble Tickets started from the published pages (prepare_tool.py strips its own additions when re-run), and Subnet Sprint carries the `#f-levels` radio-scope fix that the original claude.ai artifact lacks.
- Lockdown Drills (`lockdown-drills/`): six OS hardening trainers (Windows 11, Windows Server, Linux Mint, Ubuntu, FreeBSD, Cisco IOS), each with a reference `.txt`; `manifests/lockdown-drills.json`.
- Lockdown Range (`lockdown-range/`): three browser-only hardening labs (Windows Range: Windows 11 + Server 2025; Linux Range: Ubuntu 24.04, Linux Mint 22, Ubuntu Server 24.04; Cisco Range: Packet Tracer-style IOS topology), each with a solution-walkthrough `.txt` (published as `reference.txt`, downloads as `*-walkthrough.txt`); `manifests/lockdown-range.json` (links the series strip; cards use the `screen` icon). Sources: `../tool4that-src/lockdown-range/` (the six files add_tools reads). Their editable parts, build scripts and tests: `../tool4that-src/lockdown-range-dev/` (`parts/<os>/NN-*.{html,css,js}` + `build.sh` concatenate into one page; `shared/check_page.py` mirrors this repo's refusal rules; `test/smoke.js` + `test/*-explore.js` replay every scenario to 100/100). Rebuild there, copy the six files into `../tool4that-src/lockdown-range/`, then run add_tools.py and build_hub.py here.
- Defense Ladder (`defense-ladder/`): a standalone cybersecurity learning ladder (no manifest, no series); source `../tool4that-src/defense-ladder/defense-ladder.html`. It sits in the **Learning** section of the Cybersecurity category. Prepare it with the one-off command: `py prepare_tool.py ..\tool4that-src\defense-ladder\defense-ladder.html defense-ladder --name "Defense Ladder" --description "DESCRIPTION" --icon "🎓"`, using the `description` from its `tools.json` entry (self-contained; no `--allow-script`, `--accept-runtime-fallback`, or `--frame-guard` needed).
- **Cybersecurity content is general training.** The cyber tools are a standalone cybersecurity course and labs, not material for any particular competition: no competition names, marks, rounds, scoring-engine terms, or links to competition sites, in visible text or in IDs, comments, file names, and storage keys. Material removed for that reason lives in `../tool4that-src/private/`, which never goes in this repository.
- PFAT, the Personal Finance Advisor Tool (`spend-lens/`, kept at that address; downloads as `pfat.html`): the claude.ai artifact "PFAT — Personal Finance Advisor Tool"; `manifests/finance.json` (swaps its Google Fonts for a system stack, allows pdf.js from cdnjs, frame guard).
- Maxed & Matched: `../maxed-and-matched-src`, which is **private**. Build there, then copy `dist/site/index.html` and `dist/site/og-image.png` into `maxed-and-matched/`.

# Tool4That: notes for Claude

Static GitHub Pages site for the org site `tool4that/tool4that.github.io`, served at https://tool4that.github.io/. This repository is **public**.

## Layout
- `index.html`, `404.html`, `robots.txt`, `sitemap.xml`: **generated** by `build_hub.py` from `tools.json`. Don't hand-edit them; edit `tools.json` or the templates inside `build_hub.py`, then rebuild.
- `<slug>/index.html`: one self-contained tool per folder, built elsewhere (see "Tool sources").
- `.nojekyll`: GitHub serves the files exactly as committed.
- `.gitattributes` (`* -text`): byte-exact commits, so each tool card's SHA-256 matches the served file.

## Rules
- **Never edit a tool's `index.html` here.** Its inline scripts are pinned by SHA-256 in its Content Security Policy, so any edit breaks the page. Rebuild from source, then copy it in.
- **After adding or updating a tool,** run `py build_hub.py` (Windows) or `python3 build_hub.py`, then commit.
- **`build_hub.py` and `prepare_tool.py` read and write UTF-8 with LF explicitly.** Keep it that way, so runs on Windows don't rewrite files with Windows line endings or garble text.
- **Hub pages run no JavaScript** (`default-src 'none'`). Keep it that way.
- **No analytics, trackers, or third-party scripts.**
- **Never commit personal data:** LES files, screenshots, real pay figures, names, IDs. Everything here is public.
- **Commit identity:** user.name "Tool4That", with the GitHub noreply email.
- **Before pushing,** show `git status` and wait for approval. Never force-push.

## Add a tool
1. **Prepare the page.** It must be one self-contained HTML file: no external scripts or network calls. Run:
   ```
   py prepare_tool.py SOURCE.html <slug> --name "Name" --description "One or two sentences." --icon "🔢"
   ```
   This checks the page, adds the hash-pinned security policy, a canonical address, preview tags, an icon, and a link back to the hub, then writes `<slug>/index.html`. For a series, use a shared folder, e.g. `net-drills/<tool>`.
2. **Add an entry to `tools.json`.** Copy an existing entry and leave `sha256` and `updated` empty. `category` groups cards under a heading; `category_notes` holds optional one-line notes per section. Icons: `check`, `wrench`, `terminal`, `search`, `subnet`, or default `4`.
3. **Rebuild the hub** with `py build_hub.py`. It computes the sizes and SHA-256s.
4. **Test it.** Open the page in a browser, confirm it works, and check DevTools shows no console errors (policy violations appear there).
5. **Publish.** Commit and push after showing the diff, then check that the live page loads and its SHA-256 matches `tools.json`.
6. **Optionally redraw the hub preview image.** Edit `design/og-hub.html`, then render it at 1200×630, e.g. with headless Edge:
   ```
   & "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --headless=new --screenshot="$PWD\og-image.png" --window-size=1200,630 "$PWD\design\og-hub.html"
   ```

## Tool sources (kept outside this repository)
- Net Drills: published from claude.ai artifacts, prepared with `prepare_tool.py`, with the series strip linked between drills.
- Maxed & Matched: `../maxed-and-matched-src`, which is **private**. Build there, then copy `dist/site/index.html` and `dist/site/og-image.png` into `maxed-and-matched/`.

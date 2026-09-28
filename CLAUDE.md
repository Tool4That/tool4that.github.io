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
- **Hub pages run no JavaScript** (`default-src 'none'`). Keep it that way.
- **No analytics, trackers, or third-party scripts.**
- **Never commit personal data:** LES files, screenshots, real pay figures, names, IDs. Everything here is public.
- **Commit identity:** user.name "Tool4That", with the GitHub noreply email.
- **Before pushing,** show `git status` and wait for approval. Never force-push.

## Add a tool
1. Create `<slug>/index.html`, plus any images it uses.
2. Add an entry to `tools.json`, copying the existing one. Leave `sha256` and `updated` empty.
3. Run `py build_hub.py`.
4. Commit and push, after showing the diff.
5. Check that the live page loads and its SHA-256 matches `tools.json`.

## Tool sources (kept outside this repository)
- Maxed & Matched: `../maxed-and-matched-src`, which is **private**. Build there, then copy `dist/site/index.html` and `dist/site/og-image.png` into `maxed-and-matched/`.

# Tool4That

**Need a tool for that? There's a Tool4That.**

Free, single-file tools that run in your browser: no sign-ups, no tracking, nothing uploaded.

Live at https://tool4that.github.io/

| Tool | What it does |
|---|---|
| [Maxed & Matched TSP Calculator](https://tool4that.github.io/maxed-and-matched/) | Your exact myPay TSP percentages from your LES. Max out without losing the BRS match. |

## Add a tool

1. Put the tool in its own folder: `<slug>/index.html`, plus any images it uses.
2. Add an entry to `tools.json`: copy the existing one and leave `sha256` and `updated` empty.
3. Rebuild the hub:
   ```bash
   python3 build_hub.py
   ```
4. Publish:
   ```bash
   git add -A && git commit -m "Add <tool>" && git push
   ```

`build_hub.py` regenerates `index.html`, `404.html`, `robots.txt`, and `sitemap.xml`. It computes each tool's size and SHA-256, and changes a tool's "Updated" date only when its file changes. It uses the Python standard library only.

## Verify a download

Compare the result with the SHA-256 listed on the tool's card:

```bash
sha256sum maxed-and-matched.html
shasum -a 256 maxed-and-matched.html
certutil -hashfile maxed-and-matched.html SHA256
```
- `sha256sum`: Linux.
- `shasum -a 256`: macOS.
- `certutil -hashfile … SHA256`: Windows.

## Notes

- **Hosting:** GitHub Pages. `.nojekyll` makes GitHub serve the files exactly as committed.
- **No custom security headers:** GitHub Pages can't send them. Instead:
  - every page carries its own Content Security Policy;
  - the hub runs no JavaScript at all;
  - tools that read personal data refuse to run inside another site's frame.
- **Independent:** these are independent projects, not affiliated with any government agency.

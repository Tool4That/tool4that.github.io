# Tool4That

**Need a tool for that? There's a Tool4That.**

Free, single-file tools that run in your browser: no sign-ups, no tracking, nothing uploaded.

Live at https://freeapp4that.store/ (primary) and https://tool4that.github.io/ (backup copy).

| Tool | What it does |
|---|---|
| [Maxed & Matched TSP Calculator](https://freeapp4that.store/maxed-and-matched/) | Your exact myPay TSP percentages from your LES. Max out without losing the BRS match. |
| [Subnet Sprint](https://freeapp4that.store/net-drills/subnet-sprint/) | Net Drills: network, broadcast, and host ranges; VLSM planning; IPv6. |
| [IOS CLI Lab](https://freeapp4that.store/net-drills/ios-cli-lab/) | Net Drills: configure a simulated router and switch, then prove it from two PCs. |
| [Config Audit](https://freeapp4that.store/net-drills/config-audit/) | Net Drills: find risky config lines, choose fixes, name what's missing. |
| [Trouble Tickets](https://freeapp4that.store/net-drills/trouble-tickets/) | Net Drills: diagnose the root cause from real device output. |

Net Drills are unofficial practice for the Cisco NetAcad Network Technician path and the CyberPatriot Cisco challenge, and are not affiliated with either.

## Add a tool

1. Prepare the page with `py prepare_tool.py SOURCE.html <slug> --name "…" --description "…" --icon "🔢"`. It checks the page is self-contained and adds the security policy.
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

- **Hosting, two copies from one repository:** Cloudflare Pages deploys the primary (`freeapp4that.store`) on every push and honors `_headers` and `_redirects`; GitHub Pages serves the backup (`tool4that.github.io`). Never set a custom domain in the GitHub Pages settings: GitHub would redirect the backup address to the primary, which defeats the purpose. `.nojekyll` makes GitHub serve the files exactly as committed.
- **No custom security headers:** GitHub Pages can't send them. Instead:
  - every page carries its own Content Security Policy;
  - the hub runs no JavaScript at all;
  - tools that read personal data refuse to run inside another site's frame.
- **Independent:** these are independent projects, not affiliated with any government agency.

# Tool4That

**Need a tool for that? There's a Tool4That.**

Free, single-file tools that run in your browser: no sign-ups, no tracking, nothing uploaded.

Live at https://freeapp4that.store/ (primary) and https://tool4that.github.io/ (backup copy). The home page is a category chooser; each category has its own page (`/finance/`, `/cyber/`), each series has its own page (`/net-drills/`, `/lockdown-drills/`, `/lockdown-range/`), and `/all/` lists everything. The Cybersecurity page is split into two in-page sections: **Learning** (concepts) and **Practice** (hands-on drills and hardening labs).

| Tool | What it does |
|---|---|
| [Maxed & Matched TSP Calculator](https://freeapp4that.store/maxed-and-matched/) | Your exact myPay TSP percentages from your LES. Max out without losing the BRS match. |
| [PFAT — Personal Finance Advisor Tool](https://freeapp4that.store/spend-lens/) | Add, paste, or import CSV/PDF statements; money-in, money-out HUD, paycheck plan, 30-day look ahead, plain-language checkup. |
| [Defense Ladder](https://freeapp4that.store/defense-ladder/) | Cybersecurity &rsaquo; Learning: a four-grade cybersecurity ladder (Freshman to Senior) built on Bloom's taxonomy and aligned with the NICE Framework and CIS Controls, from concepts to quizzes, drills, and a hardening checklist you build yourself. |
| [Concept Index](https://freeapp4that.store/concept-index/) | Cybersecurity &rsaquo; Learning: look up a concept (OSI layers, VLANs, account lockout) and see where to learn it and where to practice it across Defense Ladder, Net Drills, Lockdown Drills, and Lockdown Range; rate what you know to get a path through your gaps. |
| [Study Map](https://freeapp4that.store/study-map/) | Cybersecurity &rsaquo; Learning: a printable table of contents for the course: each concept, the Defense Ladder unit that teaches it, the drills and labs that practice it, a star for what every track needs, and the matching commands on each system. |
| [Subnet Sprint](https://freeapp4that.store/net-drills/subnet-sprint/) | Net Drills: subnet sandbox; network, broadcast, and host ranges; VLSM planning; IPv6. |
| [IOS CLI Lab](https://freeapp4that.store/net-drills/ios-cli-lab/) | Net Drills: configure a simulated router and switch, then prove it from two PCs. |
| [Config Audit](https://freeapp4that.store/net-drills/config-audit/) | Net Drills: find risky config lines, choose fixes, name what's missing. |
| [Trouble Tickets](https://freeapp4that.store/net-drills/trouble-tickets/) | Net Drills: diagnose the root cause from real device output. |
| [Windows 11 Lockdown](https://freeapp4that.store/lockdown-drills/windows-11/) | Lockdown Drills: Windows 11 baseline hardening, beginner to advanced, with a command reference (.txt). |
| [Windows Server Lockdown](https://freeapp4that.store/lockdown-drills/windows-server/) | Lockdown Drills: Windows Server baseline hardening, beginner to advanced, with a command reference (.txt). |
| [Linux Mint Lockdown](https://freeapp4that.store/lockdown-drills/linux-mint/) | Lockdown Drills: Linux Mint baseline hardening, beginner to advanced, with a command reference (.txt). |
| [Ubuntu Lockdown](https://freeapp4that.store/lockdown-drills/ubuntu/) | Lockdown Drills: Ubuntu baseline hardening, beginner to advanced, with a command reference (.txt). |
| [FreeBSD Lockdown](https://freeapp4that.store/lockdown-drills/freebsd/) | Lockdown Drills: FreeBSD baseline hardening, beginner to advanced, with a command reference (.txt). |
| [Cisco IOS Lockdown](https://freeapp4that.store/lockdown-drills/cisco-ios/) | Lockdown Drills: Cisco IOS baseline hardening, beginner to advanced, with a command reference (.txt). |
| [Windows Range](https://freeapp4that.store/lockdown-range/windows/) | Lockdown Range: a Windows 11 / Server 2025 hardening lab in the browser (real panels, cmd and PowerShell, live Progress Check), with a solution walkthrough (.txt). |
| [Linux Range](https://freeapp4that.store/lockdown-range/linux/) | Lockdown Range: Ubuntu, Linux Mint and Ubuntu Server hardening labs with a bash terminal and live Progress Check, with a solution walkthrough (.txt). |
| [Cisco Range](https://freeapp4that.store/lockdown-range/cisco-ios/) | Lockdown Range: a Packet Tracer-style topology with IOS consoles, PC prompts and a live Progress Check, with a solution walkthrough (.txt). |

Defense Ladder, Net Drills, Lockdown Drills, and Lockdown Range are unofficial, general cybersecurity study and practice, not affiliated with or endorsed by Microsoft, Canonical, Linux Mint, the FreeBSD Project, or Cisco. They teach defensive skills only. Lockdown Range machines are simulations that run entirely in the page. Net Drills pair well with Cisco networking courses such as the NetAcad Network Technician path. Try hardening commands on a practice VM, not a computer you depend on.

## Add or update tools

1. Keep source pages outside this repository, e.g. `../tool4that-src/<group>/`.
2. Describe them in a manifest in `manifests/` (slug, card text, `match` patterns, prep options).
3. Prepare and register them, then rebuild the hub:
   ```bash
   python3 add_tools.py manifests/lockdown-drills.json ../tool4that-src/lockdown-drills --dry-run
   python3 add_tools.py manifests/lockdown-drills.json ../tool4that-src/lockdown-drills
   python3 build_hub.py
   ```
   - `--dry-run`: show which file matches which tool; change nothing.
   - `add_tools.py`: cleans each page, runs `prepare_tool.py` (security policy, preview tags, hub link), copies its reference `.txt`, and updates `tools.json`.
   - One-off single tool (no manifest): `python3 prepare_tool.py SOURCE.html <slug> --name "Name" --description "..." --icon "🔢"`, then add the `tools.json` entry by hand (empty `sha256`/`updated`) and rebuild.
4. If a cybersecurity tool changed, rebuild the Concept Index, which confirms every place it lists against the tool pages:
   ```bash
   python3 build_concepts.py
   python3 add_tools.py manifests/learning.json ../tool4that-src/learning
   python3 build_hub.py
   ```
5. Publish:
   ```bash
   git add -A && git commit -m "Add <tool>" && git push
   ```

`tools.json` groups tools by `categories`, optional `series` (each with its own page), and optional `sections` (an in-page grouping inside a category, above its series, e.g. Learning and Practice). `build_hub.py` validates `tools.json`, then regenerates `index.html`, the category, series, and all-tools pages, `404.html`, `robots.txt`, and `sitemap.xml`. It computes each tool's size and SHA-256, and changes a tool's "Updated" date only when its file changes. It uses the Python standard library only. `concepts.json` holds the Concept Index data; `build_concepts.py` confirms it against the tool pages and writes the page.

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

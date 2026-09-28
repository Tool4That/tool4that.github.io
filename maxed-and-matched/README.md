# Maxed & Matched TSP Calculator

**Hit the max. Keep the match.**

One HTML file. It reads your LES and gives the exact myPay TSP percentages that reach the IRS limit in your last December paycheck without losing a dollar of BRS match. It also projects where your TSP is heading.

Everything runs in your browser; nothing is uploaded. There is no install and no Python.

Live at https://tool4that.github.io/maxed-and-matched/ as part of [Tool4That](https://tool4that.github.io/).

It is independent, and not affiliated with or endorsed by DFAS, the Federal Retirement Thrift Investment Board, or DoD.

## Run

```bash
xdg-open maxed-and-matched.html
```
- Any modern browser (Chrome, Edge, Firefox, Safari). Windows: double-click the file.
- Reading an LES **PDF** loads pdf.js 5.6.205 from cdnjs.cloudflare.com on first use. If a network blocks it, use **Paste LES text** instead. Word files, pasted text, and everything else work fully offline.

## Using it

The page is layered. Most members only need the top.

1. **Add your LES**: drop the PDF or paste its text. Once it's read, this step folds into one line showing what was read (grade, base pay, current elections, YTD Deductions), with **Load a different LES** and **Fix a number**.
2. **Enter these in myPay**:
   - A plain list of the boxes to change (e.g., *Roth TSP · Base Pay 14% → 9%*), then the full eight-box grid, when to submit, and what it achieves.
   - **How to enter this in myPay** walks through the site, including the trap: enter all eight boxes, because myPay can zero out any you skip.
   - **Rest of 2026 / All of 2027** switches years.

**Fit it to your situation.** Cards that open in place, each showing its live answer while closed:
- Pay changing?
- Money tight right now? (Set my own %, with over/under alerts and a monthly take-home figure)
- Roth or Traditional?
- Next year
- Where your TSP is heading
- Month by month
- Tips

**Advanced.** Every input:
- profile and LES numbers, including YTD Deductions, which drives the math (only YTD TSP Exempt is subtracted);
- plan rules: timing, cushion, round-up, the 5% match floor;
- myPay maximums;
- service timeline;
- retirement assumptions.

**Pay tables and TSP limits** holds the yearly update tools.

Open sections are remembered on this device. Add `?ui=all` to the file's address to open everything at once.

## New year? Check DFAS

Open **Pay tables and TSP limits** (or click **update** in the header) and click **Check DFAS now**. It reads the four DFAS basic-pay pages (Enlisted, Warrant, Officers, Officers prior enlisted) and the tsp.gov limits page. Nothing goes online until you click, and it sends no cookies, no referrer, and nothing about you.

Browsers normally refuse to let a file on your computer read another website unless that site opts in (CORS). DFAS and tsp.gov likely don't, so when the browser blocks the read, the panel switches to the copy route:

1. Click **Open** next to a table. You only need the ones marked **you** (your grade and any planned promotions).
2. On the DFAS page press `Ctrl+A`, then `Ctrl+C` (Mac: `⌘`).
3. Come back and press `Ctrl+V` anywhere on the page.

How a copied page is read:
- The table type (enlisted, warrant, officer, prior-enlisted) is recognized from the content. O-1E–O-3E are told apart from O-1–O-3 by their values, not just their labels.
- The year comes from the page title. If you copied only the table, you're asked once.
- Blank cells stay in their columns.

After each load:
- The report shows grades loaded per table, the raise versus last year, and your own new monthly rate. **Undo** reverts the last import.
- DFAS doesn't always post all four tables the same day. "DFAS still shows 2026" means check back later.
- If an address returns the wrong table, the checklist says so. Fix it under **Page addresses**.

Optional other routes, under **Other ways**:
- the DFAS Word file ("Complete AC and RC Pay Tables" on the [Pay Tables page](https://www.dfas.mil/militarymembers/payentitlements/Pay-Tables/));
- a PDF;
- a saved page;
- the paste box.

**Save pay tables to share** creates a small file. One person updates, and the rest of the unit drops that file onto the page.

Guardrails:
- Drill (per-drill) tables are rejected.
- Values that don't fit monthly basic pay are skipped.
- Files are recognized by content even if email stripped the extension.
- Until a year is loaded, it is projected from the prior year: 2027 uses 3.6% (statutory ECI) by default, and the House's tiered 7/6/5% is selectable.

## What the planner models

**Rounding up (default on).** myPay takes whole percents, so the plan rounds *up* to reach the full limit instead of rounding down and leaving room unused. DFAS takes only what fits in the last paycheck, and the excess stays in that paycheck. **Room left on Dec 31** shows it as a negative, e.g. −$87.

Guardrail: rounding up is accepted only when the limit is reached in the **last paycheck of December**, and that paycheck still carries 5% of base pay. This assumes the worst case, that DFAS takes the cut from base pay. It keeps the match whole. If a round-up can't meet that, the plan stays under the limit and says why.

Setting a **Cushion ($)** turns rounding up off.

The same rule drives the alerts:
- "If you change nothing" quantifies the match at risk when the last paycheck can't absorb the overage.
- In **Set my own %**, a last-paycheck overage counts as on target, and any unused dollar is flagged.


- 402(g) elective limit (Traditional + Roth), 414(v) catch-up incl. ages 60–63 (spillover, basic pay only, unmatched), 415(c) annual additions.
- BRS: 1% automatic after 60 days; match (100% of first 3%, 50% of next 2%) after 2 years; both end at 26 years. Legacy High-3: no agency money.
- Special/incentive/bonus contributions need a basic-pay election; contributions past a limit are rejected, forfeiting later match.
- Base pay prorated on the DFAS 30-day month: longevity steps on the PEBD anniversary, promotions on their date, E-1 under 4 months rate.
- LES pay types are classified by reconciling the TSP deduction against your rates to the cent (for example, SAVE PAY counted as special pay).

## Privacy (PII / PHI)

- **PHI: none.** It never asks for or keeps health information. Deduction lines such as TRICARE Dental are ignored.
- **PII: read, never kept or sent.**
  - An LES contains PII: name, SSN or DoD ID, sometimes account details.
  - The page reads it only inside the browser. Nothing is uploaded: tests record zero network requests while an LES is read.
  - It extracts only pay values: grade, pay date, TSP elections, YTD, and pay amounts.
  - Pasted LES text is cleared from the page the moment it's read.
  - The "What was read" view hides names, SSNs, DoD IDs, and account numbers.
  - Tests paste a full LES with a name, SSN, DoD ID, and account number, then confirm none of them remain in the page or in browser storage.
- **What's stored:**
  - **Remember on this device** (in the privacy banner) keeps those pay values, plus any birth date and retirement inputs you enter, in this browser's local storage until **Forget everything**.
  - With Remember off, only an "off" flag is stored, so the choice survives reloads and Forget.
- **Outside the page's control:**
  - the LES PDF in your Downloads folder;
  - shared computers;
  - browser extensions, which can read any page you open.

## Security

Content Security Policy:
- Inline scripts are pinned by SHA-256; there is no `'unsafe-inline'` or `'unsafe-eval'` for scripts.
- The only remote script host is `cdnjs.cloudflare.com`, for pdf.js, loaded only when a PDF is dropped.
- `connect-src https://www.dfas.mil https://www.tsp.gov` is used only by **Check DFAS now**.

Check DFAS requests are GETs with `credentials: 'omit'` and `referrerPolicy: 'no-referrer'`, a 15 s timeout, and a 5 MB cap.

Fetched and pasted HTML is parsed with `DOMParser`, which is inert: embedded scripts never run (tested). Values are validated for range, for increasing with years of service, and against last year's table.

Word files are read with a built-in ZIP reader capped at 30 MB inflated (decompression-bomb guard).

## Hosting it

**Home: GitHub Pages, as part of Tool4That.** The Tool4That repository holds this page in `maxed-and-matched/`; its README covers publishing and adding tools.

GitHub Pages can't send custom HTTP headers. What still protects the page there:
- The Content Security Policy inside the page still applies.
- The tool refuses to run inside another site's frame, which covers the missing `frame-ancestors`.
- github.io serves HTTPS only.

**Alternative: Cloudflare Pages (free).**
- Cloudflare can deploy the same GitHub repository directly.
- It honors a `_headers` file, which adds `frame-ancestors`, HSTS, and the other headers.
- Static requests are free and unlimited.

**Avoid** pay-per-GB clouds (S3/CloudFront, Azure, GCP) for a public page: bot traffic becomes a bill.

Before you share the link:
- **No analytics or tag managers.** They add third-party scripts to a page that reads LES data.
- **MFA on the hosting account.** Whoever controls it controls the code that reads members' LES.
- **Publish the SHA-256** of each release.
- **Official DoD use:** check with your PA, privacy, and cyber offices first. A personal commercial site is not an official DoD site, so use no seals or branding.

## Limits

- Monthly simulation. If a month hits the limit, the mid-month versus end-of-month split isn't modeled, so the match that month is reported as at risk.
- Not modeled: officer CZTE exclusion cap, mandatory Roth catch-up for prior-year FICA wages over $150k, REDUX multiplier (treated as High-3), reserve drill pay.
- Promotions are entered, not predicted. Date of rank isn't on the LES.
- Planning aid, not financial or tax advice.

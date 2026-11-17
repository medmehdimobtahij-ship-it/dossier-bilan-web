# Dossier Bilan

[![Tests](https://github.com/medmehdimobtahij-ship-it/dossier-bilan-web/actions/workflows/tests.yml/badge.svg)](https://github.com/medmehdimobtahij-ship-it/dossier-bilan-web/actions/workflows/tests.yml)

At the firm, every year-end closing is prepared in the same Excel workbook: 42 sheets, about 20,000 formulas, copied from one client to the next.

I didn't just move it to the web. I went through every formula the way I would review a client file, checked it against accounting and tax rules, and fixed what was wrong.
The result is a web app that does the same work, with controls you can actually trust.

![Summary of a demo file](docs/capture-synthese.png)

## The accounting behind it

**Review by cycle.** Every account of the trial balance is assigned to a cycle (cash, receivables and payables, tax, payroll, fixed assets, equity, loans…) and gets a review status and a comment, carried over to the next year.

**Controls that block the file**, shown on the summary page:
- trial balance N and N-1 balanced to the cent
- result from the SIG (French management balances) = accounting result
- last year's profit allocation fully justified, account by account (1061, 1068, 110/119, dividends…)
- revenue tied to VAT: from revenue per rate, through accruals, receivables and cash collected, to the taxable base actually declared on the CA3 returns
- equity below half of the share capital flagged

**Tax and legal**
- taxable income with add-backs and deductions (non-deductible fines and gifts, parent-subsidiary regime with its 5% share of costs…)
- tax losses carried forward, capped at €1M + 50% of the profit above (art. 209 I CGI)
- corporate tax at 15% up to €42,500, then 25%
- profit allocation at the AGM: legal reserve (5% of profit until it reaches 10% of capital), dividends per partner, social charges, 12.8% withholding, IFU boxes
- for a majority manager (TNS): the part of dividends above 10% of capital, share premium and current account is subject to social contributions, year-end provision for contributions based on the PASS

Every rule is written out in plain words in [docs/REGLES.md](docs/REGLES.md) (in French).

## What I found in the original Excel

Rebuilding it formula by formula meant I had to understand each one. Some were wrong, and a few of them in ways nobody would notice:

- **Tax losses disappeared.** Past losses weren't capped at the profit. With €10,000 of profit and €50,000 of losses, the Excel used all €50,000, and €40,000 of carryforward vanished from the following years.
- **A VAT control that could never fail.** For the 0%, intra-EU and export columns, the formula divided by the rate of the neighbouring column. The error turned into 0, so the line always said "ok", even with a real difference.
- **Joint venture results counted twice** (655 / 755 shared the same heading), which broke the SIG = accounting result control.
- **Grants (13) and regulated provisions (14) dropped out of equity** after the AGM.
- **The revenue split for the tax return read only 13 of the 26 revenue accounts.**
- **Former clients' data was still inside the template**, so every new file shipped with it.

There are 9 corrections in total, each with the faulty cell, its effect and the fix, in [docs/ECARTS_EXCEL.md](docs/ECARTS_EXCEL.md).

A few points aren't bugs but professional judgement (where do 79 "transferts de charges" go in the SIG? should the 10% dividend threshold use year N or N-1?). Those are left to the chartered accountant who signs, and the app behaves like the Excel until then.

## How I know it's right

I built a test bench that writes fictional client files into a copy of the original Excel, lets Excel recalculate, and compares every cell with my app to the cent.
Last run: **35,526 cells on 13 files, no unexpected difference.** The only gaps are the corrections above.

The original workbook belongs to the firm, so it isn't published. The bench is here to show the method.

| SIG | Equity and allocation |
|---|---|
| ![SIG](docs/capture-sig.png) | ![Equity](docs/capture-capitaux.png) |

## Try it

You need Python 3.10+. No account, no internet.

- Windows: double-click `demo.bat`
- macOS / Linux: `sh demo.sh`

Then open http://localhost:8095 (login `demo` / `demo`). The demo has three fake companies: a consulting firm, a bakery and a loss-making digital studio.

Tests: `python -m pytest tests`

Built with Python and Flask. The whole file is recalculated on every input in under 10 ms (the Excel took 2 to 5 seconds). The trial balance comes from Pennylane (read-only API) or from an Excel / CSV file.

## What's not done yet

- I followed Pennylane's public docs for the API but haven't tried it with a real token yet.
- It's built for a small team, so there are no per-file permissions.

The interface is in French, since it was made for a French firm.

MIT licence. Made by Mehdi Mobtahij.

# LTC Watch

Ontario long-term care inspection reports, in plain language. Every finding
cited to the official Ministry of Long-Term Care report.

Live: https://ltc-watch-jigar.netlify.app

## What it does

- **Crawl** (`ltc.py`): pulls every published inspection report for every
  listed home from the Ministry's public reports portal
  (publicreports.mltc.gov.on.ca) — a guest Oracle Apex API, no auth. For
  each inspection it extracts the written notifications (NCs, with the
  sections of the Fixing Long-Term Care Act, 2021 they cite), administrative
  monetary penalties (AMPs), compliance orders, inspection dates, and
  protocols used.
- **Briefs** (`briefs.py`): an LLM writes a facts-only, cited brief for
  every inspection that found violations. Clean inspections are counted,
  not briefed.
- **Render** (`render.py`): editorial static site — home rankings by
  notifications and AMPs, per-home inspection history, most-cited law
  sections, method page.
- **Refresh**: nightly Hermes cron (agent-approved runtime) runs the crawl
  incrementally (only new inspection IDs) and redeploys to Netlify.

## API contract (reverse-engineered, verified 2026-08-17)

`POST https://publicreports.mltc.gov.on.ca/webruntime/api/apex/execute?language=en-CA&asGuest=true&htmlEncode=false`

- `getHomeDetailsbyNameOrLocarion` `{homeNameOrLocation}` -> home list
- `getHomeDetails` `{accountNumber}` -> report list (Salesforce record Ids)
- `getHomeInspectionDetails` `{inspectionId, homeId, usePublish: true}` ->
  full report: written notifications, compliance orders, intake details

## Running

```sh
python3 ltc.py --city Toronto   # crawl + aggregate -> dist/data/ltc.json
python3 briefs.py               # LLM briefs for new violation findings
python3 render.py               # editorial site -> dist/
```

Cached raw responses live in `state/cache/` (gitignored); `state/seen.json`
drives the incremental crawl. The LLM key is read from
`~/dev/deepseek-harness/.env` (never committed).

## Honesty notes

- Findings are regulatory notices, not court judgments; the official portal
  is the source of truth.
- Briefs are AI-generated wire copy — check the cited inspection number
  before quoting.
- Data: Government of Ontario (King's Printer), used for public
  accountability reporting.

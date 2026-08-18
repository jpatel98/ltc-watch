#!/usr/bin/env python3
"""LTC Watch render: editorial static site from dist/data/ltc.json +
briefs.json. Reuses the Council Beat editorial style. Run: python3 render.py
"""
import html, json, os, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, "dist")
DATA = os.path.join(DIST, "data")

SITE = "LTC Watch"
TAGLINE = ("Ontario long-term care inspections, in plain language. "
           "Every finding cited to the official Ministry of Long-Term Care report.")
FOOTER_NOTE = ""

def esc(s):
    return html.escape(str(s), quote=True)

def fmt_date(iso):
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        return iso or "unknown"

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")

def layout(title, body, active=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — {SITE}</title>
<link rel="stylesheet" href="/style.css">
<meta name="description" content="{esc(TAGLINE)}">
</head>
<body>
<header class="masthead">
  <div class="wrap">
    <p class="kicker">Ontario long-term care &middot; Inspection watch &middot; {datetime.now().strftime('%B %Y')}</p>
    <h1 class="name"><a href="/">{SITE}</a></h1>
    <nav>
      <a href="/" class="{('on' if active=='home' else '')}">Rankings</a>
      <a href="/about.html" class="{('on' if active=='about' else '')}">Method &amp; sources</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="footer">
  <div class="wrap">
    <p><strong>{SITE}</strong> &mdash; {esc(TAGLINE)}</p>
    <p>Data is crawled nightly from the official Ministry of Long-Term Care
    inspection reports portal (publicreports.mltc.gov.on.ca). Briefs are
    written by an AI model with facts-only instructions; every brief cites
    its official inspection number. Source: Government of Ontario.</p>
    {('<p class="meta">Data as of: ' + FOOTER_NOTE + '</p>') if FOOTER_NOTE else ''}
  </div>
</footer>
</body>
</html>"""

def brief_article(b):
    kicker = f'{esc(b.get("city") or "")} &middot; {fmt_date(b.get("date"))} &middot; {esc(b.get("inspection_type") or "Inspection")}'
    chips = ""
    if b.get("n_amp"):
        chips += f'<span class="chip amp">AMP fine issued</span>'
    if b.get("sections"):
        chips += ' ' + " ".join(f'<span class="chip">{esc(s)}</span>' for s in b["sections"][:4])
    return f"""<article class="brief">
  <p class="kicker">{kicker} &middot; {esc(b.get("inspection_number") or "")}</p>
  <h3>{esc(b.get("home_name") or "")}</h3>
  <p class="body">{esc(b.get("body") or "")}</p>
  <p class="src">{chips}</p>
</article>"""

def render_index(bundle, briefs):
    homes = bundle["homes"]
    body = []
    flagged = [h for h in homes if h["notifications"] > 0]
    body.append(f'<p class="kicker">Toronto long-term care homes &middot; {len(homes)} homes, {sum(h["reports"] for h in homes)} inspections on file</p>')
    body.append("<h2>Which homes have the most inspection findings?</h2>")
    body.append("<p>Ranked by written notifications issued (violations of the Fixing Long-Term Care Act, 2021) and administrative monetary penalties. Clean reports — inspections with no findings — are counted but not flagged.</p>")

    rows = []
    for i, h in enumerate(homes, 1):
        flag = "amp" if h["amps"] else ("warn" if h["notifications"] else "")
        rows.append(
            f'<tr class="{flag}"><td class="rank">{i}</td>'
            f'<td><a href="/homes/{slug(h["id"])}.html">{esc(h["name"])}</a></td>'
            f'<td class="num">{h["notifications"]}</td>'
            f'<td class="num">{h["amps"]}</td>'
            f'<td class="num">{h["reports"]}</td>'
            f'<td class="num muted">{fmt_date(h["last_report"])}</td></tr>')
    body.append(f"""<table class="attend">
<thead><tr><th></th><th>Home</th><th class="num">Notifications</th><th class="num">AMPs</th><th class="num">Inspections</th><th class="num">Last report</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>""")

    body.append('<p class="meta">Legend: <span class="dot amp"></span> AMP fine issued &middot; <span class="dot warn"></span> findings but no AMP</p>')

    if briefs:
        body.append('<h4 class="rulehead">Latest findings</h4>')
        for b in sorted(briefs, key=lambda x: x.get("date") or "", reverse=True)[:12]:
            body.append(brief_article(b))

    body.append('<h4 class="rulehead">Most-cited sections of the Fixing Long-Term Care Act, 2021</h4>')
    body.append("<ul class=\"meetlist\">")
    # s.154(1) is the enforcement boilerplate on every notification; skip it
    cited = [x for x in bundle["sections"] if x[0] != "154 (1)"]
    for s, n in cited[:12]:
        body.append(f'<li>s. {esc(s)} &mdash; cited {n} times</li>')
    body.append("</ul>")
    return layout("Rankings — " + SITE, "\n".join(body), "home")

def render_home(h, briefs):
    by_home = [b for b in briefs if b["home_id"] == h["id"]]
    rows = []
    for r in sorted(h["latest"], key=lambda x: x["date_issued"] or "", reverse=True):
        chip = ""
        if r["n_notifications"]:
            chip = f'<span class="chip warn">NC {r["n_notifications"]}</span>'
        if r["n_amp"]:
            chip += ' <span class="chip amp">AMP</span>'
        rows.append(f'<tr><td>{fmt_date(r["date_issued"])}</td><td>{esc(r["inspection_type"])}</td><td class="num">{chip or "clean"}</td></tr>')
    body = [
        f'<p class="kicker">{esc(h.get("city") or "")} &middot; LTC home</p>',
        f'<h2>{esc(h["name"])}</h2>',
        f'<p class="meta">{h["reports"]} inspections on file &middot; {h["notifications"]} written notifications &middot; {h["amps"]} AMPs &middot; last report {fmt_date(h["last_report"])}</p>',
        '<h4 class="rulehead">Inspection history</h4>',
        '<table class="attend"><thead><tr><th>Report date</th><th>Type</th><th>Findings</th></tr></thead>',
        f'<tbody>{"".join(rows)}</tbody></table>',
        f'<p class="back"><a href="/">&larr; Back to rankings</a></p>',
    ]
    if by_home:
        body.insert(4, '<h4 class="rulehead">Findings in plain language</h4>')
        for b in sorted(by_home, key=lambda x: x.get("date") or "", reverse=True):
            body.insert(5, brief_article(b))
    return layout(f"{h['name']} — {SITE}", "\n".join(body), "home")

def render_about():
    body = [
        "<h2>Method &amp; sources</h2>",
        "<p>LTC Watch crawls the official <a href=\"https://publicreports.mltc.gov.on.ca/\">Ministry of Long-Term Care inspection reports portal</a> nightly, pulls every published inspection report for every listed home, and extracts the written notifications (NCs), administrative monetary penalties (AMPs), and compliance orders from the official report text. An AI model then writes a plain-language brief for each inspection that found violations, with facts-only instructions.</p>",
        "<h3>What the columns mean</h3>",
        "<ul>",
        "<li><strong>Notifications</strong> — Written Notifications issued to the licensee for non-compliance (FLTCA, 2021, s. 154).</li>",
        "<li><strong>AMPs</strong> — Administrative Monetary Penalties issued alongside a notification.</li>",
        "<li><strong>Inspections</strong> — published inspection reports, including clean ones.</li>",
        "</ul>",
        "<h3>Limits (read before quoting)</h3>",
        "<ul>",
        "<li>This is a crawling/aggregation of official reports; the official portal is the source of truth. A finding is a regulatory notice, not a court judgment.</li>",
        "<li>Reports are published with a lag after the inspection date; the site shows what the ministry has published.</li>",
        "<li>Briefs are AI-generated wire copy: check the cited inspection number before quoting.</li>",
        "</ul>",
        "<p class=\"meta\">Data: Government of Ontario (King's Printer), used for public accountability reporting.</p>",
    ]
    return layout("Method — " + SITE, "\n".join(body), "about")

def main():
    global FOOTER_NOTE
    with open(os.path.join(DATA, "ltc.json")) as f:
        bundle = json.load(f)
    bp = os.path.join(DATA, "briefs.json")
    briefs = json.load(open(bp)) if os.path.exists(bp) else []
    FOOTER_NOTE = f"reports as of {bundle['generated_at'][:10]} (crawled nightly)"

    pages = {"index.html": render_index(bundle, briefs), "about.html": render_about()}
    for h in bundle["homes"]:
        pages[f"homes/{slug(h['id'])}.html"] = render_home(h, briefs)
    for rel, content in pages.items():
        p = os.path.join(DIST, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content)
    print(f"rendered {len(pages)} pages")

if __name__ == "__main__":
    main()

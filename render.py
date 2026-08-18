#!/usr/bin/env python3
"""LTC Watch render — "The Report Cards": dark editorial accountability board.

Unofficial letter grades computed from official findings:
  rate = (written notifications + 0.5 x AMPs) / inspections on file
  A: 0   B: <1.0   C: 1.0-2.4   D: 2.5-4.9   F: >=5.0
Run: python3 render.py
"""
import html, json, os, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, "dist")
DATA = os.path.join(DIST, "data")

SITE = "LTC WATCH"
TAGLINE = ("Ontario long-term care inspection report cards. Unofficial grades, "
           "official findings, cited to the Ministry of Long-Term Care.")

GRADE_RULES = "rate = (written notifications + 0.5 x AMPs) / inspections on file. A: 0, B: <1.0, C: 1.0-2.4, D: 2.5-4.9, F: 5.0+"

def esc(s):
    return html.escape(str(s), quote=True)

def fmt_date(iso):
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %-d, %Y")
    except Exception:
        return iso or "?"

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")

def grade(rate):
    if rate <= 0: return "A"
    if rate < 1.0: return "B"
    if rate < 2.5: return "C"
    if rate < 5.0: return "D"
    return "F"

def rate_of(h):
    return (h["notifications"] + 0.5 * h["amps"]) / max(h["reports"], 1)

def grade_chip(g, big=False):
    cls = f"grade {g}" + (" big" if big else "")
    return f'<span class="{cls}" title="Unofficial letter grade">{g}</span>'

def layout(title, body, active=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — {SITE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
<meta name="description" content="{esc(TAGLINE)}">
</head>
<body>
<header class="masthead">
  <div class="wrap">
    <p class="kicker mono">Ontario long-term care &middot; inspection report cards &middot; {datetime.now().strftime('%b %Y')}</p>
    <h1 class="name"><a href="/">{SITE}</a></h1>
    <nav>
      <a href="/" class="{('on' if active=='home' else '')}">The Board</a>
      <a href="/about.html" class="{('on' if active=='about' else '')}">Method</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="footer">
  <div class="wrap">
    <p><strong>{SITE}</strong> &mdash; {esc(TAGLINE)}</p>
    <p class="mono dim">Grades are unofficial, computed from official inspection
    findings crawled nightly from publicreports.mltc.gov.on.ca.
    {esc(GRADE_RULES)}. Briefs are AI-written, facts-only, cited to their
    inspection number. A finding is a regulatory notice, not a judgment.</p>
    <p class="mono dim">Data as of {esc(FOOTER_NOTE)}</p>
  </div>
</footer>
<script src="/ui.js"></script>
</body>
</html>"""

FOOTER_NOTE = ""

def brief_card(b):
    sev = "amp" if b.get("n_amp") else ("warn" if b.get("n_notifications") else "ok")
    chips = f'<span class="tag {sev}">{b["n_notifications"]} NC</span>'
    if b.get("n_amp"):
        chips += f'<span class="tag amp">AMP</span>'
    return f"""<article class="card brief" data-sev="{sev}">
  <p class="mono dim small">{esc(b.get("city") or "")} &middot; {fmt_date(b.get("date"))} &middot; {esc(b.get("inspection_number") or "")}</p>
  <h3>{esc(b.get("home_name") or "")}</h3>
  <p class="body">{esc(b.get("body") or "")}</p>
  <p class="tags">{chips}</p>
</article>"""

def render_index(bundle, briefs):
    homes = bundle["homes"]
    graded = [(h, rate_of(h), grade(rate_of(h))) for h in homes]
    worst = max(graded, key=lambda x: x[1])

    # section bars (skip 154(1) boilerplate)
    cited = [(s, n) for s, n in bundle["sections"] if s != "154 (1)"][:10]
    maxn = cited[0][1] if cited else 1

    rows = []
    for i, (h, rate, g) in enumerate(sorted(graded, key=lambda x: -x[1]), 1):
        pct = min(100, round(100 * rate / worst[1]))
        amp = '<span class="amp-mark">AMP</span>' if h["amps"] else ""
        rows.append(f"""<tr class="row {g}">
  <td class="rank mono">{i}</td>
  <td class="gcell">{grade_chip(g)}</td>
  <td class="home"><a href="/homes/{slug(h['id'])}.html">{esc(h['name'])}</a></td>
  <td class="num mono">{h["notifications"]}</td>
  <td class="num mono">{h["amps"]} {amp}</td>
  <td class="num mono dim">{h["reports"]}</td>
  <td class="bar"><span class="rate" style="width:{pct}%"></span></td>
</tr>""")

    spot_brief = next((b for b in briefs if b["home_id"] == worst[0]["id"]), None)
    spot = f"""<section class="spotlight">
  <div class="spot-head">
    {grade_chip(worst[2], big=True)}
    <div>
      <p class="mono dim small">Bottom of the class &middot; Toronto</p>
      <h2><a href="/homes/{slug(worst[0]['id'])}.html">{esc(worst[0]['name'])}</a></h2>
      <p class="mono dim">{worst[0]['notifications']} notifications &middot; {worst[0]['amps']} AMPs &middot; {worst[0]['reports']} inspections &middot; {worst[1]:.2f} findings per inspection</p>
    </div>
  </div>
  {f'<p class="body">{esc(spot_brief["body"])}</p>' if spot_brief else ''}
</section>"""

    latest = sorted(briefs, key=lambda x: x.get("date") or "", reverse=True)[:12]
    cards = "".join(brief_card(b) for b in latest)

    body = [
        '<section class="hero">',
        '<p class="mono dim small">Toronto &middot; 35 homes &middot; 542 inspections &middot; findings in all of them</p>',
        '<h2>Nobody gets an A.</h2>',
        '<p>The ministry has published <strong class="mono">542 inspection reports</strong> for Toronto&rsquo;s '
        f'<strong class="mono">35</strong> long-term care homes. {sum(1 for h in homes if h["notifications"]>0)} of them '
        f'contain written notifications of non-compliance. Grades below are computed from the official record '
        f'&mdash; the formula is on the <a href="/about.html">method page</a>.</p>',
        '<div class="legend mono dim small"><span class="tag A">A</span> clean <span class="tag B">B</span> &lt;1.0 '
        '<span class="tag C">C</span> 1.0&ndash;2.4 <span class="tag D">D</span> 2.5&ndash;4.9 '
        '<span class="tag F">F</span> 5.0+ findings per inspection</div>',
        "</section>",
        spot,
        '<section class="board">',
        '<div class="board-head"><h4>The board</h4><input id="filter" type="search" placeholder="Filter homes…" aria-label="Filter homes"></div>',
        f'<table id="board"><thead><tr><th></th><th></th><th>Home</th><th class="num">NCs</th><th class="num">AMPs</th><th class="num">Insp.</th><th>Rate</th></tr></thead><tbody>{"".join(rows)}</tbody></table>',
        "</section>",
        '<section class="sections"><h4>Most-cited sections of the Fixing Long-Term Care Act, 2021</h4>',
        '<div class="bars">' + "".join(
            f'<div class="barline"><span class="mono small">s. {esc(s)}</span><div class="bar"><span class="fill" style="width:{max(4, round(100*n/maxn))}%"></span></div><span class="mono dim small">{n}</span></div>'
            for s, n in cited) + "</div></section>",
        '<section class="briefs"><h4>Latest findings</h4><div class="grid">' + cards + "</div></section>",
    ]
    return layout("The Board — " + SITE, "\n".join(body), "home")

def render_home(h, briefs):
    rate = rate_of(h)
    g = grade(rate)
    by_home = [b for b in briefs if b["home_id"] == h["id"]]
    tiles = f"""<div class="tiles">
      <div class="tile {g}"><span class="mono dim small">Notifications</span><span class="big mono" data-count="{h['notifications']}">0</span></div>
      <div class="tile {g}"><span class="mono dim small">AMPs</span><span class="big mono" data-count="{h['amps']}">0</span></div>
      <div class="tile {g}"><span class="mono dim small">Inspections</span><span class="big mono" data-count="{h['reports']}">0</span></div>
      <div class="tile rate-tile {g}"><span class="mono dim small">Findings / inspection</span><span class="big mono">{rate:.2f}</span></div>
    </div>"""
    timeline = []
    for r in sorted(h["latest"], key=lambda x: x["date_issued"] or "", reverse=True):
        sev = "amp" if r["n_amp"] else ("warn" if r["n_notifications"] else "ok")
        label = f'{r["n_notifications"]} NC' if r["n_notifications"] else "clean"
        if r["n_amp"]:
            label += " + AMP"
        timeline.append(f'<li class="{sev}"><span class="dot"></span><span class="mono small date">{fmt_date(r["date_issued"])}</span><span class="type">{esc(r["inspection_type"])}</span><span class="tag {sev}">{label}</span></li>')
    briefs_html = "".join(brief_card(b) for b in sorted(by_home, key=lambda x: x.get("date") or "", reverse=True))
    body = [
        f'<p class="mono dim small">{esc(h.get("city") or "")} &middot; report card</p>',
        f'<div class="cardhead">{grade_chip(g, big=True)}<h2>{esc(h["name"])}</h2></div>',
        tiles,
        f'<p class="mono dim small">Last published report: {fmt_date(h["last_report"])} &middot; grade formula: {esc(GRADE_RULES)}</p>',
        '<section class="timeline"><h4>Inspection history</h4><ul>' + "".join(timeline) + "</ul></section>",
        f'<section class="briefs"><h4>Findings in plain language</h4><div class="grid">{briefs_html or "<p class=dim>No briefs yet for this home.</p>"}</div></section>',
        '<p class="back mono dim small"><a href="/">&larr; Back to the board</a></p>',
    ]
    return layout(f"{h['name']} — {SITE}", "\n".join(body), "home")

def render_about():
    body = [
        "<h2>Method</h2>",
        "<p>LTC WATCH crawls the official <a href=\"https://publicreports.mltc.gov.on.ca/\">Ministry of Long-Term Care inspection reports portal</a> nightly, pulls every published inspection report, and extracts the written notifications (NCs), administrative monetary penalties (AMPs), and compliance orders from the official report text.</p>",
        "<h4>Unofficial letter grades</h4>",
        f"<p class=\"mono dim\">{esc(GRADE_RULES)}</p>",
        "<ul class=\"dim\"><li>Rate = (written notifications + 0.5 x AMPs) &divide; inspections on file.</li>",
        "<li>A home with zero findings earns an A. No Toronto home currently does.</li>",
        "<li>Grades are a transparency device, not a ministry rating. They weigh findings, not care quality directly.</li></ul>",
        "<h4>What the numbers mean</h4>",
        "<ul><li><strong>NC</strong> &mdash; written notification issued to the licensee for non-compliance (FLTCA, 2021, s. 154).</li>",
        "<li><strong>AMP</strong> &mdash; administrative monetary penalty issued alongside a notification.</li>",
        "<li><strong>Inspections</strong> &mdash; published reports, including clean ones.</li></ul>",
        "<h4>Limits (read before quoting)</h4>",
        "<ul class=\"dim\"><li>This is an aggregation of official reports; the ministry portal is the source of truth.</li>",
        "<li>Reports publish with a lag after inspection; the site shows what the ministry has published.</li>",
        "<li>Briefs are AI-generated wire copy: check the cited inspection number before quoting.</li></ul>",
        "<p class=\"mono dim small\">Data: Government of Ontario (King's Printer), used for public accountability reporting.</p>",
    ]
    return layout("Method — " + SITE, "\n".join(body), "about")

def main():
    global FOOTER_NOTE
    with open(os.path.join(DATA, "ltc.json")) as f:
        bundle = json.load(f)
    bp = os.path.join(DATA, "briefs.json")
    briefs = json.load(open(bp)) if os.path.exists(bp) else []
    FOOTER_NOTE = f"{bundle['generated_at'][:10]} (crawled nightly)"

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

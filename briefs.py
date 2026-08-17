#!/usr/bin/env python3
"""LTC Watch briefs: LLM-written, facts-only summaries of inspections that
found violations. Only NEW inspections get briefs (state/seen_briefs.json).
Key read server-side from ~/dev/deepseek-harness/.env. Run: python3 briefs.py
"""
import json, os, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DIST_DATA = os.path.join(BASE, "dist", "data")
STATE = os.path.join(BASE, "state")


def load_env_key():
    env = os.path.join(os.path.expanduser("~"), "dev", "deepseek-harness", ".env")
    with open(env) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DEEPSEEK_API_KEY not found")


def chat(prompt, key, max_tokens=300, temperature=0.3, retries=3):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature, "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


SYSTEM = ("You are a sharp, plain-spoken long-term care reporter for a "
          "Toronto news wire. Write like a professional beat reporter: "
          "facts only, exact dates and section numbers, no speculation, no "
          "opinion, no filler, no bullet points, no markdown, no headlines. "
          "Two or three sentences. Name the home, the inspection date, what "
          "was found, and the law section cited. Never invent names, "
          "numbers, or claims. Use absolute dates, never relative day names.")


def prompt(r):
    notif = "; ".join(
        f"{n['num']} ({', '.join(n['sections'])}, AMP: {n['amp']})" for n in r["notifications"])
    return f"""Write a 2-3 sentence hard-news brief about this Ontario long-term care inspection finding.

Home: {r['home_name']}
City: {r.get('home_city')}
Inspection type: {r['inspection_type']}
Report issued: {r['date_issued']}
Written notifications: {notif}
Intake details: {r['intake'][:300]}
Non-complied orders: {r['not_complied'][:300]}
Official inspection number to cite: {r['inspection_number']}"""


def main():
    key = load_env_key()
    with open(os.path.join(DIST_DATA, "ltc.json")) as f:
        bundle = json.load(f)
    state_path = os.path.join(STATE, "seen_briefs.json")
    seen = set()
    if os.path.exists(state_path):
        with open(state_path) as f:
            seen = set(json.load(f))

    existing = []
    bp = os.path.join(DIST_DATA, "briefs.json")
    if os.path.exists(bp):
        with open(bp) as f:
            existing = json.load(f)
    existing_by_id = {b["inspection_id"] for b in existing}

    new_briefs = []
    for r in bundle["reports"]:
        if r["inspection_id"] in seen or r["inspection_id"] in existing_by_id:
            continue
        if r["n_notifications"] == 0:
            continue
        try:
            body = chat(prompt(r), key)
        except Exception as e:
            print(f"brief failed {r['inspection_id']}: {e}")
            continue
        new_briefs.append({
            "inspection_id": r["inspection_id"],
            "home_name": r["home_name"], "home_id": r["home_id"],
            "city": r.get("home_city"), "date": r["date_issued"],
            "inspection_number": r["inspection_number"],
            "inspection_type": r["inspection_type"],
            "n_notifications": r["n_notifications"], "n_amp": r["n_amp"],
            "sections": sorted({s for n in r["notifications"] for s in (n.get("sections") or [])}),
            "body": body,
            "sources": [{"label": f"Report {r['inspection_number']}",
                         "url": "https://publicreports.mltc.gov.on.ca/"}],
        })
        print(f"  brief: {r['home_name']} {r['date_issued']} — {body[:70]}…")
        time.sleep(0.2)

    all_briefs = new_briefs + existing
    with open(bp, "w") as f:
        json.dump(all_briefs, f, indent=1, ensure_ascii=False)
    seen |= {b["inspection_id"] for b in new_briefs}
    with open(state_path, "w") as f:
        json.dump(sorted(seen), f)
    print(f"briefs total: {len(all_briefs)} (new: {len(new_briefs)})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""LTC Watch: crawl Ontario long-term care home inspection reports.

Source: Ministry of Long-Term Care public reports portal
(publicreports.mltc.gov.on.ca, Oracle Apex guest API). All endpoints are
public, JSON, and curl-able.

API contract (verified 2026-08-17):
  POST /webruntime/api/apex/execute?language=en-CA&asGuest=true&htmlEncode=false
  - getHomeDetailsbyNameOrLocarion {"homeNameOrLocation": "Toronto"} -> homes
  - getHomeDetails              {"accountNumber": "2201"} -> report list
  - getHomeInspectionDetails    {"inspectionId": "<Id>", "homeId": "2201",
                                 "usePublish": true} -> full report HTML fields

Output: dist/data/ltc.json (aggregates only) + state/ cache + seen ids.
Run: python3 ltc.py [--city Toronto] [--all]
"""
import argparse, html, json, os, re, time, urllib.request
from collections import Counter, defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIST_DATA = os.path.join(BASE, "dist", "data")
STATE = os.path.join(BASE, "state")
CACHE = os.path.join(STATE, "cache")
os.makedirs(DIST_DATA, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

API = ("https://publicreports.mltc.gov.on.ca/webruntime/api/apex/execute"
       "?language=en-CA&asGuest=true&htmlEncode=false")
UA = {"User-Agent": "Mozilla/5.0 (ltc-watch pipeline; contact hello@axiontechnologies.ca)",
      "Content-Type": "application/json"}
SLEEP = 0.25


def apex(method, params=None, retries=3):
    body = json.dumps({"namespace": "", "classname": "@udd/01pOH000000GbLN",
                       "method": method, "isContinuation": False,
                       "params": params or {}, "cacheable": False}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, data=body, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r).get("returnValue")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ERROR {method}: {e}")
                return None
            time.sleep(2 * (attempt + 1))


def cache_path(name):
    return os.path.join(CACHE, re.sub(r"[^a-zA-Z0-9]", "_", name) + ".json")


def cached(name, fetcher):
    p = cache_path(name)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    data = fetcher()
    if data is not None:
        with open(p, "w") as f:
            json.dump(data, f)
    return data


def homes(city):
    res = cached("homes_" + (city or "ALL"), lambda: apex("getHomeDetailsbyNameOrLocarion",
                                                          {"homeNameOrLocation": city or ""}))
    if not isinstance(res, list):
        print(f"search returned {res!r}")
        return []
    seen = set()
    out = []
    for h in res:
        if h.get("Home_Number__c") in seen:
            continue
        seen.add(h.get("Home_Number__c"))
        out.append({"id": h.get("Home_Number__c"), "name": h.get("Home_Name__c")})
    return out


def strip_html(s):
    if not s:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", s)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"[ \t]+", " ", t).strip()


def parse_notifications(wn_html):
    """Extract written notifications (NC #N) + sections + AMPs from HTML."""
    txt = strip_html(wn_html)
    out = []
    parts = re.split(r"NC\s*#\s*(\d+)", txt)
    # parts[0] is preamble; then pairs of (num, body)
    for i in range(1, len(parts), 2):
        num = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        sections = re.findall(r"FLTCA,\s*2021,\s*s\.\s*([0-9]+(?:\s*\([0-9]+\))?)", body)
        amp = bool(re.search(r"AMP\s*#\s*\d+|Administrative Monetary Penalty", body))
        out.append({
            "num": f"NC #{num}",
            "sections": [s.strip() for s in sections][:6],
            "amp": amp,
            "summary": re.sub(r"\s+", " ", body)[:600],
        })
    return out


def parse_report(details):
    idet = details.get("inspectionDetails") or {}
    wn = parse_notifications(idet.get("WN_Details__c"))
    not_complied = strip_html(idet.get("Not_Complied__c"))
    complied = strip_html(idet.get("Complied__c"))
    return {
        "inspection_id": idet.get("Id"),
        "inspection_number": idet.get("Inspection_Number__c"),
        "inspection_type": (idet.get("Inspection_Type__c") or "").strip(),
        "date_issued": idet.get("Date_LR_Issued__c"),
        "licensee": idet.get("Licensee__c"),
        "intake_type": (idet.get("Intake_Type__c") or "").strip(),
        "protocols": [p.strip() for p in strip_html(idet.get("Inspection_Protocols__c")).splitlines() if p.strip()],
        "intake": strip_html(idet.get("Intake_Details__c"))[:500],
        "notifications": wn,
        "n_notifications": len(wn),
        "n_amp": sum(1 for n in wn if n["amp"]),
        "not_complied": not_complied[:300],
        "n_not_complied_orders": len(re.findall(r"Order\s*#\d+", not_complied)),
        "complied": complied[:300],
        "n_complied_orders": len(re.findall(r"Order\s*#\d+", complied)),
        "review_appeal": strip_html(idet.get("ReviewAppealInformation__c"))[:200],
    }


def crawl(home_id, home_name, force=False):
    details = apex("getHomeDetails", {"accountNumber": home_id})
    if not details:
        return []
    report_list = details.get("reportList")
    reports = json.loads(report_list) if isinstance(report_list, str) else (report_list or [])
    out = []
    for rep in reports:
        rid = rep.get("Id")
        if not rid:
            continue
        parsed = cached(f"inspection_{rid}", lambda rid=rid, hid=home_id: apex(
            "getHomeInspectionDetails", {"inspectionId": rid, "homeId": hid, "usePublish": True}))
        if not parsed:
            continue
        r = parse_report(parsed)
        r["home_id"] = home_id
        r["home_name"] = home_name
        r["home_city"] = rep.get("Home_City__c")
        r["report_type"] = rep.get("Report_Type__c")
        r["date_amended"] = rep.get("Date_Amended_LR_Issued__c")
        out.append(r)
        time.sleep(SLEEP)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="Toronto")
    ap.add_argument("--all", action="store_true", help="search all homes (empty query)")
    args = ap.parse_args()

    hs = homes(None if args.all else args.city)
    print(f"homes: {len(hs)}")

    state_path = os.path.join(STATE, "seen.json")
    seen = set()
    if os.path.exists(state_path):
        with open(state_path) as f:
            seen = set(json.load(f))

    all_reports = []
    new_ids = []
    for i, h in enumerate(hs, 1):
        if not h["id"]:
            continue
        reps = crawl(h["id"], h["name"])
        fresh = [r for r in reps if r["inspection_id"] not in seen]
        new_ids += [r["inspection_id"] for r in fresh]
        all_reports += reps
        print(f"  [{i}/{len(hs)}] {h['name']}: {len(reps)} reports ({len(fresh)} new)")
        time.sleep(SLEEP)

    seen |= set(new_ids)
    with open(state_path, "w") as f:
        json.dump(sorted(seen), f)

    # aggregates
    by_home = defaultdict(list)
    for r in all_reports:
        by_home[r["home_id"]].append(r)
    section_count = Counter()
    for r in all_reports:
        for n in r["notifications"]:
            for s in n["sections"]:
                section_count[s] += 1

    homes_out = []
    for hid, reps in by_home.items():
        with_v = [r for r in reps if r["n_notifications"] > 0]
        homes_out.append({
            "id": hid, "name": reps[0]["home_name"], "city": reps[0].get("home_city"),
            "reports": len(reps),
            "reports_with_violations": len(with_v),
            "notifications": sum(r["n_notifications"] for r in reps),
            "amps": sum(r["n_amp"] for r in reps),
            "last_report": max((r["date_issued"] or "" for r in reps), default=None),
            "latest": sorted(reps, key=lambda r: r["date_issued"] or "", reverse=True)[:8],
        })
    homes_out.sort(key=lambda h: (h["notifications"], h["amps"]), reverse=True)

    bundle = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "Ministry of Long-Term Care public inspection reports (publicreports.mltc.gov.on.ca)",
        "homes": homes_out,
        "reports": all_reports,
        "sections": section_count.most_common(30),
    }
    with open(os.path.join(DIST_DATA, "ltc.json"), "w") as f:
        json.dump(bundle, f, indent=1)
    print(f"\ntotal reports: {len(all_reports)}, new: {len(new_ids)}")
    print(f"homes with violations: {sum(1 for h in homes_out if h['notifications'] > 0)}")
    print("top sections:", section_count.most_common(5))


if __name__ == "__main__":
    main()

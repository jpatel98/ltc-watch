import json
b = json.load(open('/home/jigar/dev/ltc-watch/dist/data/ltc.json'))
homes = b['homes']
rows = []
for h in homes:
    rate = h['notifications'] / max(h['reports'], 1) + 0.5 * h['amps'] / max(h['reports'], 1)
    rows.append((h['name'], round(rate, 2), h['notifications'], h['amps'], h['reports']))
rows.sort(key=lambda r: -r[1])
for r in rows:
    print(f"{r[0][:38]:40s} rate={r[1]:6.2f}  NC={r[2]:4d} AMP={r[3]} reps={r[4]}")

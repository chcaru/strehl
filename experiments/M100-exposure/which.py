"""Which stack is binding which bar? Reads sweep.json."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "sweep.json")))
names = sorted(d)

for p, t in [(99.5, 0.85), (99.9, 0.90), (99.9, 0.95), (99.95, 0.90),
             (99.95, 0.95), (99.95, 1.00), (99.99, 1.00)]:
    print("=== p%.2f target %.2f ===" % (p, t))
    print("  %-30s %+7s %10s %10s %8s %8s"
          % ("stack", "stops", "any-clip%", "all-clip%", "p99.9", "bt709"))
    for n in names:
        r = [x for x in d[n] if x["p"] == p and x["target"] == t]
        if not r:
            continue
        r = r[0]
        flag = ""
        if r["any_clip"] > 0.005:
            flag += " ANY"
        if r["all_clip"] > 0.002:
            flag += " ALL"
        if r["mean_p999"] < 0.90:
            flag += " DARK"
        print("  %-30s %+7.2f %10.4f %10.4f %8.4f %8.4f%s"
              % (n, r["stops"], 100 * r["any_clip"], 100 * r["all_clip"],
                 r["mean_p999"], r["bt709_p999"], flag))
    print()

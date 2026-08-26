import json
d = json.load(open(r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json", encoding="utf-8"))
u = []
for r in d["rows"]:
    e = r.get("evidence") or {}
    m, f, t = e.get("merge_edge_dnpx"), e.get("frame_edge_dnpx"), e.get("edge_ratio_min")
    if None in (m, f, t) or f == 0:
        continue
    u.append((r["subject"], m / f, t))
print("usable rows: %d\n" % len(u))
tests = {
    "round to 2 dp differs":      lambda q, t: round(q, 2) != round(t, 2),
    "round to 3 dp differs":      lambda q, t: round(q, 3) != round(t, 3),
    "round to 1 dp differs":      lambda q, t: round(q, 1) != round(t, 1),
    "absolute diff > 0.01":       lambda q, t: abs(q - t) > 0.01,
    "absolute diff > 0.05":       lambda q, t: abs(q - t) > 0.05,
    "relative error > 1%":        lambda q, t: abs(q / t - 1) > 0.01,
    "relative error > 2%":        lambda q, t: abs(q / t - 1) > 0.02,
    "relative error > 5%":        lambda q, t: abs(q / t - 1) > 0.05,
}
for name, fn in tests.items():
    n = sum(1 for _, q, t in u if fn(q, t))
    print("  %-26s -> %2d of %d %s" % (name, n, len(u), "  <== 13" if n == 13 else ""))
print("\nworst by every ranking:")
for key, lab in ((lambda x: abs(x[1]/x[2]-1), "relative error"),
                 (lambda x: abs(x[1]-x[2]), "absolute difference")):
    w = max(u, key=key)
    print("  by %-20s: %-26s %.3f vs %.3f" % (lab, w[0], w[1], w[2]))
b = next(x for x in u if x[0] == "bee-2-cpl")
rank = sorted(u, key=lambda x: -abs(x[1]/x[2]-1))
print("  bee-2-cpl rank by relative error: %d of %d"
      % ([x[0] for x in rank].index("bee-2-cpl") + 1, len(u)))

import json
d = json.load(open(r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json", encoding="utf-8"))
rows = d["rows"]
usable, missing = [], []
for r in rows:
    e = r.get("evidence") or {}
    m, f, t = e.get("merge_edge_dnpx"), e.get("frame_edge_dnpx"), e.get("edge_ratio_min")
    if m is None or f is None or t is None or f == 0:
        missing.append((r["subject"], m, f, t)); continue
    usable.append((r["subject"], m, f, t, m / f))

print("rows total %d | usable %d | missing/None %d" % (len(rows), len(usable), len(missing)))
for s, m, f, t in missing:
    print("   excluded: %-24s merge=%s frame=%s ratio=%s" % (s, m, f, t))

print("\n%-26s %10s %10s %8s %8s %8s" % ("subject","merge","frame","m/f","stated","rel.err"))
res = []
for s, m, f, t, q in sorted(usable, key=lambda x: -abs(x[4]/x[3]-1)):
    rel = abs(q / t - 1.0)
    res.append((s, q, t, rel))
    print("%-26s %10.3f %10.3f %8.3f %8.3f %7.1f%%" % (s, m, f, q, t, 100*rel))

for tol in (0.001, 0.005, 0.01, 0.02, 0.05):
    bad = [r for r in res if r[3] > tol]
    print("\ntolerance %5.1f%% -> %2d of %d rows disagree" % (100*tol, len(bad), len(res)))
w = res[0]
print("\nWORST: %s  computed m/f = %.4f  stated edge_ratio_min = %.4f  -> %.1f%% out"
      % (w[0], w[1], w[2], 100*w[3]))

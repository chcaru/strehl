"""F1/F2: check every number in the frame_edge_dnpx definition against the data
it describes -- by machine, from the shipped artifact, not by eye.

Guard: hard-error on an empty selection.  An earlier version of this probe used
the wrong nesting, selected 0 rows, and printed 'sets equal: True  OK' for two
empty sets -- a green that meant nothing.  Never let the empty case pass.
"""
import json, re
J = json.load(open(r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json", encoding="utf-8"))
rows = J["rows"]
defn = J["fields"]["frame_edge_dnpx"]

recs = []
for r in rows:
    e = r.get("evidence") or {}
    m, f, t = e.get("merge_edge_dnpx"), e.get("frame_edge_dnpx"), e.get("edge_ratio_min")
    if m is None or f is None or t is None or f == 0:
        continue
    mf = m / f
    recs.append((r["subject"], mf, t, abs(mf - t), abs(mf - t) / t * 100.0))
if len(recs) < 20:
    raise SystemExit("PROBE BROKEN: only %d usable rows -- selection predicate wrong" % len(recs))
print("usable rows: %d of %d" % (len(recs), len(rows)))

s_abs = {n for n, _, _, a, _ in recs if a > 0.01}
s_rel = {n for n, _, _, _, p in recs if p > 1.0}
if not s_abs or not s_rel:
    raise SystemExit("PROBE BROKEN: empty disagreement set")
print()
print("CLAIM 'disagrees on 13 of 25 rows'")
print("   usable == 25   : %s   %s" % (len(recs) == 25, "OK" if len(recs) == 25 else "MISMATCH"))
print("   abs>0.01 count : %d   %s" % (len(s_abs), "OK" if len(s_abs) == 13 else "MISMATCH"))
print("   rel>1%%   count : %d   %s" % (len(s_rel), "OK" if len(s_rel) == 13 else "MISMATCH"))
print("CLAIM 'both criteria select the SAME 13' (set equality, not count)")
print("   sets equal     : %s   %s" % (s_abs == s_rel, "OK" if s_abs == s_rel else "MISMATCH"))
if s_abs != s_rel:
    print("   only abs: %s" % sorted(s_abs - s_rel))
    print("   only rel: %s" % sorted(s_rel - s_abs))
for tol, want in ((0.5, 16), (2.0, 10)):
    got = sum(1 for _, _, _, _, p in recs if p > tol)
    print("CLAIM 'at %.1f%% it is %d rows' -> got %d   %s"
          % (tol, want, got, "OK" if got == want else "MISMATCH"))

print()
byrel = sorted(recs, key=lambda t: -t[4]); byabs = sorted(recs, key=lambda t: -t[3])
for label, rank in (("RELATIVE error", byrel), ("ABSOLUTE difference", byabs)):
    print("ordering by %s:" % label)
    for i, (n, mf, er, a, p) in enumerate(rank[:3], 1):
        print("   %d. %-34s m/f=%.4f true=%.4f  abs=%.4f rel=%.1f%%" % (i, n, mf, er, a, p))

print()
m = re.search(r"Worst is ([a-z0-9-]+) at ([\d.]+) vs a true ([\d.]+) \(\+(\d+)%\)", defn)
n2 = re.search(r"([a-z0-9-]+) is second at ([\d.]+) vs ([\d.]+) \(\+(\d+)%\)", defn)
if not m or not n2:
    raise SystemExit("ANCHOR DID NOT LAND -- definition wording changed")
name, smf, ser, spct = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
act = [r for r in recs if r[0] == name][0]
print("STATED worst  : %s  %.3f vs %.3f  +%d%%" % (name, smf, ser, spct))
print("   max by REL? %-5s (actual %s)   max by ABS? %-5s (actual %s)"
      % (byrel[0][0] == name, byrel[0][0], byabs[0][0] == name, byabs[0][0]))
print("   m/f  stated %.3f vs recomputed %.4f  %s" % (smf, act[1], "OK" if abs(smf-act[1])<0.001 else "MISMATCH"))
print("   true stated %.3f vs recomputed %.4f  %s" % (ser, act[2], "OK" if abs(ser-act[2])<0.001 else "MISMATCH"))
print("   pct  stated %d%% vs recomputed %.1f%%  %s" % (spct, act[4], "OK" if abs(spct-act[4])<1.0 else "MISMATCH"))
name2 = n2.group(1); a2 = [r for r in recs if r[0] == name2][0]
print("STATED second : %s  %.3f vs %.3f  +%d%%" % (name2, float(n2.group(2)), float(n2.group(3)), float(n2.group(4))))
print("   rank by REL : %d      rank by ABS : %d"
      % ([r[0] for r in byrel].index(name2)+1, [r[0] for r in byabs].index(name2)+1))
print("   m/f %.4f  true %.4f  rel %.1f%%" % (a2[1], a2[2], a2[4]))

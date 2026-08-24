"""Final aggregation -- computes the exact headline numbers quoted in the report."""
from __future__ import annotations
import json, os

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out")


def j(name):
    p = os.path.join(OUT, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


s5b, s5, s8, s7, s6 = j("s5b_election_checks.json"), j("s5_election.json"), j("s8_floor.json"), j("s7_alignment_price.json"), j("s6_spectral.json")

print("== GRID CONTROL (the headline) ==")
tot_px = tot_pairs = 0
min_exact, max_abs = 1.0, 0.0
per = {}
for roi, d in s5b.items():
    gc = d.get("grid_control", [])
    if not gc:
        print(f"  {roi:15s} grid_control EMPTY (no frame cleared the minimum-pixel threshold)")
        continue
    n = sum(r["n"] for r in gc)
    per[roi] = (len(gc), n, min(r["frac_exact"] for r in gc), max(r["max_abs"] for r in gc))
    tot_px += n
    tot_pairs += len(gc)
    min_exact = min(min_exact, per[roi][2])
    max_abs = max(max_abs, per[roi][3])
    print(f"  {roi:15s} frames={len(gc):3d}  px={n:7d}  min frac_exact={per[roi][2]:.6f}  max|diff|={per[roi][3]:.0f}")
print(f"  TOTAL           pairs={tot_pairs}  px={tot_px}  min frac_exact={min_exact:.6f}  max|diff| DN={max_abs:.0f}")

print("\n== MATCHES-SOME-FRAME, and the residual ==")
for roi, d in s5.items():
    if not isinstance(d, dict) or "frac_pixel_matches_some_frame" not in d:
        continue
    nm = s5b.get(roi, {}).get("nomatch", {})
    rg = s5b.get(roi, {}).get("roughness", {})
    print(f"  {roi:15s} matches_some={100*d['frac_pixel_matches_some_frame']:.4f}%  "
          f"distinct_elected={d['n_distinct_elected']:3d}  "
          f"nomatch median_nearest={nm.get('median_nearest_dn')} max={nm.get('max_nearest_dn')} "
          f"within2={100*nm.get('frac_within_2', 0):.2f}%")
    print(f"  {'':15s} roughness: fwhm={rg.get('fwhm')} median_dev={rg.get('median_dev')} "
          f"p90={rg.get('p90_dev')} beyond_half_fwhm={100*rg.get('frac_beyond_half_fwhm', 0):.2f}%")

print("\n== ARMS ==")
for k in ("arms", "neff", "arm_neff"):
    if k in s5:
        print(" ", k, json.dumps(s5[k])[:600])
print("  (top-level keys:", [k for k in s5 if not isinstance(s5[k], dict) or "window" not in s5[k]], ")")

print("\n== S8 FLOOR ==")
print(json.dumps(s8, indent=1)[:2500])
print("\n== S7 ==")
print(json.dumps(s7, indent=1)[:1800])
print("\n== S6 R2 / sigma_eq ==")
for k in ("R2", "primary", "sigma_eq", "M_vs_F"):
    if k in s6:
        print(" ", k, json.dumps(s6[k])[:1400])
print("  keys:", list(s6))

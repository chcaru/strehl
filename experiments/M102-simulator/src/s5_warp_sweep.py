"""M102 S5 -- sensitivity of the index round-trip to unmodelled warp.

WHY THIS EXISTS. PREREGISTRATION D2 planted an extra global scale on the
second half of the stack and required R1 to go red. It did not: at the
registered magnitude the round-trip stayed green on every bar. That is a
measurement, not something to re-tune quietly, so this sweep replaces a
failed binary control with a threshold.

The hypothesis it tests: an index map is insensitive to a geometric error
smaller than the DEPTH AUTOCORRELATION LENGTH of the scene, because moving
texture within a constant-depth region maps depth to the same depth. If that
is right, the round-trip should stay green until the displacement in the
plane region exceeds the slab width, and go red after.

Usage:
  python src/s5_warp_sweep.py
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m102lib as M       # noqa: E402
import m102scene as MS    # noqa: E402
import s2_generate as GEN  # noqa: E402
import s3_roundtrip as RT  # noqa: E402

PCTS = [4.127, 8.0, 16.0, 32.0]


def main():
    rows = []
    # Depth structure scale, for the prediction the sweep tests.
    K, w = 24, 512
    slab_cfa = w / K
    for p in PCTS:
        tag = f"warp{p:g}".replace(".", "p")
        d = os.path.join(M.WORK, tag)
        spec = MS.SimSpec(frames=32, seed=7)
        GEN.generate(d, spec, plant="warp", breathing=False, warp_pct=p)
        r = RT.score(d, tag)
        t = r["textured"]
        # Displacement at the plane's mid radius, in CFA px.
        disp = 256.0 * (p / 100.0) / (1.0 + p / 100.0)
        rows.append({"warp_pct": p, "disp_cfa_px_at_r256": disp,
                     "disp_over_slab": disp / slab_cfa,
                     "median_abs": t["median_abs"],
                     "median_signed": t["median_signed"],
                     "frac_within_2": t["frac_within_2"],
                     "p90_abs": t["p90_abs"],
                     "R1_green": r["bars"]["R1_median_abs_le_1"],
                     "R2_green": r["bars"]["R2_frac_within2_ge_0.90"],
                     "ALL_GREEN": r["bars"]["ALL_GREEN"]})
        print(f"  warp {p:6.3f}%  disp {disp:6.2f} px "
              f"({disp / slab_cfa:5.2f} slabs)  median|e|={t['median_abs']:.4f}"
              f"  within2={t['frac_within_2']:.4f}"
              f"  {'GREEN' if rows[-1]['ALL_GREEN'] else 'RED'}", flush=True)
    out = {"slab_width_cfa_px": slab_cfa, "rows": rows,
           "registered_D2_pct": 4.127}
    red = [r for r in rows if not r["ALL_GREEN"]]
    out["first_red_pct"] = red[0]["warp_pct"] if red else None
    out["first_red_disp_over_slab"] = (red[0]["disp_over_slab"] if red
                                       else None)
    with open(os.path.join(M.OUT, "s5_warp_sweep.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()

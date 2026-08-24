"""M92 S5 -- arm G, non-decisional: what does the AVERAGED instrument say about
M57's strategic near-selector finding?

M57 section 9 (PR11) reports, MEASURED, that on six of eight real cells and on a
ground-truth plant the near-selector configuration (n_eff 1.4-2.4) delivers the
sharpest output, by 0.496-0.740 px against the shipped gate.  That is the same
instrument this milestone is calibrating.  If averaging over disjoint ROIs
strengthens or weakens it, that has to be said.

Arm G is NOT part of the SHIP decision.  It reads, per ROI, the equivalent-blur
difference between the shipped gate 0.50 and the near-selector gate 0.99 built
from the SAME frames, and averages it over the disjoint grid.

Sign convention, verified against M57 S7's own planted signal: `dsig(rs1, rs2)`
is POSITIVE when configuration 2 is the blurrier one.  Configuration 1 here is
gate 0.50 and configuration 2 is gate 0.99, so a NEGATIVE mean means the
near-selector is sharper -- M57's direction.

The error bar is empirical repetition across ROIs, never a jackknife: the mean's
standard error is sd(across ROIs)/sqrt(N), and a percentile bootstrap over ROIs
is reported alongside it.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as K    # noqa: E402

TAG = os.environ.get("M92_TAG", "")
ONLY = [s for s in os.environ.get("M92_STACKS", "").split(",") if s]
NBOOT = 20000


def main():
    t0 = time.time()
    meta = json.load(open(os.path.join(M92.OUT, "s1_cells.json")))
    s2 = json.load(open(os.path.join(M92.OUT, "s2_null_averaging.json")))
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log("M92 S5 -- arm G (non-decisional): shipped gate 0.50 vs near-selector")
    log("  gate 0.99, same frames, averaged over the disjoint grid.")
    log("  NEGATIVE mean = the near-selector is SHARPER (M57 section 9's sign).")
    log("  M57 PR11 measured 0.496-0.740 px sharper on 6 of 8 real cells.")
    log("=" * 78)

    out = {}
    for stack in (ONLY or list(M92.STACKS)):
        z = np.load(os.path.join(M92.CACHE, f"cells_{stack}_disjoint.npz"))
        rows = meta[stack]["disjoint"]
        g0, g1 = f"{M92.GATE_SHIPPED:.2f}", f"{M92.GATE_SELECTOR:.2f}"
        n = sum(1 for kk in z.files if kk.endswith(f"_{g0}_a"))
        log("\n" + "=" * 78)
        log(f"{stack}  ({meta[stack]['n_frames']} frames, EXIF ISO "
            f"{meta[stack]['iso']})   ({time.time()-t0:.0f}s)")
        log("=" * 78)
        log(f"  {'k':>3} {'x':>5} {'y':>5} {'hp_sd':>8} {'n_eff .50':>10}"
            f" {'n_eff .99':>10} {'dsig px':>10} {'jack se':>9}")
        vals, keep = [], []
        order = np.argsort([r["hp_sd"] for r in rows])   # rule 9: flat first
        for k in order:
            a0, b0 = z[f"{k:02d}_{g0}_a"], z[f"{k:02d}_{g0}_b"]
            a1, b1 = z[f"{k:02d}_{g1}_a"], z[f"{k:02d}_{g1}_b"]
            d = K.dsig(K.RingStats(a0, b0), K.RingStats(a1, b1))
            log(f"  {k:>3} {rows[k]['x']:>5} {rows[k]['y']:>5}"
                f" {rows[k]['hp_sd']:>8.3f} {rows[k]['n_eff']:>10.3f}"
                f" {rows[k]['n_eff_099']:>10.3f} {d['px']:>+10.5f}"
                f" {d['se_px']:>9.5f}")
            if np.isfinite(d["px"]):
                vals.append(d["px"])
                keep.append(int(k))
        v = np.array(vals)
        N = v.size
        mean = float(v.mean())
        sd = float(v.std(ddof=1))
        sem = sd / np.sqrt(N)
        rng = np.random.default_rng(95)
        bs = np.array([v[rng.integers(0, N, N)].mean() for _ in range(NBOOT)])
        lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
        nsharp = int((v < 0).sum())
        log(f"\n  finite on {N}/{n} ROIs.  mean {mean:+.5f} px   sd across ROIs"
            f" {sd:.5f}   SE(mean) {sem:.5f}")
        log(f"  bootstrap over ROIs (20000): 95% CI [{lo:+.5f}, {hi:+.5f}]"
            f"   |mean|/SE = {abs(mean)/sem:.2f}")
        log(f"  sign agreement: {nsharp}/{N} ROIs say the near-selector is "
            f"SHARPER (negative)")
        log(f"  M57 PR11's range, as a single-ROI reading: -0.496 to -0.740 px."
            f"  Per-ROI range here: {v.min():+.5f} to {v.max():+.5f} px")

        # read against this milestone's own measured nulls
        arms = s2.get(stack, {}).get("arms", {})
        iso = meta[stack]["iso"]
        log(f"  read against M92's measured nulls (nearest ladder rungs):")
        for mult in (1, 2, 3):
            key = f"A1 indep noise x{mult} (ISO {iso})"
            if key not in arms:
                continue
            lad = arms[key]["ladder"]
            n1 = lad["1"]["rms"]
            rungs = sorted(int(k) for k in lad
                           if np.isfinite(lad[k]["rms"]))
            near = min(rungs, key=lambda q: abs(q - N))
            nn = lad[str(near)]["rms"]
            log(f"    x{mult}: Null(1) {n1:.5f} px, Null({near}) {nn:.5f} px"
                f"  ->  |mean|/Null({near}) = {abs(mean)/nn:6.2f}x,"
                f"  |mean|/Null(1) = {abs(mean)/n1:5.2f}x"
                f"   [readable at N=1? {'yes' if abs(mean) > n1 else 'NO'}]")
        out[stack] = dict(n=N, keep=keep, values=[float(x) for x in v],
                          mean=mean, sd=sd, sem=sem, ci=[lo, hi],
                          n_sharper=nsharp,
                          n_eff_099=[rows[k]["n_eff_099"] for k in keep],
                          n_eff_ship=[rows[k]["n_eff"] for k in keep])

    with open(os.path.join(M92.OUT, f"s5_gate_contrast{TAG}.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    with open(os.path.join(M92.OUT, f"s5_gate_contrast{TAG}.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote out/s5_gate_contrast{TAG}.{{json,log}}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

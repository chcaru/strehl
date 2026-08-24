"""A1 -- is a CONSTANT per-channel frame offset the right model?

The orchestrator's middle option keeps the single green election but gathers red
and blue at a per-channel focus-index OFFSET. That is only correct if the axial
term is depth-independent. The concern raised with it is that M107 reports
`k_R - k_G` as a RANGE (-0.67..-1.07), not a constant.

That range is ACROSS stacks. This asks the different and more decisive question:
is it structured WITHIN a stack -- against depth, or against radius?

## The confound, registered in PRE-REGISTRATION-3 before running

`dR = k_R - k_G` and `k_G` are not independent: both contain `k_G`. Regressing
one on the other induces a SPURIOUS NEGATIVE SLOPE through shared noise alone,
with no depth-dependence needed. A regression run without a control here would
confirm depth-dependence on a stack where none existed.

So every regression is run twice: once on the real channel difference, and once
on `null = k_G1 - k_G2`, which is two greens -- same wavelength, different lattice
site -- and therefore carries that identical shared-noise structure and none of
the chromatic signal. **The null's R^2 is the floor. A1 is scored against the
null, not against zero.**

## Scoring, as registered

  R^2 < 0.10 on both regressions in all stacks  -> constant offset ADEQUATE
  R^2 >= 0.30 with consistent sign across stacks -> constant offset WRONG MODEL
  in between                                     -> INDETERMINATE, not resolved
                                                    post hoc
"""
import sys, os, json, glob
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump

CONF_Q = 0.75  # keep the most confident quartile; argmax in flat regions is noise


def ols(x, y):
    """Slope, R^2 of y ~ x."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if x.size < 32 or np.ptp(x) < 1e-9:
        return {"n": int(x.size), "slope": float("nan"), "r2": float("nan")}
    A = np.column_stack([x, np.ones_like(x)])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {"n": int(x.size), "slope": float(coef[0]),
            "r2": 1.0 - ss_res / max(ss_tot, 1e-12)}


def main():
    files = sorted(glob.glob(os.path.join(OUT, "json", "e3_*.npz")))
    print(f"{len(files)} argmax map file(s)")
    out = {"conf_quantile": CONF_Q, "stacks": {}}

    for f in files:
        tag = os.path.basename(f)[3:-4]
        z = np.load(f)
        kR, kG1, kG2, kB = z["kR"], z["kG1"], z["kG2"], z["kB"]
        conf = z["conf"]
        kG = 0.5 * (kG1 + kG2)
        dR = kR - kG
        dB = kB - kG
        null = kG1 - kG2

        # Confidence restriction, defined and enforced rather than assumed.
        # E3 stored `conf` as a boolean mask (the unimodality/confidence gate it
        # had already applied), so use it directly; fall back to a quantile if a
        # future run stores a score instead.
        if conf.dtype == bool:
            m0 = conf
            thr = None
        else:
            thr = float(np.nanquantile(conf, CONF_Q))
            m0 = conf >= thr
        m = np.isfinite(dR) & np.isfinite(null) & np.isfinite(kG) & m0

        ny, nx = kR.shape
        yy, xx = np.mgrid[0:ny, 0:nx]
        # Radius about the map centre. These maps are sub-regions, so this is
        # radius within the region, which is the quantity a radial trend would
        # show up in locally; it is NOT full-frame radius, and the report says so.
        rr = np.hypot(xx - nx / 2.0, yy - ny / 2.0)

        rec = {"shape": [int(ny), int(nx)], "n_confident": int(m.sum()),
               "median_dR": float(np.median(dR[m])),
               "median_dB": float(np.median(dB[m])),
               "median_null": float(np.median(null[m]))}

        for name, sig in (("dR", dR), ("dB", dB), ("null", null)):
            rec[f"{name}_vs_depth"] = ols(kG[m], sig[m])
            rec[f"{name}_vs_radius"] = ols(rr[m], sig[m])

        out["stacks"][tag] = rec

        print(f"\n=== {tag}  ({ny}x{nx}, {int(m.sum())} confident px) ===")
        print(f"  medians: dR={rec['median_dR']:+.4f}  dB={rec['median_dB']:+.4f}  "
              f"null={rec['median_null']:+.4f}")
        for name in ("dR", "dB", "null"):
            d = rec[f"{name}_vs_depth"]; r = rec[f"{name}_vs_radius"]
            print(f"  {name:5s} vs depth : slope={d['slope']:+.5f}  R2={d['r2']:.4f}"
                  f"   | vs radius: slope={r['slope']:+.6f}  R2={r['r2']:.4f}")

    # ---- score A1 against the null floor -------------------------------
    print("\n=== A1 scored against the G1-G2 null floor ===")
    verdicts = {}
    for axis in ("depth", "radius"):
        rs, ns = [], []
        for tag, rec in out["stacks"].items():
            rs.append(rec[f"dR_vs_{axis}"]["r2"])
            ns.append(rec[f"null_vs_{axis}"]["r2"])
        rs = np.array(rs, float); ns = np.array(ns, float)
        excess = rs - ns
        if np.all(rs < 0.10):
            v = "CONSTANT OFFSET ADEQUATE"
        elif np.all(rs >= 0.30):
            v = "CONSTANT OFFSET IS THE WRONG MODEL"
        else:
            v = "INDETERMINATE"
        verdicts[axis] = {
            "dR_r2": rs.tolist(), "null_r2": ns.tolist(),
            "excess_over_null": excess.tolist(), "verdict": v,
        }
        print(f"  vs {axis:6s}: dR R2 = {np.round(rs,4).tolist()}   "
              f"null R2 = {np.round(ns,4).tolist()}")
        print(f"              excess over null = {np.round(excess,4).tolist()}  -> {v}")
    out["a1_verdict"] = verdicts

    dump("e11_axial", out)


if __name__ == "__main__":
    main()

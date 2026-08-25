"""M126 addendum 2 -- quantisation exposure of THIS milestone's estimator.

ORCH withdrew its triage rule (absolute-vs-ratio, small-over-large) after three
independent refutations, and instructed every agent whose work rested on it to
re-derive exposure for its own estimator, either algebraically or with a
dose-response control. This script is the measured half; the algebra is in the
report.

WHAT MY ESTIMATOR ACTUALLY IS
-----------------------------
    hp   = g - box5(g)                         # SPATIAL high-pass, ONE image
    N    = log10( sd(hp) over FLAT tiles )
    D    = log10( sd(hp) over DETAIL tiles )
    Q    = D - N
    dX   = X(arm) - X(A0)

The first thing to establish is that this is NOT the construction ORCH warned
about. The differencing hazard (split-half, frame-difference, paired) books the
value-correlated half of quantisation error as signal because the SAME pixel
value in two frames rounds the SAME way, so the error cancels in the difference.

My high-pass differences a pixel against its own 5x5 neighbourhood, INSIDE one
image. Neighbouring pixels generally hold different values, so their rounding
errors do not cancel -- they add. The prediction is therefore the OPPOSITE
failure: my N should ABSORB quantisation variance, not hide it. That is
V-M113's dispersion hazard, not ORCH's differencing hazard, and it is the one
I have to bound.

PREDICTIONS -- written before running, per the M115 discipline ORCH asked us to
copy. Any that misses gets reported as a miss.

  P-A  Flat tiles in a 16-bit LINEAR render are dark, so I expect few distinct
       levels. Median distinct levels per 4096-px flat tile < 100, and I expect
       at least one subject with flat tiles under V-M113's threshold of 12.
  P-B  N rises monotonically with narrowing dose. (If it FALLS, my estimator
       hides quantisation like a differencing one and I have a real problem.)
  P-C  dQ ATTENUATES toward 0 rather than inverting, because a common variance
       floor q^2/12 enters sd_det and sd_flat alike:
           Q' = 0.5*log10( (sd_det^2 + v) / (sd_flat^2 + v) ) -> 0 as v -> inf
       Retention beta = dQ(dose)/dQ(0) should fall monotonically from 1 toward
       0 and should NOT go materially negative.
  P-D  The byte-identical placebo (G2 == A0) reads dQ EXACTLY 0.00000 at every
       dose. Two identical files quantise identically at any dose, so this is a
       null that must hold by construction. If it ever moves, the instrument is
       broken and nothing else here counts.
  P-E  Detail-tile improved_frac drifts toward 0.5 as dose rises.
  P-F  Deterministic narrowing and equal-power random dither will NOT differ by
       anything like ORCH's 16x on MY statistic, because my statistic does not
       difference across samples. I expect a ratio within about 1.5x.

P-F is the load-bearing one: it is the test that would show ORCH's warning DOES
apply to me after all.

Reads pixels with tifffile only, asserts uint16. Never writes to D:\.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import score as S   # the published metric, imported so it cannot drift

OUT = S.ROOT / "quant.json"
RNG = np.random.default_rng(20260824)

LEVEL_SUBJECTS = S.SUBJECTS
DOSE_SUBJECTS = ["bee-3-cpl", "tweezers-cpl"]
# (file tag, display name, sign convention used in the report)
DOSE_ARMS = [
    ("G2", "G2-robust  (byte-identical placebo)"),
    ("G4", "G4-softgate"),
    ("G6", "G6-halo"),
]
DOSES = [0, 1, 2, 3, 4, 5, 6, 7, 8]   # keep-bits removed; 8 == ORCH's 8-bit case


def narrow(u16: np.ndarray, k: int) -> np.ndarray:
    """Real quantisation: deterministic in the VALUE, which is the whole point.
    Every pixel holding value v maps to the same v' in every image."""
    if k == 0:
        return u16.astype(np.float64)
    q = 1 << k
    return (np.floor(u16.astype(np.float64) / q) * q)


def dither(u16: np.ndarray, k: int) -> np.ndarray:
    """The INVALID control ORCH named: additive uniform noise of the same
    variance as the quantisation error (q^2/12), but independent of the value."""
    if k == 0:
        return u16.astype(np.float64)
    q = 1 << k
    return u16.astype(np.float64) + RNG.uniform(-q / 2.0, q / 2.0, size=u16.shape)


def green_u16(path: Path) -> np.ndarray:
    import tifffile
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path.name} is {a.dtype}, expected uint16"
    return a[:, :, 1]


def level_census(g: np.ndarray, tflat: np.ndarray, tdet: np.ndarray) -> dict:
    """Distinct levels inside each TILExTILE tile, split by tile class."""
    h, w = g.shape
    hh, ww = h // S.TILE, w // S.TILE
    b = g[: hh * S.TILE, : ww * S.TILE].reshape(hh, S.TILE, ww, S.TILE)
    b = b.transpose(0, 2, 1, 3).reshape(hh, ww, S.TILE * S.TILE)
    b.sort(axis=2)
    # distinct == 1 + number of positions where the sorted run steps
    nlev = 1 + (np.diff(b, axis=2) != 0).sum(axis=2)
    out = {}
    for name, sel in (("flat", tflat), ("detail", tdet)):
        v = nlev[sel]
        out[name] = {
            "n_tiles": int(v.size),
            "min": int(v.min()), "p10": float(np.quantile(v, 0.10)),
            "median": float(np.median(v)), "p90": float(np.quantile(v, 0.90)),
            "max": int(v.max()),
            "frac_below_12": float((v < 12).mean()),
        }
    return out


def main() -> int:
    report = {"levels": {}, "dose": {}, "dither": {}}

    print("=" * 78)
    print("PART A -- level census on the real renders (V-M113's axis)")
    print("=" * 78)
    for subj in LEVEL_SUBJECTS:
        mp = S.MEASURE / f"{subj}__M0.tif"
        ap = S.MEASURE / f"{subj}__A0.tif"
        if not (mp.exists() and ap.exists()):
            print(f"  {subj}: renders missing, skipped")
            continue
        struct = S.structure(S.green(mp))
        fc = float(np.quantile(struct, S.FLAT_FRAC))
        dc = float(np.quantile(struct, 1.0 - S.DET_FRAC))
        tflat, tdet = S.tile_class(struct, fc, dc)
        cen = level_census(green_u16(ap), tflat, tdet)
        report["levels"][subj] = cen
        print(f"\n  {subj}")
        for cls in ("flat", "detail"):
            c = cen[cls]
            print(f"    {cls:<7} tiles={c['n_tiles']:<5} levels "
                  f"min={c['min']:<6} p10={c['p10']:<9.1f} median={c['median']:<9.1f} "
                  f"max={c['max']:<6} frac<12={c['frac_below_12']:.4f}")

    print()
    print("=" * 78)
    print("PART B -- quantisation dose-response on the published statistic")
    print("=" * 78)
    for subj in DOSE_SUBJECTS:
        mp = S.MEASURE / f"{subj}__M0.tif"
        ap = S.MEASURE / f"{subj}__A0.tif"
        if not (mp.exists() and ap.exists()):
            print(f"  {subj}: renders missing, skipped")
            continue

        # Masks are built ONCE from the UNDEGRADED mask arm and held fixed at
        # every dose, so the response is the statistic's and not mask drift.
        # Section 8 of the report is why that is stated rather than assumed.
        struct = S.structure(S.green(mp))
        fc = float(np.quantile(struct, S.FLAT_FRAC))
        dc = float(np.quantile(struct, 1.0 - S.DET_FRAC))
        mflat, mdet = struct <= fc, struct >= dc
        tflat, tdet = S.tile_class(struct, fc, dc)

        ref_u16 = green_u16(ap)
        report["dose"][subj] = {}

        for tag, name in DOSE_ARMS:
            p = S.MEASURE / f"{subj}__{tag}.tif"
            if not p.exists():
                print(f"  {subj} {tag}: missing, skipped")
                continue
            arm_u16 = green_u16(p)
            identical = bool(np.array_equal(arm_u16, ref_u16))
            rows = []
            print(f"\n  {subj}  {name}"
                  f"{'   [green plane bitwise identical to A0]' if identical else ''}")
            print(f"    {'dose':<6}{'dN':>10}{'dD':>10}{'dQ':>10}"
                  f"{'beta':>9}{'impr':>9}{'N(A0)':>10}")
            base_dq = None
            for k in DOSES:
                a = S.score_plane(S.highpass(narrow(arm_u16, k)), mflat, mdet)
                r = S.score_plane(S.highpass(narrow(ref_u16, k)), mflat, mdet)
                tsd_a = S.tile_sd(S.highpass(narrow(arm_u16, k)))
                tsd_r = S.tile_sd(S.highpass(narrow(ref_u16, k)))
                disp = S.dispersion(tsd_a, tsd_r, tdet, True)
                dN, dD, dQ = a["N"] - r["N"], a["D"] - r["D"], a["Q"] - r["Q"]
                if k == 0:
                    base_dq = dQ
                beta = (dQ / base_dq) if (base_dq not in (None, 0.0)) else float("nan")
                imp = disp.get("improved_frac", float("nan"))
                rows.append({"dose": k, "dN": dN, "dD": dD, "dQ": dQ,
                             "beta": beta, "improved_frac": imp,
                             "N_ref": r["N"], "D_ref": r["D"]})
                print(f"    {k:<6}{dN:>+10.5f}{dD:>+10.5f}{dQ:>+10.5f}"
                      f"{beta:>9.4f}{imp:>9.4f}{r['N']:>10.5f}")
            report["dose"][subj][tag] = {"name": name, "identical": identical,
                                         "rows": rows}

    print()
    print("=" * 78)
    print("PART C -- deterministic narrowing vs equal-power random dither (P-F)")
    print("=" * 78)
    print("  ORCH measured a 16x gap on a differencing estimator. If my spatial")
    print("  high-pass shows a comparable gap, the warning applies to me too.")
    for subj in DOSE_SUBJECTS:
        mp = S.MEASURE / f"{subj}__M0.tif"
        ap = S.MEASURE / f"{subj}__A0.tif"
        if not (mp.exists() and ap.exists()):
            continue
        struct = S.structure(S.green(mp))
        fc = float(np.quantile(struct, S.FLAT_FRAC))
        dc = float(np.quantile(struct, 1.0 - S.DET_FRAC))
        mflat, mdet = struct <= fc, struct >= dc
        ref_u16 = green_u16(ap)
        base = S.score_plane(S.highpass(narrow(ref_u16, 0)), mflat, mdet)
        rows = []
        print(f"\n  {subj}   baseline sd_flat = {base['sd_flat']:.4f} DN")
        print(f"    {'dose':<6}{'sd_flat narrow':>16}{'sd_flat dither':>16}"
              f"{'var ratio':>12}")
        for k in (4, 6, 8):
            n = S.score_plane(S.highpass(narrow(ref_u16, k)), mflat, mdet)
            d = S.score_plane(S.highpass(dither(ref_u16, k)), mflat, mdet)
            vn = n["sd_flat"] ** 2 - base["sd_flat"] ** 2
            vd = d["sd_flat"] ** 2 - base["sd_flat"] ** 2
            ratio = (vd / vn) if vn > 0 else float("nan")
            rows.append({"dose": k, "sd_flat_narrow": n["sd_flat"],
                         "sd_flat_dither": d["sd_flat"],
                         "added_var_narrow": vn, "added_var_dither": vd,
                         "dither_over_narrow": ratio})
            print(f"    {k:<6}{n['sd_flat']:>16.4f}{d['sd_flat']:>16.4f}"
                  f"{ratio:>12.4f}")
        report["dither"][subj] = {"baseline_sd_flat": base["sd_flat"], "rows": rows}

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

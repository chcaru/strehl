"""
s27 - the window floor of the spectral n_eff estimator.

Registered in PREREGISTRATION-D.md, committed fc85d50 BEFORE this ran.

Answers the orchestrator's question (b): does M70's spectral n_eff have a
spatially-local form that could serve as a per-tile calibration target, and
below what window would I not trust it?

Design note that s12 could not honour: NESTED crops about the SAME centre, so
image content is held fixed and only the window changes. s12 rescaled its patch
grid, moving window and content together.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402
import s04_through_focus as S4  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
ROOT = r"D:\personal\macro"

WINDOWS = (256, 128, 64, 32, 16)
STACKS = {"wrapped-text-1": 100.0, "wrapped-text-2": 400.0}
RNG = np.random.default_rng(70027)


def bins_in_band(lo: float, hi: float, tile: int) -> float:
    """V17 as PRE-REGISTERED: analytic annulus area. Kept for the record.

    s27 found this OVERSTATES occupancy at small tiles -- see actual_bins().
    """
    return float(np.pi * (hi * hi - lo * lo) * tile * tile)


def actual_bins(lo: float, hi: float, tile: int) -> int:
    """V17 as OPERATED: how many DISCRETE radial frequencies land in the band.

    The radial grid at a Welch tile of `tile` samples has spacing 1/tile. A band
    narrower than that spacing can contain zero grid points however large its
    analytic area is, which is what actually makes band_average return nan.
    """
    f = np.arange(0, tile // 2 + 1) / float(tile)
    return int(np.sum((f >= lo) & (f < hi)))


def band_powers(patch: np.ndarray, tile: int) -> np.ndarray:
    f, pr, c = L.spectrum(patch, "GQ", tile=tile, window="hann", sector="iso")
    ba = M.band_average(f, pr, c)
    return np.array([ba[b[0]][0] for b in M.BANDS])


def n_eff_unclipped(s: np.ndarray) -> float:
    """P5's corrected estimator: NO clip before the sum."""
    mx = float(np.max(s))
    return float(np.sum(s) / mx) if mx > 0 else np.nan


def mid_n_eff(power: np.ndarray, nvar: np.ndarray) -> float:
    """power (K, B), nvar (K,) -> mean over mid bands of unclipped n_eff."""
    out = []
    for bd in M.MID_BANDS:
        j = [b[0] for b in M.BANDS].index(bd)
        out.append(n_eff_unclipped(power[:, j] - nvar))
    return float(np.mean(out))


def crop_centre(a: np.ndarray, size: int) -> np.ndarray:
    r0 = (a.shape[0] - size) // 2
    c0 = (a.shape[1] - size) // 2
    return a[r0:r0 + size, c0:c0 + size]


def frames_of(stack: str) -> list[str]:
    d = os.path.join(ROOT, stack)
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.lower().endswith(".arw")]


def load_gq(path: str, rc: int, cc: int, size: int) -> np.ndarray:
    a = L.load_active(path)
    return L.crop_lattice(a, "GQ", rc, cc, size)


def calibrate_step(latent: np.ndarray, target: float, iso: float) -> float:
    """V15: the plant must resemble the stack its latent came from.

    The first s27 run used an arbitrary 0.55 px/frame ladder and produced
    n_eff_true = 1.456 against a real 3.906 -- V15 FIRED. The blur ladder is
    therefore calibrated so the plant's noiseless mid-band n_eff matches the
    real stack's, which is what makes W1's ratio meaningful.
    """
    lo, hi = 0.02, 1.20
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        v = plant_true_n_eff(latent, mid, 256, 128)
        if v > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def blur_ladder(K: int, step: float) -> np.ndarray:
    return np.abs(np.arange(K) - K // 2) * step + 0.35


def plant_true_n_eff(latent: np.ndarray, step: float, P: int, tile: int) -> float:
    K = 41
    sig = blur_ladder(K, step)
    clean = [band_powers(crop_centre(
        gaussian_filter(latent, s, mode="reflect"), P), tile) for s in sig]
    return mid_n_eff(np.array(clean), np.zeros(K))


def null_distribution(shape_p: int, tile: int, lvl: float, iso: float,
                      trials: int = 40, K: int = 41) -> dict:
    """W2 done correctly: n_eff on pure noise is a RATIO OF NOISE TO NOISE and
    is wildly dispersed on a single draw. The first s27 run tested one draw and
    'failed' W2 at every window including 256, where the estimator is known
    null-safe (P5: -0.16..+0.08 over many trials). The statistic is the
    DISTRIBUTION, so that is what is measured here.
    """
    nvar = float(M.noise_var_dn2(lvl, iso))
    vals = []
    for _ in range(trials):
        pw = np.array([band_powers(
            np.full((shape_p, shape_p), lvl)
            + RNG.normal(0.0, np.sqrt(nvar), (shape_p, shape_p)), tile)
            for _ in range(K)])
        v = mid_n_eff(pw, np.full(K, nvar))
        if np.isfinite(v):
            vals.append(v)
    if not vals:
        return {"median": np.nan, "p05": np.nan, "p95": np.nan, "n": 0}
    a = np.array(vals)
    return {"median": float(np.median(a)), "p05": float(np.percentile(a, 5)),
            "p95": float(np.percentile(a, 95)), "n": len(vals)}


# --------------------------------------------------------------------------
def arm_plant_and_null(latent: np.ndarray, iso: float, step: float):
    """PLANT: real latent, calibrated Gaussian blur ladder, modelled noise."""
    K = 41
    sig = blur_ladder(K, step)
    lvl = float(np.mean(latent))
    nvar_true = float(M.noise_var_dn2(lvl, iso))

    res = {"per_window": {}, "step": step}
    for P in WINDOWS:
        tile = max(P // 2, 8)
        clean, noisy = [], []
        for k in range(K):
            b = gaussian_filter(latent, sig[k], mode="reflect")
            bc = crop_centre(b, P)
            clean.append(band_powers(bc, tile))
            noisy.append(band_powers(
                bc + RNG.normal(0.0, np.sqrt(nvar_true), bc.shape), tile))
        clean = np.array(clean); noisy = np.array(noisy)
        res["per_window"][P] = {
            "tile": tile,
            "bins_b3": bins_in_band(0.100, 0.150, tile),
            "actual_b3": actual_bins(0.100, 0.150, tile),
            "actual_b4": actual_bins(0.150, 0.200, tile),
            "actual_b5": actual_bins(0.200, 0.2762, tile),
            "n_eff_true": mid_n_eff(clean, np.zeros(K)),
            "n_eff_hat": mid_n_eff(noisy, np.full(K, nvar_true)),
            "null": null_distribution(P, tile, lvl, iso),
        }
    return res


def arm_real(stack: str, iso: float):
    paths = frames_of(stack)
    rc, cc = S4.CENTRES[len(S4.CENTRES) // 2]
    big = [load_gq(p, rc, cc, WINDOWS[0]) for p in paths]
    out = {}
    for P in WINDOWS:
        tile = max(P // 2, 8)
        pw, lv = [], []
        for a in big:
            c = crop_centre(a, P)
            pw.append(band_powers(c, tile))
            lv.append(M.w2_weighted_mean(np.clip(c, 0.0, None), tile))
        pw = np.array(pw)
        nvar = np.array([M.noise_var_dn2(x, iso) for x in lv])
        out[P] = {"tile": tile, "n_eff": mid_n_eff(pw, nvar),
                  "bins_b3": bins_in_band(0.100, 0.150, tile)}
    return out


def main() -> None:
    print("=" * 92)
    print("s27  WINDOW FLOOR OF THE SPECTRAL n_eff ESTIMATOR   (PREREGISTRATION-D, fc85d50)")
    print("=" * 92)

    print("\n[V17] bins per band -- PRE-REGISTERED analytic area vs ACTUAL discrete")
    print("      occupancy. The analytic form was the registered one and it is WRONG:")
    print("      a band narrower than the 1/tile grid spacing can hold ZERO grid")
    print("      points however large its area, which is what returns nan.")
    print(f"  {'window':>7s} {'tile':>5s} {'analytic b3':>12s} " +
          " ".join(f"{'act ' + b[0]:>11s}" for b in M.BANDS[2:5]))
    for P in WINDOWS:
        t = max(P // 2, 8)
        print(f"  {P:7d} {t:5d} {bins_in_band(0.100, 0.150, t):12.1f} " +
              " ".join(f"{actual_bins(b[1], b[2], t):11d}" for b in M.BANDS[2:5]))

    st = "wrapped-text-1"
    iso = STACKS[st]
    paths = frames_of(st)
    rc, cc = S4.CENTRES[len(S4.CENTRES) // 2]
    lat = load_gq(paths[len(paths) // 2], rc, cc, WINDOWS[0])

    print("\n[W3] REAL, nested crops about one centre -- content fixed, window varies")
    real = {}
    for s, i in STACKS.items():
        real[s] = arm_real(s, i)
    print(f"  {'window':>7s} " + " ".join(f"{s:>26s}" for s in STACKS))
    for P in WINDOWS:
        cells = []
        for s in STACKS:
            r = real[s][P]
            base = real[s][WINDOWS[0]]["n_eff"]
            rat = r["n_eff"] / base if base else np.nan
            fl = ("UNDEF" if actual_bins(0.150, 0.200, r["tile"]) < 1
                  else ("PASS" if 0.90 <= rat <= 1.10 else "FAIL"))
            cells.append(f"{r['n_eff']:8.3f} x{rat:5.3f} {fl:>6s}")
        print(f"  {P:7d} " + " ".join(f"{c:>26s}" for c in cells))

    target = real[st][WINDOWS[0]]["n_eff"]
    print(f"\n[V15] calibrating the plant to the stack its latent came from")
    print(f"  the FIRST s27 run used an arbitrary 0.55 px/frame ladder and gave")
    print(f"  n_eff_true = 1.456 against a real {target:.3f}  ->  V15 FIRED.")
    step = calibrate_step(lat, target, iso)
    print(f"  calibrated blur step: {step:.4f} px/frame  (corpus measured range")
    print(f"  0.6017-1.1856 px/frame, section 19.2)")

    pl = arm_plant_and_null(lat, iso, step)
    print(f"\n[plant] latent = real patch, {st} frame {len(paths)//2}, "
          f"{WINDOWS[0]} GQ, ISO {iso:.0f}, K=41")

    print("\n[W1/W2] PLANT with a real latent, and the NULL as a DISTRIBUTION")
    print("        (W2 on a single draw is meaningless: n_eff on pure noise is a")
    print("         ratio of noise to noise. 40 trials per window.)")
    print(f"  {'window':>7s} {'act b3':>7s} {'true':>8s} {'measured':>9s} "
          f"{'hat/true':>9s} {'null med':>9s} {'null p05..p95':>20s} {'W1':>6s} {'W2':>6s}")
    for P in WINDOWS:
        r = pl["per_window"][P]
        und = r["actual_b4"] < 1
        rat = r["n_eff_hat"] / r["n_eff_true"] if r["n_eff_true"] else np.nan
        w1 = "UNDEF" if und else ("PASS" if abs(rat - 1) <= 0.10 else "FAIL")
        nm = r["null"]["median"]
        w2 = "UNDEF" if und else ("PASS" if abs(nm) <= 0.25 else "FAIL")
        rng = f"{r['null']['p05']:8.3f}..{r['null']['p95']:.3f}"
        print(f"  {P:7d} {r['actual_b3']:7d} {r['n_eff_true']:8.3f} "
              f"{r['n_eff_hat']:9.3f} {rat:9.3f} {nm:9.3f} {rng:>20s} "
              f"{w1:>6s} {w2:>6s}")

    print("\n[V16] which term dominates -- discretisation (noiseless) or noise?")
    print(f"  {'window':>7s} {'noiseless/256':>14s} {'noise term':>12s} {'dominant':>16s}")
    b = pl["per_window"][WINDOWS[0]]
    for P in WINDOWS:
        r = pl["per_window"][P]
        if r["actual_b4"] < 1:
            print(f"  {P:7d} {'UNDEFINED':>14s} {'UNDEFINED':>12s} {'-':>16s}")
            continue
        disc = r["n_eff_true"] / b["n_eff_true"]
        noise = r["n_eff_hat"] / r["n_eff_true"] if r["n_eff_true"] else np.nan
        dom = "discretisation" if abs(disc - 1) > abs(noise - 1) else "noise"
        print(f"  {P:7d} {disc:14.3f} {noise:12.3f} {dom:>16s}")

    print("\n[VERDICT] smallest window meeting W1, W2 and W3 on both stacks:")
    ok = []
    for P in WINDOWS:
        r = pl["per_window"][P]
        if r["actual_b4"] < 1:
            continue
        rat = r["n_eff_hat"] / r["n_eff_true"] if r["n_eff_true"] else np.nan
        if abs(rat - 1) > 0.10 or abs(r["null"]["median"]) > 0.25:
            continue
        if all(0.90 <= real[s][P]["n_eff"] / real[s][WINDOWS[0]]["n_eff"] <= 1.10
               for s in STACKS):
            ok.append(P)
    print(f"  windows passing all three: {ok if ok else 'NONE'}")
    if ok:
        m = min(ok)
        print(f"  -> recommended floor: {m} GQ samples = {2 * m - 1} sensor px, "
              f"Welch tile {max(m // 2, 8)}")

    with open(os.path.join(OUT, "s27_window_floor.json"), "w", encoding="utf-8") as fh:
        json.dump({"plant": {str(k): v for k, v in pl["per_window"].items()},
                   "calibrated_step": step,
                   "real": {s: {str(k): v for k, v in d.items()}
                            for s, d in real.items()},
                   "passing": ok}, fh, indent=1)
    print("\nwrote out/s27_window_floor.json")


if __name__ == "__main__":
    main()

"""BUILD-PYRNOISE -- commission the instrument before believing a single number.

Rule 20: before running any gate, control or metric, write down the input that
would make it FAIL, and check such an input exists. Every criterion below is
stated with its pass bar BEFORE the number is printed, and the file carries a
SABOTAGE arm -- a plain gradient-energy "detail" statistic -- which must read RED
on the same plants the real statistic passes. A commissioning suite where
everything passes has not shown it can reject.

Pre-registered criteria
  C1  noise null, detail    |d f50| <= 3%       under +15% added noise sd
  C2  blur null, detail     f50 falls monotonically in sigma_blur, and by >= 15%
                            at sigma = 1.0 px
  C3  contrast null, detail |d f50| <= 1e-9     under a x2.0 gain (arithmetic)
  C4  positive control      hp_sd after planting sigma_a matches
                            sqrt(sigma_0^2 + sigma_a^2) to <= 1.0%
  C5  identity null         arm against a bit-identical re-render reads 1.000000
  C6  SABOTAGE reads RED    plain gradient energy moves >= 10% under the same
                            +15% noise plant that C1 passes
  C7  rule 9 flat control   the detail statistic must not credit a flat region
                            with detail when noise is added to it
"""

import pathlib

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

import pyrnoise as pn
from measure import choose_rois, fov_scale, MATCHED

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
RNG = np.random.default_rng(20260826)

PASS = {}


def verdict(key, ok, msg):
    PASS[key] = ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {key}  {msg}")


def grad_energy(a):
    """SABOTAGE ARM. The statistic this project has already killed: mean
    gradient magnitude. Kept runnable so the suite can be shown to reject."""
    gy, gx = np.gradient(np.asarray(a, dtype=np.float64))
    return float(np.sqrt(gy * gy + gx * gx).mean())


def main(subject="109MSDCF"):
    d = RENDERS / subject
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    pool = [t for t in MATCHED if (d / f"{t}.tif").exists()] + [frames[len(frames) // 2]]
    mean_img = np.mean([pn.green(d / f"{t}.tif") for t in pool], axis=0)
    # Use the same ROI measure.py measures on: choose_rois now also requires a
    # candidate to clear the border on the ALIGNED grid, so it needs the same
    # magnification, read from the same run's own banner.
    s = fov_scale(d / "pyr_default.err")
    flat_roi, _, flat_mean, det_roi, _, det_mean, _, _ = choose_rois(mean_img, s)

    ref = "frame011" if "frame011" in frames else frames[len(frames) // 2]
    img = pn.green(d / f"{ref}.tif")
    detail = pn.crop(img, det_roi, pn.BOX).copy()
    flat = pn.crop(img, flat_roi, pn.BOX).copy()
    detail_i = detail[pn.BOX:-pn.BOX, pn.BOX:-pn.BOX]

    print(f"=== commissioning on {subject} / {ref} (real pixels, real noise) ===")
    print(f"detail tile {det_roi} mean {det_mean:.1f} DN   flat tile {flat_roi} mean {flat_mean:.1f} DN")

    s0_detail = pn.hp_sd(detail)
    s0_flat = pn.hp_sd(flat)
    f0 = pn.f50(detail_i)
    g0 = grad_energy(detail_i)
    print(f"baseline: hp_sd(detail) {s0_detail:.4f} DN   hp_sd(flat) {s0_flat:.4f} DN")
    print(f"          f50(detail)   {f0:.6f} c/px   grad_energy(detail) {g0:.4f} DN/px\n")

    # ---- C4 positive control: plant a known noise increment ---------------
    print("C4  POSITIVE CONTROL -- plant a known sigma, require the predicted move")
    worst = 0.0
    for frac in (0.05, 0.15, 0.30, 1.00):
        sa = frac * s0_flat
        n = RNG.normal(0.0, sa, size=flat.shape)
        meas = pn.hp_sd(flat + n)
        pred = np.sqrt(s0_flat ** 2 + sa ** 2)
        err = abs(meas / pred - 1.0)
        worst = max(worst, err)
        print(f"      +{frac:5.0%} sigma_a={sa:7.4f}  predicted {pred:8.4f}  measured {meas:8.4f}"
              f"  err {err:+.3%}")
    verdict("C4", worst <= 0.010, f"worst |measured/predicted - 1| = {worst:.3%} (bar 1.0%)")

    # ---- C5 identity null --------------------------------------------------
    print("\nC5  NULL -- the shipping arm against a bit-identical re-render")
    a = pn.green(d / "pyr_default.tif")
    b = pn.green(d / "pyr_default_null.tif")
    import hashlib
    ha = hashlib.sha256((d / "pyr_default.tif").read_bytes()).hexdigest()
    hb = hashlib.sha256((d / "pyr_default_null.tif").read_bytes()).hexdigest()
    ra = pn.roi_stats(a, flat_roi)
    rb = pn.roi_stats(b, flat_roi)
    ident = (ha == hb)
    r_raw, r_hp = rb["raw_sd"] / ra["raw_sd"], rb["hp_sd"] / ra["hp_sd"]
    print(f"      sha256 equal: {ident}   ({ha[:16]}...)")
    print(f"      raw_sd ratio {r_raw:.6f}x   hp_sd ratio {r_hp:.6f}x")
    verdict("C5", ident and abs(r_raw - 1) < 1e-12 and abs(r_hp - 1) < 1e-12,
            f"re-render reads {r_hp:.6f}x")

    # ---- C1 / C6 noise null on the DETAIL statistic -----------------------
    print("\nC1  NOISE NULL on the detail statistic (and C6, the sabotage arm)")
    print("      this is the test that killed a gradient norm at +33%.")
    print("      The plant is swept to +100% because that is the SIZE OF THE EFFECT")
    print("      being measured -- a single frame carries roughly twice a merged")
    print("      arm's noise -- and a null commissioned only at +15% would say")
    print("      nothing about the range the arms actually span.")
    c1_worst, c6_best = 0.0, 0.0
    for frac in (0.05, 0.15, 0.30, 0.50, 1.00):
        sa = frac * s0_detail
        n = RNG.normal(0.0, sa, size=detail_i.shape)
        df = pn.f50(detail_i + n) / f0 - 1.0
        dg = grad_energy(detail_i + n) / g0 - 1.0
        c1_worst = max(c1_worst, abs(df))
        c6_best = max(c6_best, abs(dg))
        print(f"      +{frac:5.0%} noise :  f50 {df:+8.3%}    grad_energy {dg:+8.3%}  <-- sabotage")
    verdict("C1", c1_worst <= 0.030,
            f"f50 moves at most {c1_worst:+.3%} anywhere in the swept range (bar 3%)")
    verdict("C6", c6_best >= 0.100,
            f"sabotage moves {c6_best:+.3%} on the same plants -- the plant IS potent, "
            f"and a naive statistic WOULD have been fooled (bar 10%)")

    # ---- C2 blur null ------------------------------------------------------
    print("\nC2  BLUR NULL on the detail statistic")
    prev, mono, drop1 = f0, True, None
    for sg in (0.5, 1.0, 1.5, 2.0):
        fb = pn.f50(gaussian_filter(detail_i, sg))
        gb = grad_energy(gaussian_filter(detail_i, sg))
        if fb >= prev:
            mono = False
        prev = fb
        if abs(sg - 1.0) < 1e-9:
            drop1 = 1.0 - fb / f0
        print(f"      sigma {sg:4.1f} px :  f50 {fb:.6f} ({fb/f0-1:+8.3%})"
              f"    grad_energy {gb/g0-1:+8.3%}")
    verdict("C2", mono and drop1 >= 0.15,
            f"monotone={mono}, fall at sigma=1.0 px is {drop1:.1%} (bar 15%)")

    # ---- C3 contrast null --------------------------------------------------
    print("\nC3  CONTRAST NULL on the detail statistic")
    f2 = pn.f50(detail_i * 2.0)
    f_off = pn.f50(detail_i + 500.0)
    print(f"      x2.0 gain    : f50 {f2:.9f} vs {f0:.9f}   d = {f2-f0:+.3e}")
    print(f"      +500 DN bias : f50 {f_off:.9f}            d = {f_off-f0:+.3e}")
    verdict("C3", abs(f2 - f0) <= 1e-9 and abs(f_off - f0) <= 1e-9,
            "gain and offset invariance are arithmetic, and hold")

    # ---- the one free choice in f50, made visible -------------------------
    print("\n    f_lo sensitivity (the single free parameter in f50), on this tile:")
    base = pn.f50_sensitivity(detail_i)
    blur = pn.f50_sensitivity(gaussian_filter(detail_i, 1.0))
    for lo in sorted(base):
        print(f"      f_lo {lo:.2f} : f50 {base[lo]:.6f}   under sigma=1.0 px blur "
              f"{blur[lo]:.6f}  ({blur[lo]/base[lo]-1:+.2%})")

    # ---- C7 rule 9: flat-ROI control for the detail statistic -------------
    print("\nC7  RULE 9 -- the detail statistic on a FLAT region")
    ff0 = pn.f50(flat[pn.BOX:-pn.BOX, pn.BOX:-pn.BOX])
    gg0 = grad_energy(flat[pn.BOX:-pn.BOX, pn.BOX:-pn.BOX])
    sa = 0.15 * s0_flat
    n = RNG.normal(0.0, sa, size=flat[pn.BOX:-pn.BOX, pn.BOX:-pn.BOX].shape)
    ff1 = pn.f50(flat[pn.BOX:-pn.BOX, pn.BOX:-pn.BOX] + n)
    gg1 = grad_energy(flat[pn.BOX:-pn.BOX, pn.BOX:-pn.BOX] + n)
    print(f"      flat tile f50 {ff0:.6f} -> {ff1:.6f} under +15% noise ({ff1/ff0-1:+.3%})")
    print(f"      flat tile grad_energy {gg0:.3f} -> {gg1:.3f} ({gg1/gg0-1:+.3%})  <-- sabotage")
    verdict("C7", abs(ff1 / ff0 - 1.0) <= 0.05,
            f"adding noise to a flat region moves f50 {ff1/ff0-1:+.3%} (bar 5%)")

    print("\n" + "=" * 62)
    bad = [k for k, v in PASS.items() if not v]
    print("COMMISSIONING: " + ("ALL PASS" if not bad else f"FAILED {bad}"))
    print("=" * 62)
    return not bad


if __name__ == "__main__":
    import sys
    ok = main(sys.argv[1] if len(sys.argv) > 1 else "109MSDCF")
    sys.exit(0 if ok else 1)

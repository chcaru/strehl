"""BUILD-PYRNOISE -- a declared bake-off between candidate DETAIL statistics.

`f50` -- the cumulative-median frequency -- FAILED its own pre-registered blur
null (2.0% fall at sigma = 1.0 px against a 15% bar). Rule 30 forbids narrowing
an assertion to make it pass, so the bar does not move. Instead every candidate
is run against the SAME bars, and whichever passes is the one that gets used.
Candidates that fail are reported failing.

BARS, registered here and unchanged from `commission.py`:
  B1  noise null       |d stat| <= 3%  at EVERY plant from +5% to +100% added
                       noise sd. +100% is the size of the real effect: a single
                       frame carries roughly twice a merged arm's noise.
  B2  blur null        stat moves monotonically in sigma_blur AND by >= 15% at
                       sigma = 1.0 px, in the direction that means "less detail"
  B3  contrast null    exactly invariant to a x2 gain and a +500 DN offset
  B4  potency          the sabotage arm (plain gradient energy) must move >= 10%
                       on the same plants, or the plants prove nothing

Run on TWO tiles from two different subjects so a pass is not a property of one
patch of one photograph.
"""

import pathlib

import numpy as np
from scipy.ndimage import gaussian_filter

import pyrnoise as pn
from measure import choose_rois, fov_scale, MATCHED

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
RNG = np.random.default_rng(20260826)

# name -> (fn, sign) ; sign = +1 if the statistic FALLS on blur, -1 if it rises
#
# `f_lo` is f50's single free parameter. It is calibrated HERE, against planted
# blur and planted noise whose answers are known -- never against the arms. The
# setting is frozen before any arm is read, and the whole sweep is reported so
# the choice is visible rather than asserted.
CANDIDATES = {
    "f50(f_lo=0.05)": (lambda a: pn.f50(a, f_lo=0.05), +1),
    "f50(f_lo=0.12)": (lambda a: pn.f50(a, f_lo=0.12), +1),
    "f50(f_lo=0.18)": (lambda a: pn.f50(a, f_lo=0.18), +1),
    "f50(f_lo=0.25)": (lambda a: pn.f50(a, f_lo=0.25), +1),
    "hf_share      ": (pn.hf_share, +1),
    "spectral_cent ": (pn.spectral_centroid, +1),
    "acf_length    ": (lambda a: pn.acf_length(np.pad(a, pn.BOX, mode="reflect")), -1),
    "grad_energy(S)": (lambda a: float(np.hypot(*np.gradient(a)).mean()), +1),
}


def tile_of(subject):
    d = RENDERS / subject
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    pool = [t for t in MATCHED if (d / f"{t}.tif").exists()] + [frames[len(frames) // 2]]
    mean_img = np.mean([pn.green(d / f"{t}.tif") for t in pool], axis=0)
    _, _, _, det_roi, _, det_mean, _, _ = choose_rois(mean_img, fov_scale(d / "pyr_default.err"))
    ref = frames[len(frames) // 2]
    img = pn.green(d / f"{ref}.tif")
    return pn.crop(img, det_roi), det_roi, ref, det_mean


def bakeoff(subjects):
    results = {k: {"noise": [], "blur1": [], "mono": [], "contrast": []} for k in CANDIDATES}
    for subject in subjects:
        tile, roi, ref, mean_dn = tile_of(subject)
        s0 = pn.hp_sd(np.pad(tile, pn.BOX, mode="reflect"))
        print(f"\n--- {subject}  detail tile {roi} on {ref}, mean {mean_dn:.0f} DN, "
              f"hp_sd {s0:.1f} DN ---")
        hdr = f"{'statistic':<16}{'base':>12} | " + "".join(f"{f'+{int(p*100)}%':>9}" for p in
                                                            (0.05, 0.15, 0.30, 0.50, 1.00))
        hdr += " | " + "".join(f"{f'blur{s}':>9}" for s in (0.5, 1.0, 1.5, 2.0)) + f"{'x2':>8}"
        print(hdr)
        print("-" * len(hdr))
        plants = {p: RNG.normal(0.0, p * s0, size=tile.shape) for p in (0.05, 0.15, 0.30, 0.50, 1.00)}
        blurs = {s: gaussian_filter(tile, s) for s in (0.5, 1.0, 1.5, 2.0)}
        for name, (fn, sign) in CANDIDATES.items():
            b = fn(tile)
            row = f"{name:<16}{b:12.6f} | "
            worst = 0.0
            for p in (0.05, 0.15, 0.30, 0.50, 1.00):
                d = fn(tile + plants[p]) / b - 1.0
                worst = max(worst, abs(d))
                row += f"{d:+8.2%} "
            results[name]["noise"].append(worst)
            row += "| "
            prev, mono, drop1 = b, True, None
            for s in (0.5, 1.0, 1.5, 2.0):
                v = fn(blurs[s])
                d = v / b - 1.0
                # "less detail" means down for sign +1, up for sign -1
                if sign * (v - prev) > 0:
                    mono = False
                prev = v
                if abs(s - 1.0) < 1e-9:
                    drop1 = -sign * d
                row += f"{d:+8.2%} "
            results[name]["blur1"].append(drop1)
            results[name]["mono"].append(mono)
            c = abs(fn(tile * 2.0) / b - 1.0) + abs(fn(tile + 500.0) / b - 1.0)
            results[name]["contrast"].append(c)
            row += f"{c:8.1e}"
            print(row)

    print(f"\n{'=' * 78}\nVERDICT against the registered bars\n{'=' * 78}")
    print(f"{'statistic':<16}{'B1 noise<=3%':>14}{'B2 blur>=15%':>14}{'mono':>7}"
          f"{'B3 contrast':>13}{'D=blur/noise':>14}   verdict")
    winners = []
    for name in CANDIDATES:
        r = results[name]
        n = max(r["noise"])
        b1 = min(r["blur1"])
        mono = all(r["mono"])
        c = max(r["contrast"])
        ok_n, ok_b, ok_c = n <= 0.03, b1 >= 0.15 and mono, c <= 1e-9
        v = "PASS" if (ok_n and ok_b and ok_c) else "FAIL(" + ",".join(
            x for x, o in (("B1", ok_n), ("B2", ok_b), ("B3", ok_c)) if not o) + ")"
        if ok_n and ok_b and ok_c:
            winners.append(name.strip())
        dratio = (b1 / n) if n > 0 else float("inf")
        print(f"{name:<16}{n:13.2%}{b1:13.2%}{str(mono):>7}{c:13.1e}{dratio:13.1f}x   {v}")
    print(f"\nB4 potency: grad_energy(S) moved {max(results['grad_energy(S)']['noise']):.1%} on "
          f"the noise plants -- the plants are potent, so a PASS on B1 is a real result.")
    print("\nD is the DISCRIMINATION RATIO: the sigma=1.0 px blur response divided by the")
    print("worst noise-plant response. It is what decides whether a movement between two")
    print("arms can be attributed to detail rather than to the arms' different noise.")
    print(f"\nSTATISTICS THAT MAY BE USED: {winners if winners else 'NONE -- report noise only'}")
    return winners


if __name__ == "__main__":
    import sys
    subs = sys.argv[1:] or ["109MSDCF"]
    bakeoff(subs)

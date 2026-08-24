"""s11: EXPLORATORY secondary analysis, declared post-hoc.

Two changes from the pre-registered instrument, each with a stated reason that
is independent of the outcome:

  1. ESF half-width 64 um instead of 192 um.  The pre-registration chose 192 um
     to halve an Airy-tail truncation bias that the free amplitude already
     absorbs.  On real data the wider window admits scene structure and, more
     importantly, spreads the same samples over 3x as many bins, so the noise
     floor is ~1.8x higher.  The synthetic controls in s09 show 64 um recovers
     planted cutoffs of 60/86.3/110/140 to within 0.4%.
  2. Per-wing ESF deramp.  Validated in s09: it is a no-op on clean plants and
     on ramped plants, so it changes nothing that matters; it is kept only
     because the real ESF demonstrably carries different wing slopes.

A split-half floor is computed as an independent check on the band floor: the
along-edge samples are split into two interleaved sets, and the half-difference
spectrum estimates noise without assuming any band is signal-free.

This analysis CANNOT rescue the pre-registered verdict and is not used to.
It exists to answer one one-sided question that M85 needs: is there any
measurable energy above 86.3 cy/mm?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

ROOT = Path("D:/personal/macro")
OUT = Path(__file__).resolve().parents[1] / "out"
BIN_UM, TAPER, CORE_UM = 0.64, 0.10, 24.0
HALF_UM = 64.0
F_LO, F_HI = 10.0, 150.0
NB = (250.0, 380.0)
NROW, NCOL = 160, 400

# best frames taken from the pre-registered s06/s07 focus rule, unchanged
BEST = {
    ("119MSDCF", "A1"): 6, ("119MSDCF", "A2"): 6, ("119MSDCF", "A3"): 5,
    ("119MSDCF", "A4"): 9,
    ("109MSDCF", "C1"): 17, ("109MSDCF", "C2"): 8, ("109MSDCF", "C3"): 9,
    ("109MSDCF", "C4"): 6,
    ("tweezers-cpl", "D1"): 90, ("tweezers-cpl", "D2"): 3,
    ("tweezers-cpl", "D3"): 49,
}
ROIS = {
    "119MSDCF": [("A1", 1280, 0), ("A2", 1280, 200), ("A3", 1280, 400),
                 ("A4", 1280, 600)],
    "109MSDCF": [("C1", 1280, 0), ("C2", 1280, 200), ("C3", 1200, 400),
                 ("C4", 1200, 600)],
    "tweezers-cpl": [("D1", 2080, 2000), ("D2", 2080, 2400),
                     ("D3", 2080, 2600)],
}


def one(sub, xs, ys, r0, c0):
    s = sub[r0:r0 + NROW, c0:c0 + NCOL].astype(float)
    xr, yr = xs[c0:c0 + NCOL], ys[r0:r0 + NROW]
    line = L.fit_edge_line(s, xr, yr, axis="horizontal")
    XX, YY = np.meshgrid(xr, yr)
    full = L.sfr_from_sites2(s.ravel(), XX.ravel(), YY.ravel(), line,
                             BIN_UM, HALF_UM, TAPER, core_um=CORE_UM)
    # interleaved along-edge halves: same scene positions, independent noise
    halves = []
    for off in (0, 1):
        sh = s[:, off::2]
        Xh, Yh = np.meshgrid(xr[off::2], yr)
        halves.append(L.sfr_from_sites2(sh.ravel(), Xh.ravel(), Yh.ravel(),
                                        line, BIN_UM, HALF_UM, TAPER,
                                        core_um=CORE_UM))
    f = full["freq_cymm"]
    m1, m2 = halves[0]["mtf"], halves[1]["mtf"]
    split = np.abs(m1 - m2) / 2.0
    fl, flat = L.noise_floor_curve(f, full["mtf"], BIN_UM, NB)
    fit = L.fit_fc(f, full["mtf"], F_LO, F_HI)
    return f, full, fl, flat, split, fit, line


def main():
    rows = []
    print("EXPLORATORY: half-width 64 um, per-wing deramp, split-half floor")
    print("=" * 96)
    print(f"{'stack':>13} {'roi':>3} {'frm':>4} {'mtf40':>6} {'fc':>7} "
          f"{'sig':>5} {'amp':>5} | {'M86':>7} {'band':>7} {'split':>7} "
          f"{'z86':>5} | {'M97':>7} {'band':>7} {'split':>7} {'z97':>5}")
    for stack, rois in ROIS.items():
        files = sorted((ROOT / stack).glob("*.ARW"))
        for name, r0, c0 in rois:
            k = BEST[(stack, name)]
            active = L.load_active(files[k])
            sub, xs, ys = L.green_sites(active, "G1")
            try:
                f, full, fl, flat, split, fit, line = one(sub, xs, ys, r0, c0)
            except L.EdgeFitError as e:
                print(f"{stack:>13} {name:>3} {k:4d}  {e}")
                del active, sub
                continue
            del active, sub

            def at(fr):
                i = int(np.argmin(np.abs(f - fr)))
                lo = max(0, i - 1)
                use = max(fl[i], split[i])
                return dict(i=i, mtf=float(full["mtf"][i]),
                            band=float(fl[i]), split=float(split[i]),
                            z=float(full["mtf"][i] / use),
                            run3=bool(np.all(full["mtf"][lo:lo + 3] >
                                             3.0 * np.maximum(fl[lo:lo + 3],
                                                              split[lo:lo + 3]))))
            i40 = int(np.argmin(np.abs(f - 40.0)))
            a86, a97 = at(86.30), at(97.66)
            print(f"{stack:>13} {name:>3} {k:4d} {full['mtf'][i40]:6.3f} "
                  f"{fit['fc_cymm']:7.2f} {fit['sigma_um']:5.2f} "
                  f"{fit['amp']:5.2f} | {a86['mtf']:7.4f} {a86['band']:7.4f} "
                  f"{a86['split']:7.4f} {a86['z']:5.2f} | {a97['mtf']:7.4f} "
                  f"{a97['band']:7.4f} {a97['split']:7.4f} {a97['z']:5.2f}")
            rows.append(dict(stack=stack, roi=name, frame=k,
                             mtf40=float(full["mtf"][i40]), fc=fit["fc_cymm"],
                             sigma=fit["sigma_um"], amp=fit["amp"],
                             angle=line["angle_deg"],
                             resid=line["resid_sd_px"],
                             contrast=line["contrast"], flat=flat,
                             a86=a86, a97=a97))

    print()
    print("BAR 1 re-run on the exploratory settings (still one-sided, still")
    print("conservative: the threshold uses the LARGER of the band floor and")
    print("the split-half floor at each frequency)")
    det = [r for r in rows if r["a97"]["run3"] and r["a97"]["z"] > 3.0]
    st = sorted({r["stack"] for r in det})
    print(f"  ROIs passing 3-sigma / 3-bin at 97.66 cy/mm: {len(det)} "
          f"from stacks {st}")
    det86 = [r for r in rows if r["a86"]["run3"] and r["a86"]["z"] > 3.0]
    print(f"  ROIs passing at 86.30 cy/mm: {len(det86)} from stacks "
          f"{sorted({r['stack'] for r in det86})}")

    print()
    print("Diffraction-limited expectation through the SAME instrument, for")
    print("comparison (from the s09 plants at fc=86.3): MTF(40) = 0.42")
    f56 = [r["mtf40"] for r in rows if r["stack"] in ("119MSDCF",)]
    print(f"  measured MTF(40) on 119MSDCF f/5.6: "
          f"{np.median(f56):.3f} (n={len(f56)})  -> shortfall factor "
          f"{0.42/np.median(f56):.2f}x")

    a = [r["fc"] for r in rows if r["stack"] == "119MSDCF"]
    b = [r["fc"] for r in rows if r["stack"] == "109MSDCF"]
    print(f"\nBAR 3 on the exploratory settings: f/5.6 median "
          f"{np.median(a):.2f}, f/11 median {np.median(b):.2f}, ratio "
          f"{np.median(a)/np.median(b):.3f} (predicted 1.9643)")

    (OUT / "s11_exploratory.json").write_text(
        json.dumps(rows, indent=1, default=float), encoding="utf-8")
    print("\nwrote out/s11_exploratory.json")


if __name__ == "__main__":
    main()

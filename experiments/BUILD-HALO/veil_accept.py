"""Acceptance for the veil-envelope estimator, against ORCH's frozen bars.

Bars, unchanged since they were set:

  * TARGET  flower-bud-alone-cpl d=120-200 must beat -247 DN, which is what a
    single mid-bracket frame already achieves. Worse than one of the merge's
    own inputs on that band is failure by definition.
  * PLACEBO 109MSDCF must be ~a no-op. It has a dark subject on a bright
    backdrop but no depth separation, so a fix acting on veiling has nothing
    to do there. Movement means the operator is acting on something else.
  * GUARD   couch-fibers-cpl unchanged.
  * Rim and surround are reported SEPARATELY. They have opposite signs and a
    combined score would hide a trade.

Two traps this script is built to avoid
---------------------------------------
1. The silhouette mask is derived from the OFF merge in this same run, not
   from any `STREHL_ONLY_FRAME` render. That flag changes the stack digest, the
   alignment sidecar is rejected, and the frame becomes its own reference with
   an identity warp -- so a mask taken from one is not registered to a merge.
   Every arm here is a merge of the same stack from the same pin, so a mask
   from one is exactly registered to all of them.

2. The aura is DEFINED as a deficit relative to the image's own far field, so
   that is the reference used. But the estimator only ever raises pixels, and
   it could in principle raise the far field too -- which own-far-field
   referencing would silently hide. So the raw far-field level of every arm is
   printed before any normalisation, in the discipline of section 23.2: report
   the divisor, never just the ratio.
"""

from pathlib import Path
import sys

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

OUT = Path(r"C:\dev\strehl-out\VEIL")

# ORCH's bands, so the numbers are directly comparable to his tables.
BANDS = [(1, 4), (4, 12), (12, 16), (16, 30), (30, 60), (60, 120),
         (120, 200), (200, 300), (300, 420)]
FAR = (500, 900)
RIM = [(1, 4), (4, 12), (12, 16)]
SURROUND = [(30, 60), (60, 120), (120, 200), (200, 300)]
TARGET_BAND = (120, 200)
TARGET_BAR = -247.0


def luma(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.ndim == 3:
        out = (0.2126 * a[..., 0].astype(np.float32)
               + 0.7152 * a[..., 1].astype(np.float32)
               + 0.0722 * a[..., 2].astype(np.float32))
    else:
        out = a.astype(np.float32)
    del a
    return out


def bands_for(ref: np.ndarray):
    backdrop = float(np.median(ref))
    subject = ref < 0.5 * backdrop
    subject = binary_closing(subject, np.ones((9, 9)))
    subject = binary_opening(subject, np.ones((9, 9)))
    print(f"  backdrop {backdrop:.1f} DN, subject {100 * subject.mean():.2f}% of frame")
    dist = distance_transform_edt(~subject)
    idx = []
    for lo, hi in BANDS:
        m = (dist >= lo) & (dist < hi) & ~subject
        idx.append(np.flatnonzero(m.ravel()).astype(np.int64))
        del m
    fm = (dist >= FAR[0]) & (dist < FAR[1]) & ~subject
    far = np.flatnonzero(fm.ravel()).astype(np.int64)
    del fm, dist, subject
    return idx, far


def run(subject_name: str, arms: dict, bar: float | None, gating: bool = True) -> bool:
    print(f"\n{'=' * 78}\n{subject_name}\n{'=' * 78}")
    missing = [n for n, p in arms.items() if not p.exists()]
    if missing:
        print(f"  pending, not yet rendered: {', '.join(missing)}")
    arms = {n: p for n, p in arms.items() if p.exists()}
    if "off" not in arms:
        print("  SKIP -- no off baseline yet")
        return True
    if len(arms) < 2:
        print("  SKIP -- nothing to compare against the baseline yet")
        return True

    ref = luma(arms["off"])
    idx, far = bands_for(ref)
    if far.size == 0:
        print("  SKIP -- no far field; subject mask fills the frame")
        return True
    print(f"  far field d={FAR}: {far.size:,} px")
    del ref

    prof = {}
    for name, path in arms.items():
        img = luma(path)
        f = float(np.median(img.ravel()[far]))
        # Deficit below this image's OWN far field, which is the definition of
        # the aura. The raw level `f` is printed so a global lift cannot hide.
        p = np.array([float(np.median(img.ravel()[ix])) - f if ix.size else np.nan
                      for ix in idx])
        prof[name] = (p, f)
        del img

    print(f"\n  {'arm':>10} {'farDN':>9} " +
          " ".join(f"{f'{lo}-{hi}':>9}" for lo, hi in BANDS))
    for name, (p, f) in prof.items():
        print(f"  {name:>10} {f:9.1f} " +
              " ".join(f"{v:9.0f}" for v in p))

    def group(p, sel):
        w = [(BANDS.index(b), b) for b in sel]
        return float(np.nanmean([p[i] for i, _ in w]))

    print(f"\n  {'arm':>10} {'RIM(1-16)':>12} {'SURROUND(30-300)':>18}")
    for name, (p, _) in prof.items():
        print(f"  {name:>10} {group(p, RIM):12.0f} {group(p, SURROUND):18.0f}")

    ok = True
    if bar is not None:
        ti = BANDS.index(TARGET_BAND)
        print(f"\n  TARGET d={TARGET_BAND[0]}-{TARGET_BAND[1]}, bar better than {bar:.0f} DN")
        for name, (p, _) in prof.items():
            v = p[ti]
            verdict = "PASS" if v > bar else "fail"
            if name != "off" and v <= bar:
                ok = False
            print(f"    {name:>10} {v:9.0f} DN   {verdict}")
    else:
        base = prof["off"][0]
        label = "change vs off (expected here, reported not gated)" if not gating \
            else "no-op check: max |arm - off| across all bands"
        print(f"\n  {label}")
        for name, (p, _) in prof.items():
            if name == "off":
                continue
            d = float(np.nanmax(np.abs(p - base)))
            if not gating:
                print(f"    {name:>10} {d:9.0f} DN   (informational)")
                continue
            verdict = "PASS (no-op)" if d < 50 else "MOVED"
            if d >= 50:
                ok = False
            print(f"    {name:>10} {d:9.0f} DN   {verdict}")
    return ok


def main() -> int:
    good = True
    good &= run(
        "flower-bud-alone-cpl  -- TARGET",
        {"off": OUT / "fb-off.tif",
         "veil0.65": OUT / "fb-v0p65.tif",
         "pm-off": OUT / "fb-pm-off.tif",
         "pm-veil": OUT / "fb-pm-v0p65.tif",
         "pm-c1.5": OUT / "fb-pm-c1p5.tif",
         "pm-floor": OUT / "fb-pm-fl.tif",
         "pm-c4.0": OUT / "fb-pm-c4p0.tif"},
        TARGET_BAR,
    )
    good &= run(
        "109MSDCF  -- PLACEBO (must be a no-op)",
        {"off": OUT / "ms-pm-off.tif",
         "veilfloor": OUT / "ms-pm-fl.tif"},
        None,
    )
    good &= run(
        "couch-fibers-cpl  -- GUARD (must be unchanged)",
        {"off": OUT / "cf-pm-off.tif",
         "veil1.5": OUT / "cf-pm-c1p5.tif",
         "veilfloor": OUT / "cf-pm-fl.tif"},
        None,
    )
    good &= run(
        "bee-2-cpl  -- PORTFOLIO",
        {"off": OUT / "bee2-pm-off.tif",
         "veil1.5": OUT / "bee2-pm-c1p5.tif",
         "veilfloor": OUT / "bee2-pm-fl.tif"},
        None,
        gating=False,
    )
    print(f"\n{'=' * 78}\nOVERALL: {'PASS' if good else 'FAIL'}\n{'=' * 78}")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())

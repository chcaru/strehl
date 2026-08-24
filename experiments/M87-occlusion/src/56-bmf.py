"""M87 step 56 -- the bar the next milestone needs: Blur-Matched Fidelity (BMF).

WHY THIS EXISTS. Registered bar X4 failed: three of four DELIBERATELY BROKEN
unmixings improved the halo metric by 77-85%. So no halo-suppression number can
certify a reconstruction, alone or combined with other suppression numbers. ORCH
asks for a fidelity term "measured against truth". On synthetic scenes I have
truth and the reconstruction already passes there (band RMSE 3.46% -> 1.82%).
On the real bee there IS no truth -- you cannot photograph what is behind an
opaque subject -- and the real bee is exactly where the fix failed. A bar that
binds only where the previous attempt already succeeded cannot catch the next
failure. So this builds a fidelity term that needs NO truth.

THE IDEA. The halo is a BROAD veil (d ~ 15-40 px). The hair fringe is FINE
structure (1-4 px). A band-separated comparison can tell "removed the veil"
from "removed the hairs" -- but only if it is never band-averaged, which is
M104's discipline 643 and ORCH's explicit warning.

The instrument is a race against the maximally destructive intervention that
achieves the SAME suppression:

    BMF = fine_ratio(candidate) / fine_ratio(blur matched on the coarse band)

A Gaussian blur is tuned until it suppresses the COARSE band exactly as much as
the candidate does. Then the two are compared on the FINE band. BMF > 1 means
the candidate bought its halo suppression more cheaply than destruction did.
BMF <= 1 means it is no better than a blur, which is the X4 failure made
quantitative.

REGISTERED BARS -- WRITTEN BEFORE THE SCRIPT WAS RUN:
  V1  NO-OP region (max_delta 0, changed 0.0%): every ratio must be EXACTLY
      1.0. Any deviation means the metric manufactures signal and is void.
  V2  DAMAGE region (strongest correction, the hair fringe): the fine-band
      ratio must fall below 0.95, i.e. the instrument must SEE the damage I
      saw by eye. If it does not fire here it is useless.
  V3  BAND SEPARATION: at the damage region the coarse ratio must fall further
      than the fine ratio. If the fix removes fine structure at least as hard
      as it removes the veil, it is not a targeted correction.
  V4  BROKEN ARM, registered not appended: the coarse-matched Gaussian blur.
      BMF must be computed against it. PREDICTION: the shipped d=40 correction
      scores BMF <= 1.05 at the hair fringe -- no better than a blur -- which
      is why it cannot be defaulted ON. If BMF >> 1 my §16.9 reading was too
      harsh and I will say so.

DIM GUARD. M95 is landing native-sampling emit, which CHANGES output
dimensions. Nothing here hardcodes 7032x4688; the shapes are read, asserted
equal between arms, and recorded.

READS 16-BIT TIFF WITH tifffile, NEVER PIL -- see fact P40: PIL silently
8-bit-converts 16-bit RGB TIFFs and quantised a headline of mine tonight.
"""

import json
import pathlib

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

OUTDIR = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

BEFORE = OUTDIR / "30-SHIP-BEFORE-default.tif"
AFTER = OUTDIR / "31-SHIP-AFTER-fixhalo.tif"

# full-resolution ROIs, from data/43-ship-crops.json and data/44-detail-control.json
R_DAMAGE = (866, 1566, 1050, 2150)      # strongest correction: the hair fringe
R_NOOP = (1500, 2100, 3500, 4300)       # measured max_delta 0, changed 0.0%

# Named bands, never averaged together (discipline 643).
FINE = (1.0, 3.0)      # ~2-6 px structure: hairs, facets
COARSE = (8.0, 32.0)   # ~16-64 px structure: the halo veil

FINE_BAR = 0.95
BMF_BAR = 1.05


def luma(a):
    a = a.astype(np.float32)
    if a.ndim == 3:
        a = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return a


def band_energy(img, lo, hi):
    """RMS energy of a difference-of-Gaussians band. Named band, not averaged."""
    b = gaussian_filter(img, lo) - gaussian_filter(img, hi)
    return float(np.sqrt(np.mean(b.astype(np.float64) ** 2)))


def ratios(before, after):
    return {"fine": band_energy(after, *FINE) / band_energy(before, *FINE),
            "coarse": band_energy(after, *COARSE) / band_energy(before, *COARSE)}


def match_blur(before, target_coarse):
    """Find sigma whose coarse-band ratio equals the candidate's. Bisection."""
    lo, hi = 0.01, 64.0
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        r = band_energy(gaussian_filter(before, mid), *COARSE) / \
            band_energy(before, *COARSE)
        if r > target_coarse:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    print(f"reading {BEFORE.name} and {AFTER.name} with tifffile (never PIL)")
    b_full = tifffile.imread(BEFORE)
    a_full = tifffile.imread(AFTER)
    print(f"  BEFORE {b_full.shape} {b_full.dtype}")
    print(f"  AFTER  {a_full.shape} {a_full.dtype}")
    assert b_full.shape == a_full.shape, "DIM GUARD: arms differ in shape"
    out = {"shape": list(b_full.shape), "fine_band": FINE, "coarse_band": COARSE,
           "regions": {}}

    for tag, (y0, y1, x0, x1) in (("NOOP", R_NOOP), ("DAMAGE", R_DAMAGE)):
        bb = luma(b_full[y0:y1, x0:x1])
        aa = luma(a_full[y0:y1, x0:x1])
        d = np.abs(aa - bb)
        r = ratios(bb, aa)
        rec = {"roi": [y0, y1, x0, x1], "changed_frac": float((d > 0).mean()),
               "max_delta": float(d.max()), **r}
        print(f"\n=== {tag}  y{y0}..{y1} x{x0}..{x1} ===")
        print(f"  changed {100 * rec['changed_frac']:.2f}%  "
              f"max|delta| {rec['max_delta']:.0f}")
        print(f"  fine   band ratio {r['fine']:.6f}")
        print(f"  coarse band ratio {r['coarse']:.6f}")

        if tag == "DAMAGE":
            sig = match_blur(bb, r["coarse"])
            blur = gaussian_filter(bb, sig)
            rb = ratios(bb, blur)
            bmf = r["fine"] / rb["fine"]
            rec.update({"blur_sigma": sig, "blur_fine": rb["fine"],
                        "blur_coarse": rb["coarse"], "BMF": bmf})
            print(f"  --- V4 broken arm: coarse-matched Gaussian blur ---")
            print(f"  matched sigma      {sig:.4f} px")
            print(f"  blur coarse ratio  {rb['coarse']:.6f} "
                  f"(target {r['coarse']:.6f})")
            print(f"  blur fine ratio    {rb['fine']:.6f}")
            print(f"  BMF = fine(fix)/fine(blur) = {bmf:.4f}")
        out["regions"][tag] = rec

    n = out["regions"]["NOOP"]
    dm = out["regions"]["DAMAGE"]
    v1 = n["fine"] == 1.0 and n["coarse"] == 1.0
    v2 = dm["fine"] < FINE_BAR
    v3 = dm["coarse"] < dm["fine"]
    v4 = dm["BMF"] > BMF_BAR
    for k, ok, why in (("V1", v1, "no-op region ratios exactly 1.0"),
                       ("V2", v2, f"fine ratio < {FINE_BAR} at the damage site"),
                       ("V3", v3, "coarse falls further than fine"),
                       ("V4", v4, f"BMF > {BMF_BAR}, better than a matched blur")):
        print(f"\n{k}  {'PASS' if ok else 'FAIL'}  -- {why}")
    out["bars"] = {"V1": bool(v1), "V2": bool(v2), "V3": bool(v3), "V4": bool(v4)}
    json.dump(out, open(DATA / "56-bmf.json", "w"), indent=1)
    print(f"\nwrote {DATA / '56-bmf.json'}")


if __name__ == "__main__":
    main()

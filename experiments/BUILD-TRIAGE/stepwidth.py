"""How many captured frames actually see each site in focus?

THE QUESTION.  `119MSDCF` resolves sharply in its source frames -- rel 0.15, in
`bee-3-cpl`'s range -- yet the merge is 26th of 26 by normalised detail and my
site comparison put it at x0.987, the corpus's lowest.  Sharp sources plus a
merge that tracks them plus a soft result is only consistent if the sharpness is
sampled too sparsely: if the focus peak is narrower than the spacing between
captured frames, then every part of the subject whose depth falls BETWEEN two
frames was never photographed in focus by any of them.  No merge can recover
that, and it is a different advisory from "the sweep stopped short".

THE MEASUREMENT.  Full width at half maximum of the through-focus curve, taken
above the noise floor and expressed in REAL CAPTURE STEPS -- not in samples.
sitescan subsamples long stacks, so a width of 3 samples on a 299-frame stack
read at stride 5 is 15 real frames.  Converting through `sampled` is the whole
point; comparing a subsampled width against a fully-sampled one would be this
project's recurring error again.

READING IT.  FWHM is the number of captured frames that hold this site in focus.
Below ~2 the sweep undersamples its own depth of field and detail at intermediate
depths is lost at capture.  Comfortably above it, the sampling is adequate and
softness must be explained by something else.

LIMITATION.  FWHM is measured on the frames that WERE captured, so it can only
report that the step is too coarse -- it cannot say what step would have been
right without knowing the physical focus increment, which is not in the EXIF I
have.  The advisory it supports is "finer steps", quantified as a ratio, not an
absolute millimetre figure.
"""
import glob
import json
import os
import sys

import numpy as np

OUT = r"C:\dev\strehl-out\BUILD-TRIAGE\sitescan"

# Below this many captured frames across the focus peak, the sweep is sampling
# its own depth of field more coarsely than the peak it is trying to find, so a
# site at an intermediate depth has no sharp frame.  Two is the Nyquist-flavoured
# minimum: fewer than two samples across a feature cannot locate it.
UNDERSAMPLED_FWHM = 2.0


def fwhm(x: np.ndarray, y: np.ndarray, floor: float) -> tuple[float, bool]:
    """Width in x-units at half height above `floor`; flag if truncated."""
    pk = int(np.argmax(y))
    top = y[pk] - floor
    if top <= 0:
        return float("nan"), True
    half = floor + 0.5 * top

    def cross(lo: int, hi: int, step: int) -> tuple[float, bool]:
        i = pk
        while 0 <= i + step < len(y) and lo <= i + step <= hi:
            j = i + step
            if y[j] <= half:                       # interpolate the crossing
                t = (y[i] - half) / max(y[i] - y[j], 1e-12)
                return float(x[i] + t * (x[j] - x[i])), False
            i = j
        return float(x[0] if step < 0 else x[-1]), True   # never fell to half

    xl, tl = cross(0, len(y) - 1, -1)
    xr, tr = cross(0, len(y) - 1, +1)
    return xr - xl, (tl or tr)


def commission() -> None:
    """A planted width it must recover, and a null it must refuse."""
    x = np.arange(60, dtype=float)
    # PLANT: Gaussian of known sigma -> FWHM = 2*sqrt(2*ln2)*sigma = 2.3548*sigma
    for sigma in (1.5, 4.0, 9.0):
        y = np.exp(-((x - 30.0) ** 2) / (2 * sigma * sigma))
        w, trunc = fwhm(x, y, 0.0)
        want = 2.3548 * sigma
        assert not trunc, f"C1: planted sigma={sigma} reported truncated"
        assert abs(w - want) / want < 0.05, \
            f"C1 width: sigma={sigma} -> FWHM {w:.2f}, expected {want:.2f}"
    # PLANT: the stride conversion must matter.  Same Gaussian read at stride 5
    # must give the SAME width in real frames, not one fifth of it.
    xs, ys = x[::5], np.exp(-((x[::5] - 30.0) ** 2) / (2 * 4.0 * 4.0))
    ws, _ = fwhm(xs, ys, 0.0)
    assert abs(ws - 2.3548 * 4.0) / (2.3548 * 4.0) < 0.12, \
        f"C2 stride: subsampled FWHM {ws:.2f} != full-rate {2.3548 * 4.0:.2f}"
    # NULL: a flat curve has no peak to measure and must be flagged truncated.
    _, tflat = fwhm(x, np.ones_like(x), 0.0)
    assert tflat, "C3 null: flat curve reported a finite FWHM"
    # NULL: a monotone ramp (peak at an end) must be flagged truncated.
    _, tramp = fwhm(x, x / x.max(), 0.0)
    assert tramp, "C4 null: monotone ramp reported a finite FWHM"
    print("commissioning OK  (3 planted widths recovered <5%, stride-invariant "
          "<12%, flat and ramp nulls both refused)")


def main() -> int:
    commission()
    pats = sys.argv[1:] or ["*.json"]
    rows = []
    skipped = []
    for pat in pats:
        for p in sorted(glob.glob(os.path.join(OUT, pat))):
            d = json.load(open(p))
            samp = np.asarray(d["sampled"], dtype=float)
            n = int(d["n_frames"])
            stride = float(np.median(np.diff(samp))) if len(samp) > 1 else 1.0
            for s in d["sites"]:
                if "curve_rel" not in s:     # written before the curve was stored
                    skipped.append(f"{d['subject']}/{s['label']}")
                    continue
                y = np.asarray(s["curve_rel"], dtype=float)
                w, trunc = fwhm(samp, y, float(d["hf_floor_rel"]))
                rows.append({
                    "subject": d["subject"], "site": s["label"], "n": n,
                    "stride": stride, "fwhm": w, "trunc": trunc,
                    "best": s["best_frame"], "rel": s["hf_max_rel"],
                })
    print(f"\n{'subject':<38} {'site':<18} {'N':>4} {'str':>4} "
          f"{'best':>5} {'rel':>7} {'FWHM':>7}  verdict")
    print("-" * 104)
    for r in sorted(rows, key=lambda r: (np.isnan(r["fwhm"]), r["fwhm"])):
        if r["trunc"] or np.isnan(r["fwhm"]):
            v = "peak not bracketed - no width"
        elif r["fwhm"] < UNDERSAMPLED_FWHM:
            v = "UNDERSAMPLED - step too coarse"
        else:
            v = "sampling adequate"
        print(f"{r['subject']:<38} {r['site']:<18} {r['n']:>4} "
              f"{r['stride']:>4.0f} {r['best']:>5} {r['rel']:>7.4f} "
              f"{r['fwhm']:>7.2f}  {v}")
    print(f"\nFWHM is in REAL captured frames (samples x stride), so it is "
          f"comparable across\nstacks of different length. Threshold "
          f"{UNDERSAMPLED_FWHM} frames across the peak.")
    if skipped:
        print(f"\nSKIPPED {len(skipped)} site(s) whose JSON predates curve "
              f"storage (re-run sitescan to include):")
        for s in skipped:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Decompose strehl's focus measure into its low- and high-frequency parts.

WHY. The first ladder's two scalars both peaked at f112 in the pale-wash ROI, but
the contact sheet plainly shows real surface texture at f32-f48 and a featureless
pale gradient from f104 on. When a number and a picture disagree the picture is
right, so the question becomes: what is the number measuring? Both my metrics and
strehl's own focus measure are gradient aggregates, and a gradient aggregate
cannot tell a fine sharp texture from a smooth steep ramp.

THE REPLICA. From the pinned source at 1cacb61:
  focus.rs  gradient_magnitude : Sobel, both kernels scaled by 0.125, magnitude
  focus.rs  box_mean           : mean over a (2r+1)^2 box, r = WINDOW_RADIUS = 13
  focus.rs  normalise_by_luma_sigma : divide by noise.green_luma_sigma(luma)
  noise.rs  green_luma_sigma(s) = sqrt(0.25 * 2 * (g*s + (r*g)^2)), g = 0.229 DN/e-,
                                  r = 1.47 e-, s black-subtracted
all on the *plane* grid, which is the raw green plane at half the output
resolution in each axis. I approximate luma = (G1+G2)/2 by 2x2-binning the green
channel of the linear demosaiced output. That is a replica, not the operator, so
it MUST be commissioned before anything is concluded from it.

COMMISSIONING. argmax over frames of the replica must land on the index the
shipped binary actually elected at that ROI, read from the election map. Four
ROIs are checked, spanning elected indices 22 to 133. A replica that cannot
reproduce the shipped election explains nothing about the shipped election, and
if that is the outcome this script prints it and the analysis stops.

THE DECOMPOSITION. Split luma into low = gaussian(L, LOW_SIGMA) and high = L - low,
then run the identical pipeline on each. The divisor is taken from the FULL luma
in all three cases, exactly as strehl does, so the three curves differ only in
which spatial frequencies reach the gradient operator.

CONTROLS. dark-patch and subject-sharp are regions where the shipped election is
correct by eye. If the split is real, full and high agree there and disagree only
at pale-wash. A split that appears everywhere is an artifact of the split.
"""
import argparse
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, uniform_filter

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
PICS = OUT / "pics"

WINDOW_RADIUS = 13          # focus.rs
LOW_SIGMA = 8.0             # plane px; the veil/ramp scale
MEASURE_HALF = 60           # plane px, the region the medians are taken over

GAIN_DN_PER_E = 0.229       # focus.rs test model, matches the shipped profile
READ_E = 1.47
# black-subtracted raw DN -> linear 16-bit output DN. levels black 512 white
# 15360 from the render log, so the raw range 14848 maps onto 65535.
K_OUT = 65535.0 / (15360.0 - 512.0)

# Elected index read from B-noalign-elect.tif, the align-off render these ladder
# frames share a frame of reference with: (median, p5, p95) over the ROI.
#
# The band is the honest target. An ROI is 120x120 plane px and elects a spread of
# indices, not one; and the replica works on the demosaiced green rather than the
# raw CFA green and omits the edge-aware layer support, so frame-exact agreement
# was never on offer. Scoring the argmax against the median alone is too strict and
# would fail a replica that is in fact electing the same mode. Both scorings are
# printed so the stricter one cannot be quietly dropped.
ELECTED = {"pale-wash": (133, 110, 156), "leaf-infocus": (37, 34, 40),
           "dark-patch": (22, 21, 46), "subject-sharp": (66, 36, 74)}


def sobel_mag(a):
    """focus.rs gradient_magnitude, including its 0.125 scaling and edge clamp."""
    p = np.pad(a, 1, mode="edge")
    gx = (p[:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[1:-1, :-2] - p[2:, :-2]) * 0.125
    gy = (p[2:, :-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[:-2, 1:-1] - p[:-2, 2:]) * 0.125
    return np.hypot(gx, gy)


def luma_sigma(luma_out_dn):
    """noise.rs green_luma_sigma, carried to the output DN scale by K_OUT."""
    s = np.maximum(luma_out_dn, 0.0) / K_OUT
    read_dn = READ_E * GAIN_DN_PER_E
    var_single = GAIN_DN_PER_E * s + read_dn * read_dn
    return np.sqrt(0.5 * var_single) * K_OUT


def focus_of(grad_src, luma_full, normalise):
    f = uniform_filter(sobel_mag(grad_src), size=2 * WINDOW_RADIUS + 1, mode="nearest")
    if normalise:
        f = f / np.maximum(luma_sigma(luma_full), 1e-6)
    return f


def centre(a):
    c = a.shape[0] // 2
    return a[c - MEASURE_HALF:c + MEASURE_HALF, c - MEASURE_HALF:c + MEASURE_HALF]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="crops")
    ap.add_argument("--normalise", type=int, default=1)
    args = ap.parse_args()

    src = OUT / f"ladder-{args.tag}"
    files = sorted(src.glob("f*.npz"))
    if not files:
        raise SystemExit(f"no frames in {src}")
    frames = [int(f.stem[1:]) for f in files]
    names = list(np.load(files[0]).keys())

    curves = {n: {"full": [], "low": [], "high": []} for n in names}
    for f in files:
        z = np.load(f)
        for n in names:
            rgb = z[n].astype(np.float64)
            g = rgb[:, :, 1]
            L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
            low = gaussian_filter(L, LOW_SIGMA, mode="nearest")
            parts = {"full": L, "low": low, "high": L - low}
            for k, v in parts.items():
                curves[n][k].append(float(np.median(centre(
                    focus_of(v, L, bool(args.normalise))))))
        print(f"  {f.stem} done")

    print(f"\n{'=' * 78}\nCOMMISSIONING: replica argmax vs the index the binary elected"
          f"\n{'=' * 78}")
    ok = strict = 0
    for n in names:
        a = frames[int(np.argmax(curves[n]["full"]))]
        e, lo, hi = ELECTED[n]
        in_band = lo <= a <= hi          # elects the same mode as the binary
        near_median = abs(a - e) <= 8    # stricter: within one ladder step
        ok += in_band
        strict += near_median
        print(f"  {n:<15} replica argmax f{a:<4} shipped elected f{e:<4} "
              f"band [{lo:>3},{hi:>3}]  band {'HIT ' if in_band else 'MISS'}"
              f"  median {'HIT' if near_median else 'MISS'}")
    print(f"  -> band {ok}/{len(names)}   median {strict}/{len(names)}")
    if ok < 3:
        print("\n  REPLICA NOT COMMISSIONED. It does not reproduce the shipped\n"
              "  election, so its decomposition says nothing about the shipped\n"
              "  election. Reporting this and stopping.")

    print(f"\n{'=' * 78}\nDECOMPOSITION (normalise={args.normalise})\n{'=' * 78}")
    summary = {}
    for n in names:
        af = frames[int(np.argmax(curves[n]["full"]))]
        ah = frames[int(np.argmax(curves[n]["high"]))]
        al = frames[int(np.argmax(curves[n]["low"]))]
        summary[n] = {"full": af, "high": ah, "low": al, "elected": ELECTED[n][0]}
        tag = "SPLIT" if abs(af - ah) > 16 else "agree"
        print(f"  {n:<15} argmax  full f{af:<4} high f{ah:<4} low f{al:<4}   {tag}")

    print(f"\n{'-' * 78}\nper-frame, pale-wash (the defect)\n{'-' * 78}")
    print(f"  {'frame':>6} {'full':>10} {'high':>10} {'low':>10}  {'high share':>10}")
    for i, k in enumerate(frames):
        fu, hi, lo = (curves["pale-wash"][t][i] for t in ("full", "high", "low"))
        print(f"  {k:>6} {fu:>10.4f} {hi:>10.4f} {lo:>10.4f}  {hi / max(fu, 1e-9):>9.1%}")

    fig, axes = plt.subplots(1, len(names), figsize=(5.2 * len(names), 4.2))
    for ax, n in zip(np.atleast_1d(axes), names):
        for k, c in (("full", "k"), ("high", "tab:red"), ("low", "tab:blue")):
            v = np.array(curves[n][k])
            ax.plot(frames, v / v.max(), c, label=k, lw=1.8)
        ax.axvline(ELECTED[n][0], color="tab:green", ls="--", lw=1.4, label="elected")
        ax.set_title(f"{n}\nfull argmax f{summary[n]['full']}  "
                     f"high argmax f{summary[n]['high']}")
        ax.set_xlabel("frame"); ax.set_ylabel("focus measure (norm.)")
        ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.suptitle("strehl focus measure split into low- and high-frequency parts "
                 "(replica of focus.rs, r=13, /green_luma_sigma)")
    fig.tight_layout()
    p = PICS / f"decomp-{args.tag}-n{args.normalise}.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    print(f"\nwrote {p}")

    (OUT / f"decomp-{args.tag}-n{args.normalise}.json").write_text(json.dumps(
        {"frames": frames, "curves": curves, "summary": summary}, indent=1))


if __name__ == "__main__":
    main()

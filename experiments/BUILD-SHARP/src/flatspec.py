"""Measure the merged noise spectrum on FLAT BACKGROUND WINDOWS only.

Why this is not the same script as halfspec.py
----------------------------------------------
halfspec.py differenced two disjoint-half merges over the whole frame and the
result was not noise: it was a legible photograph of the bee -- every hair, and the
eye's ommatidia lattice beating as moire against a sub-pixel registration
difference between the two arms.  Two mechanisms put signal into that difference:

  * the two halves ELECT different winner frames, and adjacent focus steps differ
    in content wherever there is fine detail;
  * the two half-merges are not registered to each other to better than a pixel (an
    integer offset of 1 px was measured and removed; a sub-pixel residual remains,
    and it is what makes the ommatidia visible).

Both vanish where the scene is FLAT: a defocused background has no fine detail to
elect differently and nothing for a sub-pixel shift to move.  So the estimator is
sound, but only on flat windows, and this script restricts it to them.

The honest limitation, stated up front
--------------------------------------
The gate admits more frames where the scene is flat (n_eff is large) and collapses
towards a single frame at high-contrast detail.  Noise therefore rises where detail
is.  A background-only measurement is a measurement of the noise floor in the
region of MAXIMUM averaging, so it is a LOWER BOUND on the noise elsewhere in the
frame.  It is exactly the right quantity for the Wiener denominator in flat and
mid-tone regions, and it understates the noise at detail.

Windows are chosen using ONLY the full merge, never the two arms under test, so the
choice of where to look cannot be influenced by the thing being measured.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from halfspec import load, integer_offset, radial_power  # noqa: E402


def gradient_energy(g: np.ndarray) -> np.ndarray:
    gy = np.diff(g, axis=0, prepend=g[:1])
    gx = np.diff(g, axis=1, prepend=g[:, :1])
    return gy * gy + gx * gx


def pick_flat_windows(full: np.ndarray, tile: int, n_want: int,
                      min_level: float) -> list[tuple[int, int]]:
    """Lowest-gradient, adequately-bright, non-overlapping windows of the full merge."""
    g = full.mean(axis=2)
    e = gradient_energy(g)
    h, w = g.shape
    cands = []
    step = tile // 2
    for y in range(0, h - tile + 1, step):
        for x in range(0, w - tile + 1, step):
            blk = g[y:y + tile, x:x + tile]
            lvl = float(blk.mean())
            if lvl < min_level:
                continue
            # Rank on a high PERCENTILE of gradient energy, not the mean.  A
            # defocused but hairy region averages low while still containing the
            # strong edges whose election differs between halves -- that is how the
            # first version of this picker admitted four windows full of legible
            # hairs and ommatidia.  The percentile rejects a window for its worst
            # content rather than its typical content.
            sc = float(np.percentile(e[y:y + tile, x:x + tile], 95))
            cands.append((sc, y, x, lvl))
    cands.sort()
    chosen: list[tuple[int, int]] = []
    for _, y, x, _lvl in cands:
        if all(abs(y - cy) >= tile and abs(x - cx) >= tile for cy, cx in chosen):
            chosen.append((y, x))
        if len(chosen) >= n_want:
            break
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--full", required=True)
    ap.add_argument("--scale", type=float, default=4.0,
                    help="P_full = P_D / scale (4 for halves, 8 for quarters)")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--windows", type=int, default=12)
    ap.add_argument("--min-level", type=float, default=2000.0)
    ap.add_argument("--quantile", type=float, default=25.0,
                    help="per-frequency quantile across windows; contamination is "
                         "one-sided, so a LOW quantile is the unbiased noise floor")
    ap.add_argument("--out", required=True)
    ap.add_argument("--picture", help="PNG of the difference in the chosen windows")
    args = ap.parse_args()

    a, b, full = load(args.a), load(args.b), load(args.full)
    h = min(a.shape[0], b.shape[0], full.shape[0])
    w = min(a.shape[1], b.shape[1], full.shape[1])
    a, b, full = a[:h, :w], b[:h, :w], full[:h, :w]

    dy, dx, _ = integer_offset(a, b)
    pad = 16
    a2 = a[pad:h - pad, pad:w - pad]
    b2 = b[pad + dy:h - pad + dy, pad + dx:w - pad + dx]
    f2 = full[pad:h - pad, pad:w - pad]
    d = a2 - b2

    wins = pick_flat_windows(f2, args.tile, args.windows, args.min_level)
    rep = {"a": args.a, "b": args.b, "full": args.full, "scale": args.scale,
           "tile": args.tile, "offset": [dy, dx], "windows": wins}
    if not wins:
        raise SystemExit("no flat windows found; lower --min-level")

    names = ["R", "G", "B"]
    rep["channels"] = {}
    print(f"offset dy={dy} dx={dx};  {len(wins)} flat windows of {args.tile}px")
    for ci, cn in enumerate(names):
        pn_all, pi_all, fr = [], [], None
        for (y, x) in wins:
            fr, p, _ = radial_power(d[y:y + args.tile, x:x + args.tile, ci],
                                    tile=args.tile)
            _, pi, _ = radial_power(f2[y:y + args.tile, x:x + args.tile, ci],
                                    tile=args.tile)
            pn_all.append(p)
            pi_all.append(pi)
        # Signal contamination is STRICTLY ADDITIVE: where the two halves elect
        # different frames, or a sub-pixel registration residual moves an edge, the
        # difference gains power.  Nothing in this measurement can make a window
        # read LOWER than its true noise.  So the lower envelope across many
        # windows is the unbiased estimate of the noise floor, and it does not
        # depend on a window picker being perfect.  A per-frequency low quantile is
        # used rather than the strict minimum so that one anomalously quiet window
        # cannot set the level on its own.
        pn = np.percentile(np.array(pn_all), args.quantile, axis=0) / args.scale
        pi = np.median(np.array(pi_all), axis=0)
        rep["channels"][cn] = {
            "freq": fr.tolist(),
            "p_noise_full": pn.tolist(),
            "p_image": pi.tolist(),
            "p_signal": np.maximum(pi - pn, 0.0).tolist(),
            "noise_fraction": (pn / np.maximum(pi, 1e-30)).tolist(),
        }
    rep["quantile"] = args.quantile

    # Per-window difference SD, to expose any window that is not actually flat.
    sds = [float(d[y:y + args.tile, x:x + args.tile].std()) for (y, x) in wins]
    rep["window_diff_sd"] = sds
    print("per-window difference sd (DN): " +
          ", ".join(f"{s:.0f}" for s in sds))
    print(f"  median {np.median(sds):.1f}   max/median "
          f"{max(sds)/np.median(sds):.2f}")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)

    g = rep["channels"]["G"]
    print("\n  f (cyc/px)   P_noise(full)      P_image     noise frac")
    fr = g["freq"]
    for i in range(0, len(fr), max(1, len(fr) // 14)):
        print(f"  {fr[i]:8.4f}   {g['p_noise_full'][i]:13.4g}  "
              f"{g['p_image'][i]:13.4g}   {g['noise_fraction'][i]:8.4f}")

    if args.picture:
        from PIL import Image
        t = args.tile
        cols = min(4, len(wins))
        rows = (len(wins) + cols - 1) // cols
        sd = float(np.median(sds))
        canvas = np.zeros((rows * t, cols * t, 3))
        for k, (y, x) in enumerate(wins):
            r, c = divmod(k, cols)
            canvas[r * t:(r + 1) * t, c * t:(c + 1) * t] = \
                d[y:y + t, x:x + t]
        vis = np.clip(canvas / (6 * sd) + 0.5, 0, 1)
        Image.fromarray((vis * 255).astype(np.uint8)).save(args.picture)
        print(f"\nwrote {args.picture}  (+/-{3*sd:.0f} DN full scale)")


if __name__ == "__main__":
    main()


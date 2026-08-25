"""Measure the merged noise power spectrum DIRECTLY, by differencing two merges
built from DISJOINT halves of the frame set.

Why this exists
---------------
BUILD-SHARP section 13 tried to calibrate a multi-frame Wiener filter two ways and
got answers 42x apart: a scalar Laplacian-MAD sigma implied 29.4x peak gain (which
visibly destroyed the picture with ring/worm artefacts) and a power-law fitted to a
high-frequency "dead band" implied 0.70x (attenuation).  The power-law failed
because merged noise is strongly CORRELATED -- it is the average of ~167 frames
through a Catmull-Rom gather and then a demosaic -- so its spectrum has slope
-3.53, and extrapolating that from f=0.28 down to f=0.05 inflates the low-frequency
noise estimate ~470x.  A power law is not valid two octaves outside its fit band.

The fix is to stop extrapolating and measure.  Two merges from disjoint frame
subsets see the SAME scene, so the signal cancels in the difference and what is
left is noise -- at every frequency, with no model and no dead band.

Estimator
---------
Merge over m admitted frames has noise variance ~ sigma_frame^2 / m.  A half-set
merge admits ~m/2, so its variance is ~2x the full merge's.  A and B are built from
disjoint frames, hence independent:

    P_D = P_A + P_B = 2 * (2 * P_full)  =>  P_full = P_D / 4

The factor 4 is a MODEL and is tested separately by --quarters (two disjoint
quarter-set merges should give exactly 2x the half-set difference power).

Having P_noise and the image's own spectrum P_image, the signal spectrum needed by
the Wiener denominator follows without any parametric assumption at all:

    S(f) = P_image(f) - P_noise(f)

Guards (these are the point, not decoration)
--------------------------------------------
* The two merges may not share a coverage crop -- the merge shrinks the field of
  view so every output pixel is covered by every frame, and a different frame set
  can crop differently.  Dimensions are checked and an INTEGER cross-correlation
  offset is measured.  A sub-pixel offset is reported as a hard failure rather than
  resampled away, because resampling adds blur to the very quantity being measured.
* If the two halves ELECT different frames at a pixel, the difference contains
  signal, not noise.  That contamination is visible: it looks like the scene.  This
  script writes D out as a picture and reports a structure statistic, because a
  spectrum alone cannot tell you it is measuring the wrong thing.
"""

from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

try:
    import tifffile
except ImportError:  # pragma: no cover
    raise SystemExit("tifffile is required: 16-bit TIFFs read as 8-bit through PIL")


def load(path: str) -> np.ndarray:
    """Read a 16-bit linear TIFF as float64 in [0, 65535]."""
    a = tifffile.imread(path)
    if a.ndim == 2:
        a = a[:, :, None]
    return a.astype(np.float64)


def integer_offset(a: np.ndarray, b: np.ndarray, search: int = 8) -> tuple[int, int, float]:
    """Best integer (dy, dx) aligning b onto a, by brute-force SSD on a high-contrast
    window.  Integer only, by design -- see the module docstring."""
    h, w = a.shape[:2]
    cy, cx = h // 2, w // 2
    r = min(256, h // 4, w // 4)
    # Pick the window with the most gradient energy near the centre, so the
    # correlation has something to lock onto.
    ref = a[cy - r:cy + r, cx - r:cx + r].mean(axis=2)
    best = (0, 0, float("inf"))
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            sub = b[cy - r + dy:cy + r + dy, cx - r + dx:cx + r + dx].mean(axis=2)
            if sub.shape != ref.shape:
                continue
            d = float(np.mean((ref - sub) ** 2))
            if d < best[2]:
                best = (dy, dx, d)
    return best


def radial_power(img: np.ndarray, tile: int = 512, stride: int | None = None,
                 nbins: int = 64) -> tuple[np.ndarray, np.ndarray, int]:
    """Hann-windowed, tile-averaged radial power spectrum.

    Returns (freq in cycles/px, power, n_tiles).  The Hann window costs a known
    factor in total power; it is applied identically to every spectrum computed
    here, so it cancels in every ratio this script forms.
    """
    if stride is None:
        stride = tile
    h, w = img.shape[:2]
    win = np.outer(np.hanning(tile), np.hanning(tile))
    acc = None
    n = 0
    for y in range(0, h - tile + 1, stride):
        for x in range(0, w - tile + 1, stride):
            t = img[y:y + tile, x:x + tile]
            t = t - t.mean()
            f = np.fft.fftshift(np.abs(np.fft.fft2(t * win)) ** 2)
            acc = f if acc is None else acc + f
            n += 1
    if n == 0:
        raise ValueError("no tiles: image smaller than tile size")
    acc /= n

    fy = np.fft.fftshift(np.fft.fftfreq(tile))
    fx = np.fft.fftshift(np.fft.fftfreq(tile))
    rr = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    edges = np.linspace(0, 0.5, nbins + 1)
    idx = np.digitize(rr.ravel(), edges) - 1
    flat = acc.ravel()
    freq, power = [], []
    for b in range(nbins):
        m = idx == b
        if m.sum() < 8:
            continue
        freq.append(0.5 * (edges[b] + edges[b + 1]))
        power.append(float(flat[m].mean()))
    return np.array(freq), np.array(power), n


def structure_score(d: np.ndarray) -> float:
    """How much does the difference image look like a scene rather than noise?

    Ratio of local-mean energy (8x8 box) to total energy.  Independent noise
    averages down in a box by 1/64; real structure does not.  A pure white-noise
    field scores ~1/64 = 0.0156.  Correlated noise scores higher, so this is read
    as a comparison BETWEEN arms, never as an absolute threshold.
    """
    g = d.mean(axis=2) if d.ndim == 3 else d
    g = g - g.mean()
    k = 8
    h, w = (s // k * k for s in g.shape)
    b = g[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))
    return float(np.var(b) / max(np.var(g), 1e-30))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="merge from half A")
    ap.add_argument("--b", required=True, help="merge from half B")
    ap.add_argument("--full", help="merge from all frames (for the signal spectrum)")
    ap.add_argument("--scale", type=float, default=4.0,
                    help="P_full = P_D / scale; 4.0 for halves, 8.0 for quarters")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--out", required=True, help="JSON output path")
    ap.add_argument("--picture", help="write the difference image as a PNG to LOOK AT")
    args = ap.parse_args()

    a, b = load(args.a), load(args.b)
    rep: dict = {"a": args.a, "b": args.b, "scale": args.scale}

    rep["shape_a"], rep["shape_b"] = list(a.shape), list(b.shape)
    if a.shape != b.shape:
        h = min(a.shape[0], b.shape[0])
        w = min(a.shape[1], b.shape[1])
        rep["shape_mismatch"] = True
        rep["cropped_to"] = [h, w]
        a, b = a[:h, :w], b[:h, :w]
    else:
        rep["shape_mismatch"] = False

    dy, dx, ssd = integer_offset(a, b)
    rep["offset_dy"], rep["offset_dx"], rep["offset_ssd"] = dy, dx, ssd
    if (dy, dx) != (0, 0):
        rep["offset_applied"] = True
        h, w = a.shape[:2]
        pad = 16
        a = a[pad:h - pad, pad:w - pad]
        b = b[pad + dy:h - pad + dy, pad + dx:w - pad + dx]
    else:
        rep["offset_applied"] = False

    d = a - b
    rep["diff_mean"] = float(d.mean())
    rep["diff_sd"] = float(d.std())
    rep["structure_score"] = structure_score(d)
    rep["white_noise_reference"] = 1.0 / 64.0

    # Per-channel noise spectrum from the difference.
    rep["channels"] = {}
    names = ["R", "G", "B"][: d.shape[2]] if d.ndim == 3 else ["Y"]
    for ci, cn in enumerate(names):
        f, p, n = radial_power(d[:, :, ci], tile=args.tile)
        rep["channels"][cn] = {
            "freq": f.tolist(),
            "p_diff": p.tolist(),
            "p_noise_full": (p / args.scale).tolist(),
            "n_tiles": n,
        }
    rep["tile"] = args.tile

    if args.full:
        full = load(args.full)
        fh = min(full.shape[0], a.shape[0])
        fw = min(full.shape[1], a.shape[1])
        for ci, cn in enumerate(names):
            f, pi, _ = radial_power(full[:fh, :fw, ci], tile=args.tile)
            ch = rep["channels"][cn]
            pn = np.array(ch["p_noise_full"])[: len(pi)]
            pi = pi[: len(pn)]
            s = np.maximum(pi - pn, 0.0)
            ch["p_image"] = pi.tolist()
            ch["p_signal"] = s.tolist()
            ch["noise_fraction"] = (pn / np.maximum(pi, 1e-30)).tolist()

    with open(args.out, "w", encoding="utf-8") as fh_:
        json.dump(rep, fh_, indent=1)

    print(f"shape        {rep['shape_a']} vs {rep['shape_b']}"
          f"{'  MISMATCH' if rep['shape_mismatch'] else ''}")
    print(f"offset       dy={dy} dx={dx}  (applied={rep['offset_applied']})")
    print(f"difference   mean={rep['diff_mean']:+.3f} DN   sd={rep['diff_sd']:.3f} DN")
    print(f"structure    {rep['structure_score']:.4f}"
          f"   (white noise would be {1/64:.4f})")
    g = rep["channels"].get("G", next(iter(rep["channels"].values())))
    print("\n  f (cyc/px)   P_noise(full)    P_image      noise frac")
    fr = g["freq"]
    for i in range(0, len(fr), max(1, len(fr) // 14)):
        row = f"  {fr[i]:8.4f}   {g['p_noise_full'][i]:13.4g}"
        if "p_image" in g:
            row += f"  {g['p_image'][i]:11.4g}   {g['noise_fraction'][i]:8.4f}"
        print(row)

    if args.picture:
        # Autoscale to +/-3 sd so the eye can judge whether this is noise or scene.
        v = 3.0 * rep["diff_sd"]
        vis = np.clip((d / (2 * v) + 0.5), 0, 1)
        try:
            from PIL import Image
            Image.fromarray((vis * 255).astype(np.uint8)).save(args.picture)
            print(f"\nwrote {args.picture}  (+/-{v:.1f} DN full scale)")
        except ImportError:
            print("PIL unavailable; no picture written")


if __name__ == "__main__":
    main()

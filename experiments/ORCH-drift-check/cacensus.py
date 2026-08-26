#!/usr/bin/env python3
"""Corpus-wide A/B census of an edge-chroma change, with a built-in placebo.

This exists to answer "does the win generalise", which is a different question
from "is the win real on the subject I tuned it on".

Two design rules it obeys, both learned the hard way in this project:

  * **Pixel selection is made on the ARM MEAN, never on either arm.**  If the
    edge set is chosen on arm A, arm A picks its own ground and the comparison
    is rigged.  The mean is neutral between them.
  * **The flat set is the placebo and is reported next to the signal.**  A
    radial per-channel warp must be a near-no-op where there is no edge.  If
    the flat set moves as much as the edge set, the number is not measuring
    fringe removal and must not be read as if it were.  A placebo that moves is
    a result about the instrument, so it is printed on every row, not
    aggregated away.
  * **The flat set is selected by an ABSOLUTE gradient threshold, not a
    percentile.**  This is the correction to the instrument's first version and
    it matters: a percentile selects the bottom 50% of pixels whether or not a
    single one of them is flat.  On an all-texture subject -- woven fabric, a
    frost dendrite covering the frame, a ruler face -- the "flat" half is fine
    texture, the placebo is measuring real edges, and it reports a large
    excursion that looks exactly like a failed comparison.  Measured: with the
    percentile rule the placebo read 0.6497 on `flat-on-ruler-cpl` and 0.7482 on
    `113MSDCF` while reading 0.9999 on `109MSDCF`, and the split correlated
    perfectly with whether the subject has any genuinely flat area.  So each row
    now reports the FRACTION of the frame that cleared the absolute threshold,
    and a row that cannot find enough flat pixels prints NO-FLAT-SET rather than
    a placebo number nobody should trust.

Both arms must be the same subject rendered with the same binary and the same
flags, differing in exactly one thing.

Usage:
    python cacensus.py <dirA> <dirB> [--edge-pct 99] [--flat-pct 50]
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import tifffile


def load(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16 TIFF, got {a.dtype} for {path}"
    return a.astype(np.float32) / 65535.0


def grad(g: np.ndarray) -> np.ndarray:
    gy = np.zeros_like(g)
    gx = np.zeros_like(g)
    gy[:-1, :] = np.abs(np.diff(g, axis=0))
    gx[:, :-1] = np.abs(np.diff(g, axis=1))
    return gy + gx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dira")
    ap.add_argument("dirb")
    ap.add_argument("--edge-pct", type=float, default=99.0)
    ap.add_argument("--flat-abs", type=float, default=0.002,
                    help="absolute |grad| below which a pixel counts as flat "
                         "(sRGB units, sum of |dy|+|dx|)")
    ap.add_argument("--min-flat", type=float, default=0.02,
                    help="minimum fraction of the frame that must clear "
                         "--flat-abs before a placebo verdict is printed")
    args = ap.parse_args()

    names = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(args.dira, "*.tif*"))
    )

    print(f"A = {args.dira}")
    print(f"B = {args.dirb}")
    print(f"edge = top {100 - args.edge_pct:g}% of |grad| on the ARM MEAN; "
          f"flat = |grad| < {args.flat_abs:g} ABSOLUTE (placebo), "
          f"needs >= {args.min_flat:.0%} of frame\n")
    hdr = (f"{'subject':<38s} {'edge R-G':>9s} {'edge R-B':>9s} {'edge B-G':>9s}"
           f" | {'flat%':>6s} {'flat R-G':>9s} {'flat R-B':>9s} {'flat B-G':>9s}"
           f" {'struct':>8s} {'R-G corr':>9s}")
    print(hdr)
    print("-" * len(hdr))

    rows: list[tuple[str, list[float], list[float]]] = []
    corrs: list[list[float]] = []
    structs: list[float] = []
    eraw: list[list[float]] = []
    noflat: list[str] = []
    missing = 0
    for n in names:
        pb = os.path.join(args.dirb, n + ".tiff")
        if not os.path.exists(pb):
            missing += 1
            continue
        A, B = load(os.path.join(args.dira, n + ".tiff")), load(pb)
        if A.shape != B.shape:
            print(f"{n:<38s}  SHAPE MISMATCH {A.shape} vs {B.shape} -- skipped")
            missing += 1
            continue
        m = 0.5 * (A + B)
        mg = grad(m.mean(axis=2))
        hi = mg >= np.percentile(mg, args.edge_pct)
        lo = mg < args.flat_abs
        flat_frac = float(lo.mean())

        e = []
        for i, j in ((0, 1), (0, 2), (2, 1)):
            da, db = A[..., i] - A[..., j], B[..., i] - B[..., j]
            sa, sb = da[hi].std(), db[hi].std()
            e.append(float(sb / sa) if sa else float("nan"))

        if flat_frac < args.min_flat:
            noflat.append(n)
            print(f"{n:<38s} {e[0]:9.4f} {e[1]:9.4f} {e[2]:9.4f} | "
                  f"{flat_frac:6.2%} {'NO-FLAT-SET -- placebo not evaluated':>29s}")
            rows.append((n, e, []))
            continue

        f = []
        struct = []
        for i, j in ((0, 1), (0, 2), (2, 1)):
            da, db = A[..., i] - A[..., j], B[..., i] - B[..., j]
            sa, sb = da[lo].std(), db[lo].std()
            f.append(float(sb / sa) if sa else float("nan"))
            ea = da[hi].std()
            struct.append(float(sa / ea) if ea else float("nan"))
        rows.append((n, e, f))
        # struct = how much chroma the "flat" set carries relative to the edge
        # set, in arm A alone.  A genuinely featureless set reads near zero.  A
        # set that reads high is not flat and its placebo is not a placebo.
        #
        # Deconfounded edge ratio.  The measured placebo IS this subject's own
        # noise gain k, because a flat set is noise and the correction resamples
        # it (verified in closed form against the Catmull-Rom taps by
        # noisegain.py).  Decompose the edge chroma variance into fringe and
        # noise using struct, scale only the noise part by k, and solve for the
        # fringe-only ratio:
        #     obs^2 = (fringe_after^2 + k^2 n^2) / (fringe_before^2 + n^2)
        #     n^2 = struct^2 s^2 ,  fringe_before^2 = (1 - struct^2) s^2
        #  => fringe_ratio = sqrt((obs^2 - k^2 struct^2) / (1 - struct^2))
        corr = []
        for idx in range(3):
            s2 = min(struct[idx] ** 2, 0.98) if np.isfinite(struct[idx]) else 0.0
            num = e[idx] ** 2 - (f[idx] ** 2) * s2
            corr.append(float(np.sqrt(max(num, 0.0) / (1.0 - s2))))
        corrs.append(corr)
        structs.append(struct[0])
        eraw.append(e)
        print(f"{n:<38s} {e[0]:9.4f} {e[1]:9.4f} {e[2]:9.4f} | "
              f"{flat_frac:6.2%} {f[0]:9.4f} {f[1]:9.4f} {f[2]:9.4f} "
              f"{struct[0]:8.3f} {corr[0]:9.4f}")

    if not rows:
        print("\nno comparable pairs found")
        return 1

    E = np.array([r[1] for r in rows])
    F = np.array([r[2] for r in rows if r[2]])
    print("-" * len(hdr))
    print(f"{'MEDIAN':<38s} {np.median(E[:, 0]):9.4f} {np.median(E[:, 1]):9.4f} "
          f"{np.median(E[:, 2]):9.4f} |", end="")
    if F.size:
        print(f" {'':6s} {np.median(F[:, 0]):9.4f} {np.median(F[:, 1]):9.4f} "
              f"{np.median(F[:, 2]):9.4f}")
    else:
        print("  no placebo rows")
    print(f"{'WORST (max ratio)':<38s} {E[:, 0].max():9.4f} {E[:, 1].max():9.4f} "
          f"{E[:, 2].max():9.4f}")

    # Partition every subject into counted outcomes that sum to the total, so a
    # subject that was skipped cannot read as one that improved.
    improved = int((E[:, 0] < 1.0).sum())
    worsened = int((E[:, 0] > 1.0).sum())
    flat_eq = len(rows) - improved - worsened
    print(f"\ncompared {len(rows)}, skipped {missing}, total {len(names)}")
    print(f"edge R-G: improved {improved}, worsened {worsened}, unchanged {flat_eq}"
          f"  (sums to {improved + worsened + flat_eq})")
    print(f"placebo: evaluated {F.shape[0] if F.size else 0}, "
          f"not evaluated (no flat set) {len(noflat)}"
          f"  (sums to {(F.shape[0] if F.size else 0) + len(noflat)})")
    if noflat:
        print(f"  no flat set: {', '.join(noflat)}")

    if F.size:
        worst_placebo = float(np.abs(F - 1.0).max())
        print(f"largest placebo excursion: {worst_placebo:.4f} from 1.0", end="  ")
        print("-- PLACEBO CLEAN" if worst_placebo < 0.02
              else "-- resample noise gain, see noisegain.py; edge numbers "
                   "deconfounded in the R-G corr column")
    if corrs:
        C = np.array(corrs)
        S = np.array(structs)
        # The decomposition is only meaningful where the flat set is actually
        # flat.  At struct >= 1 the "flat" set carries more chroma than the edge
        # set, the noise term exceeds the total, and the correction clamps to
        # zero -- which is not a measurement.  Report the median over valid rows
        # only, and count the rows excluded so a discarded row cannot read as a
        # row that improved.
        ok = S < 0.5
        if ok.any():
            print(f"\ndeconfounded edge R-G (fringe only), over the "
                  f"{int(ok.sum())} rows with a genuinely flat placebo set "
                  f"(struct < 0.5):")
            print(f"  median {np.median(C[ok, 0]):.4f}, "
                  f"worst {C[ok, 0].max():.4f}, best {C[ok, 0].min():.4f}")
            print(f"  vs raw median {np.median(np.array(eraw)[ok, 0]):.4f} over the same rows"
                  f" -- correction moves it by "
                  f"{np.median(C[ok, 0]) - np.median(np.array(eraw)[ok, 0]):+.4f}")
            print(f"  (a NEGATIVE move means the noise floor was DILUTING the "
                  f"measured win, not inflating it)")
        print(f"  rows excluded as struct >= 0.5 (flat set not flat): "
              f"{int((~ok).sum())}  (sums to {len(corrs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

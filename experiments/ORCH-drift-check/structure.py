"""Is the band-pass amplitude the pyramid discards SIGNAL or NOISE?

ampcurve.py measured a notch: the pyramid merge's band-pass amplitude falls to
0.31x the estimator's in a bin near 31-53 DN, on four subjects whose amplitude
ranges differ 4x, with the minimum at the same ABSOLUTE DN on each.

pyramid.rs:1048-1058 supplies a mechanism. Where no frame's smoothed band energy
clears `gate * beta * var`, the output coefficient is `usum[j] / frames` -- the
unweighted mean of that Laplacian coefficient over all N frames. The merge's own
diagnostic reports this covers 47.9% of the finest band and 36.8% of the next.

But a ratio below 1.0 has TWO readings and the ratio alone cannot separate them:

  (A) the pyramid is DESTROYING real detail the estimator keeps.
      Then the fallback mean is the bug: in a focus stack a fine-band
      coefficient lives in only the few frames where that pixel is in focus,
      so a mean over 100 frames returns ~n_focus/N of it.

  (B) the pyramid is correctly SUPPRESSING noise the estimator wrongly keeps.
      Then the fallback is right and the estimator is the defective arm. This
      is the design's own argument: below the gate no frame has information,
      so averaging is the correct estimator.

CORRELATION SEPARATES THEM, because it is amplitude-invariant.

  under (A)  blend ~= alpha * ctrl with alpha ~ 0.34. Same structure, smaller.
             Pearson r within the tile stays HIGH -- near what the strong-edge
             tiles show, where both arms certainly render the same real edges.

  under (B)  ctrl's content there is noise; blend's is a different average of
             different noise. The two are independent. r collapses toward the
             shift placebo.

So the notch bin's r, read against the strong-edge bins above it and the shift
placebo below it, is the discriminator.

CONTROLS

  null       ctrl vs itself. Must be exactly 1.0000 in every bin or the tiling
             or the band-pass is lying. Commissioning, not decoration.

  shift      ctrl vs blend displaced by SHIFT px. Destroys any true structural
             correspondence while preserving both images' amplitude statistics
             and both band-pass spectra exactly. This is what "no shared
             structure" reads as on THIS pair -- it is not assumed to be 0.

  positive   the 272-810 DN bins. Both arms demonstrably render the same edges
             there (ampcurve ratio 0.98-1.02), so r there is what "shared
             structure" reads as on this pair. The notch is judged BETWEEN
             these two empirical poles, not against 0 and 1.

PRE-REGISTERED, before running (ORCH, this session):

  If r(notch) is within 0.15 of r(strong edges)  -> reading (A), detail lost.
  If r(notch) is within 0.15 of r(shift placebo) -> reading (B), noise killed.
  Anything between                               -> mixed; report as unresolved
                                                    and do NOT claim either.

I have already been wrong once on this defect this session -- I predicted the
notch was over-selection and the exponent sweep refuted it in the opposite
direction. This prediction is written down so the same thing can happen visibly.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

TILE = 128
S_LO, S_HI = 0.535, 1.874
SHIFT = 64


def bandpass(g: np.ndarray) -> np.ndarray:
    return ndimage.gaussian_filter(g, S_LO) - ndimage.gaussian_filter(g, S_HI)


def corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson r over a tile, guarded against a constant tile."""
    a = a.ravel().astype(np.float64)
    b = b.ravel().astype(np.float64)
    a = a - a.mean()
    b = b - b.mean()
    na, nb = np.sqrt((a * a).sum()), np.sqrt((b * b).sum())
    if na < 1e-12 or nb < 1e-12:
        return float("nan")
    return float((a * b).sum() / (na * nb))


def table(name: str, R: np.ndarray, T: np.ndarray, null: bool = False) -> int:
    gr = R[:, :, 1].astype(np.float32)
    gt = gr if null else T[:, :, 1].astype(np.float32)
    lit = gr > np.quantile(gr[::4, ::4], 0.20)
    br, bt = bandpass(gr), bandpass(gt)

    h, w = gr.shape
    amps, rr, rs, rat = [], [], [], []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            sl = (slice(y, y + TILE), slice(x, x + TILE))
            if lit[sl].mean() < 0.5:
                continue
            ar = float(np.abs(br[sl]).mean())
            if ar < 1e-6:
                continue
            # The shift placebo has to stay inside the frame, so tiles within
            # SHIFT of the right/bottom edge cannot supply one. Skipping them
            # for BOTH columns keeps the two populations identical -- a placebo
            # scored on a different tile set is not a placebo.
            if y + TILE + SHIFT > h or x + TILE + SHIFT > w:
                continue
            sh = (slice(y + SHIFT, y + SHIFT + TILE), slice(x + SHIFT, x + SHIFT + TILE))
            amps.append(ar)
            rat.append(float(np.abs(bt[sl]).mean()) / ar)
            rr.append(corr(br[sl], bt[sl]))
            rs.append(corr(br[sl], bt[sh]))

    amp, r_true, r_shift, ratio = map(np.array, (amps, rr, rs, rat))
    ok = ~np.isnan(r_true) & ~np.isnan(r_shift)
    amp, r_true, r_shift, ratio = amp[ok], r_true[ok], r_shift[ok], ratio[ok]

    tag = "  [NULL: reference vs itself -- r must be 1.0000]" if null else ""
    print(f"\n{name}{tag}    tiles {len(amp)}")
    print(f"  {'refAmp band':>18}{'n':>7}{'ampRatio':>10}{'r(aligned)':>12}{'r(shifted)':>12}   verdict")
    lo, hi = np.quantile(amp, 0.005), np.quantile(amp, 0.995)
    edges = np.geomspace(max(lo, 0.5), hi, 11)
    edges = np.concatenate([[0.0], edges, [np.inf]])
    rows = []
    for i in range(len(edges) - 1):
        m = (amp >= edges[i]) & (amp < edges[i + 1])
        if m.sum() < 5:
            continue
        hs = "inf" if np.isinf(edges[i + 1]) else f"{edges[i + 1]:.0f}"
        rows.append((edges[i], hs, int(m.sum()), ratio[m].mean(), r_true[m].mean(), r_shift[m].mean()))
    for lo_e, hs, n, ra, rt, rsh in rows:
        print(f"  {lo_e:8.0f}-{hs:>8}{n:7d}{ra:10.4f}{rt:12.4f}{rsh:12.4f}")
    if null:
        bad = [r for r in rows if abs(r[4] - 1.0) > 1e-9]
        print(f"  NULL CHECK: {len(rows) - len(bad)}/{len(rows)} bins at r=1.0000 exactly", end="")
        print("   COMMISSIONED" if not bad else f"   ** FAILED in {len(bad)} bins **")
        return 0 if not bad else 1
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: structure.py <dir> <subject> [<subject> ...]", file=sys.stderr)
        return 2
    d = Path(sys.argv[1])
    subjects = sys.argv[2:]
    done = missing = failed = 0
    first = True
    for subject in subjects:
        rp, tp = d / f"{subject}--ctrl.tiff", d / f"{subject}--blend.tiff"
        if not (rp.exists() and tp.exists()):
            print(f"MISSING pair for {subject}: need both {rp.name} and {tp.name}")
            missing += 1
            continue
        R, T = tifffile.imread(rp), tifffile.imread(tp)
        assert R.dtype == np.uint16 and T.dtype == np.uint16, f"{subject}: not uint16"
        assert R.shape == T.shape, f"{subject}: shape mismatch {R.shape} vs {T.shape}"
        if first:
            failed += table(subject, R, R, null=True)
            first = False
        table(subject, R, T)
        done += 1
    # Every input lands in exactly one counted outcome, and they sum to the
    # number requested -- so a skipped subject cannot read as a passed one.
    print(f"\nSUMMARY  requested {len(subjects)}  scored {done}  missing {missing}  null-failures {failed}")
    assert done + missing == len(subjects), "outcomes do not partition the input"
    return 1 if (missing or failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())

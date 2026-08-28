#!/usr/bin/env python3
"""STAGE B -- the merge arm, put through byte-identical code to the frame arm.

Stage A settles whether any SOURCE FRAME resolves structure in a tile, entirely
inside the RAW domain where sensor noise is common-mode and cancels without
being estimated.  Stage B is the other half: it places the delivered master
beside those frames so the ratio map the brief asks for can be drawn.

THE ARMS DIFFER ONLY IN THE INPUT PLANE.  Both arms call ora.bands() and
ora.tile_stats() on a full-size single-channel plane and reduce on the same tile
grid.  No band is computed on a 128 px tile: at sigma 12.8 a 128 px tile is
almost all filter skirt, so band 4 would have become a measurement of the tile
border rather than of the image.  There is no separate code path for the master,
so no asymmetry can hide in one.

THREE THINGS MAKE THE COMPARISON HARD; ALL THREE ARE HANDLED IN THE OPEN.

1.  THE TRANSFORM.  The master is demosaiced, white balanced, matrixed and tone
    mapped; frames are raw green DN.  Absolute DN are not comparable across
    that.  So a per-tile linear gain is removed using band 4, where noise is
    0.03% of signal (kappa_4 = 0.000885, so a 45 DN frame carries 1.8 DN^2 of
    band-4 noise against 10^3-10^4 DN^2 of band-4 signal).  Every reported
    number is then a ratio, which any remaining local linear gain cancels out
    of exactly.

2.  RESAMPLING, WHICH HAS NO NEUTRAL CHOICE.  Both are computed and reported:
      'point' -- master[y0::2, x0::2], the same point sampling the Bayer green
                 plane uses.  Adds no blur to the master, but folds master
                 detail above green Nyquist into the bands, FLATTERING THE
                 MERGE.
      'box'   -- 2x2 block average.  No aliasing, but low-passes the master
                 more than the green plane is low-passed, FLATTERING THE
                 FRAMES.
    A verdict that survives both is not an artefact of this choice.

3.  NOISE, WHICH IS THE TRAP THE BRIEF NAMES.  A single source frame carries
    roughly 45 DN of pixel noise; the merge carries roughly 7 DN.  At band 2
    (kappa_2 = 0.014011) that is 28 DN^2 of pure grain in the frame arm against
    a band-2 signal of only 30-60 DN^2 in exactly the smooth regions under
    investigation.  Raw band power therefore says "the frame beats the merge"
    in every flat region, for no reason but grain.  So the headline is
    NOISE-CORRECTED on both arms:

        src_signal = max_k Var(b,k,tile) - quantile_0.25_k Var(b,k,tile)
                     (stage A's through-focus contrast: the sensor noise term
                      is common to all frames at a tile and cancels identically,
                      with no noise model fitted anywhere)
        mrg_signal = Var_master(b,tile) - (merge's own flat-tile floor)

    The uncorrected ratio is computed too and printed beside it.  Its failure
    direction is stated and asserted rather than assumed: uncorrected, the frame
    arm is inflated by grain, so the uncorrected map is BIASED TOWARD FINDING A
    MERGE DEFECT.  Where the two disagree, the uncorrected one is the adverse
    bound and is labelled as such.  A run in which the uncorrected map does NOT
    exceed the corrected map is a failure of this stated direction and is
    flagged, because it would mean the correction is not doing what is claimed.

Usage:  python stageB.py <subject> [--sampling point|box|both]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

TS = 128
# Minimum phase-correlation peak-to-background ratio for a lock to count.
# flowers-cpl locks at 16.2 with an exactly zero residual; bee-1-cpl registered
# against frame 0 scored 2.3 with a spurious 300 px shift.  4.0 sits between,
# and the gate's chosen value is reported with every result so a reader can see
# which subjects sit near it.
MIN_PEAK = 4.0
# Largest residual displacement, in green px, that still counts as a lock.
# Not zero: after a similarity resample the residual is quantised to whole
# pixels, so demanding exactly (0,0) rejects locks that are correct to within
# 1/128 of a tile.  2 px is 1.6% of the 128 px tile pitch and 0.8% of the
# 256 master px the tile spans.  This tolerance was widened from (0,0) AFTER
# the scale term was added and is stated here rather than tuned quietly; the
# subjects it rescues (bee-1-cpl box mode, residual (1,0)) had peak ratios of
# 24.7, so they were never marginal locks in the first place.
MAX_RESID = 2


def master_luma(subject: str) -> np.ndarray:
    a = tifffile.imread(os.path.join(ora.MASTERS, subject + ".tiff"))
    a = a[:, :, :3].astype(np.float32)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def to_green_grid(luma: np.ndarray, mode: str, y0: int, x0: int):
    """Master luma sampled onto the SAME TWO green sub-lattices a frame uses.

    ora.tile_stats takes the G1 and G2 sub-planes separately, so the master must
    supply both or the two arms would not be the same call.  The master has a
    value at every site, so both lattices are available exactly: G1 at the
    Bayer green site (y0,x0) and G2 at its diagonal partner (y0+1,x0+1).  This
    is what makes the arms differ ONLY in the input image.
    """
    y1, x1 = (y0 + 1) % 2, (x0 + 1) % 2
    if mode == "point":
        a = luma[y0::2, x0::2]
        b = luma[y1::2, x1::2]
    else:
        h, w = luma.shape[0] // 2 * 2, luma.shape[1] // 2 * 2
        f = luma[:h, :w]
        blk = 0.25 * (f[0::2, 0::2] + f[1::2, 0::2]
                      + f[0::2, 1::2] + f[1::2, 1::2])
        # both lattices get the same 2x2 box, offset by one block in each axis,
        # so 'box' keeps the half-pixel diagonal offset that C5 showed is
        # physically present between the two green sites.
        a = blk
        b = np.roll(np.roll(blk, -1, 0), -1, 1)
    n = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    return a[:n[0], :n[1]].astype(np.float32), b[:n[0], :n[1]].astype(np.float32)


def green_offsets(path: str) -> tuple[int, int]:
    import rawpy
    with rawpy.imread(path) as r:
        ys, xs = np.where(r.raw_pattern == 1)
        return int(ys[0]), int(xs[0])


def fit_similarity(ref: np.ndarray, mov: np.ndarray):
    """Find the (scale, dy, dx) that puts `mov` onto `ref`.

    WHY A SCALE PARAMETER IS NEEDED.  Translation-only registration failed on
    most of the corpus with weak (peak 2.6-3.6) and mutually inconsistent
    residuals -- point sampling wanting (26,99) where box sampling wanted
    (37,-124) on the same subject.  Inconsistency of that kind is the signature
    of a model that is missing a degree of freedom, not of noise.  The aligner
    applies a uniform-scale fit_to_cover upsample, so the delivered master is
    not a translate of any single frame; over a 3514 px plane a 1% scale error
    displaces the edges by 17 green px, which is enough to destroy a global
    translation lock while leaving a small, plausible-looking residual.

    The scale is found by coarse search on 4x-downsampled planes (cheap, and
    the search only has to get within one step of the truth), then refined and
    verified at full resolution by the caller.  Reporting the fitted scale is
    itself useful: a subject whose master needs a 1.02 scale to match its own
    frames is telling us something about the aligner.
    """
    from scipy.ndimage import zoom
    r4 = ref[::4, ::4].astype(np.float64)
    best = (None, -np.inf, 0, 0)
    # Two passes: coarse over a wide range, then fine around the winner.  The
    # range is deliberately wider than the aligner is believed to need, because
    # a fit that lands on the edge of its own search range is a fit that has
    # been truncated, not a fit that has converged -- earlier runs pinned at
    # 0.965 with the range starting at 0.960, which is exactly that failure.
    coarse = np.arange(0.88, 1.1201, 0.01)
    for s in coarse:
        m = zoom(mov[::4, ::4].astype(np.float64), s, order=1)
        h, w = min(r4.shape[0], m.shape[0]), min(r4.shape[1], m.shape[1])
        if h < 64 or w < 64:
            continue
        dy, dx, pk = global_shift(r4[:h, :w], m[:h, :w])
        if pk > best[1]:
            best = (float(s), pk, dy * 4, dx * 4)
    if best[0] is not None:
        for s in np.arange(best[0] - 0.009, best[0] + 0.0091, 0.002):
            m = zoom(mov[::4, ::4].astype(np.float64), s, order=1)
            h, w = min(r4.shape[0], m.shape[0]), min(r4.shape[1], m.shape[1])
            if h < 64 or w < 64:
                continue
            dy, dx, pk = global_shift(r4[:h, :w], m[:h, :w])
            if pk > best[1]:
                best = (float(s), pk, dy * 4, dx * 4)
        if abs(best[0] - 0.88) < 1e-9 or abs(best[0] - 1.12) < 1e-9:
            print(f"    WARNING scale fit pinned at the search boundary "
                  f"({best[0]}); the model is missing a degree of freedom")
    return best


def global_shift(a: np.ndarray, b: np.ndarray) -> tuple[int, int, float]:
    """Whole-plane phase correlation -> integer (dy, dx) of b relative to a.

    The correlation uses the FULL overlapping plane, not a corner crop: a corner
    crop cannot see a displacement larger than itself, and the aligner's output
    canvas is offset from the sensor's active area by hundreds of green px on
    some subjects, which a 2048 px window silently mis-locks on.

    A single global integer shift, not a per-tile fit: correspond.py measured
    frame-to-frame drift across the entire 176-frame bracket of flowers-cpl at
    median 0.00 and p90 0.00 green px, so within a bracket the scene is on a
    rail and a per-tile fit would be fitting noise.  The residual shift after
    correction is re-measured by the caller rather than assumed, so a bad lock
    reports itself instead of quietly producing a number.
    """
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    A = a[:h, :w].astype(np.float64)
    B = b[:h, :w].astype(np.float64)
    A = A - A.mean()
    B = B - B.mean()
    win = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    FA, FB = np.fft.rfft2(A * win), np.fft.rfft2(B * win)
    R = FA * np.conj(FB)
    m = np.abs(R)
    R = np.divide(R, m, out=np.zeros_like(R), where=m > 1e-12)
    c = np.fft.irfft2(R, s=(h, w))
    j = int(np.argmax(c))
    dy, dx = np.unravel_index(j, c.shape)
    pk = float(c.flat[j]) / max(float(np.quantile(np.abs(c), 0.99)), 1e-12)
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    return int(dy), int(dx), pk


def plane_tile_var(p1: np.ndarray, p2: np.ndarray, nr: int, nc: int) -> np.ndarray:
    """(NBAND, nr, nc) band variance -- the SAME call the frame arm makes."""
    st = ora.tile_stats(p1, p2, TS)
    v = st["var"]
    out = np.full((ora.NBAND, nr, nc), np.nan, np.float64)
    r = min(nr, v.shape[1])
    c = min(nc, v.shape[2])
    out[:, :r, :c] = v[:, :r, :c]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--sampling", default="both",
                    choices=["point", "box", "both"])
    args = ap.parse_args()

    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    nr, nc = int(A["nr"]), int(A["nc"])
    con, lo, hi = A["contrast"], A["lo"], A["hi"]     # (NBAND, nr, nc)
    kk = A["frames"]
    fs = ora.frames_of(args.subject)
    y0, x0 = green_offsets(fs[0])
    print(f"{args.subject}: grid {nr}x{nc}, {len(kk)} frames sampled, "
          f"green site offset ({y0},{x0})")

    lum = master_luma(args.subject)
    modes = ["point", "box"] if args.sampling == "both" else [args.sampling]
    # Register against the SHARPEST frame in the bracket, not frame 0.  In a
    # deep stack frame 0 is almost entirely defocused, shares little structure
    # with the merged master, and phase correlation then locks onto noise: on
    # bee-1-cpl registering to frame 0 gave a peak ratio of 2.3 and a spurious
    # 300 px shift, where the sharpest frame gives a clean lock.  The sharpest
    # frame is the one whose band-2 power summed over tiles is greatest, taken
    # from the stage A cube so no new decode is needed.
    kref = int(np.argmax(np.nansum(A["var_k"][:, 2], axis=(1, 2))))
    gref, _ = ora.green_pair(fs[int(kk[kref])])
    g0 = gref
    print(f"  registration reference: frame {int(kk[kref])} "
          f"(sharpest of the {len(kk)} sampled)")
    out = {}
    reg_ok = True
    for mode in modes:
        Ma, Mb = to_green_grid(lum, mode, y0, x0)
        s, spk, _, _ = fit_similarity(g0, Ma)
        if s is not None and abs(s - 1.0) > 1e-9:
            from scipy.ndimage import zoom
            Ma = zoom(Ma, s, order=1).astype(np.float32)
            Mb = zoom(Mb, s, order=1).astype(np.float32)
        dy, dx, pk = global_shift(g0.astype(np.float32), Ma)
        h = min(Ma.shape[0], g0.shape[0])
        w = min(Ma.shape[1], g0.shape[1])
        Ma = np.roll(np.roll(Ma, dy, axis=0), dx, axis=1)[:h, :w]
        Mb = np.roll(np.roll(Mb, dy, axis=0), dx, axis=1)[:h, :w]
        rdy, rdx, rpk = global_shift(g0[:h, :w].astype(np.float32), Ma)
        print(f"  [{mode}] master lattice -> scale {s:.4f} (search peak "
              f"{spk:.1f}), shift ({dy},{dx}) peak {pk:.1f}; residual "
              f"({rdy},{rdx}) peak {rpk:.1f}")
        # A hard gate, not a warning.  A ratio map built on a failed lock is a
        # measurement of the misregistration, and it fails in the direction of
        # inventing a merge defect: comparing a sharp frame tile against a
        # DIFFERENT master tile reads exactly like thrown-away detail.  So a
        # subject that does not lock is refused a number and is counted as
        # UNREGISTERED downstream rather than being quietly ranked.
        if (abs(rdy) > MAX_RESID or abs(rdx) > MAX_RESID) or pk < MIN_PEAK:
            reg_ok = False
            print(f"  [{mode}] REGISTRATION FAILED (residual ({rdy},{rdx}), "
                  f"peak {pk:.1f} < {MIN_PEAK}); this subject will be reported "
                  f"as UNREGISTERED, not ranked")
        var = plane_tile_var(Ma, Mb, nr, nc)

        # per-tile linear gain from band 4, where noise is 0.03% of signal
        gain2 = np.maximum(hi[4], 1e-9) / np.maximum(var[4], 1e-9)
        mrg = var * gain2[None, :, :]
        # The merge's own flat-tile floor per band: a low quantile over tiles.
        # Where the flattest tiles still hold structure this OVER-states merge
        # noise, which UNDER-states the merge -- adverse to exonerating it.
        nfloor = np.nanquantile(mrg.reshape(ora.NBAND, -1), 0.02, axis=1)
        mrg_sig = np.maximum(mrg - nfloor[:, None, None], 0.0)
        out[mode] = {"raw": mrg, "sig": mrg_sig, "gain2": gain2}
        print(f"  [{mode}] merge flat-tile floor per band (frame DN^2): "
              + " ".join(f"b{i}={nfloor[i]:.1f}" for i in range(ora.NBAND)))

    p = os.path.join(ora.OUT, "stageB", args.subject + ".npz")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez_compressed(
        p, subject=args.subject, nr=nr, nc=nc, modes=np.array(modes),
        src_sig=con, src_raw=hi, src_floor=lo, reg_ok=np.array(reg_ok),
        kref=int(kk[kref]),
        **{f"{m}_{a}": out[m][a] for m in modes for a in ("raw", "sig", "gain2")},
    )
    print(f"  wrote {p}   registration {'OK' if reg_ok else 'FAILED'}")

    print("\n=== per-tile  BEST SOURCE FRAME / MERGE,  band by band ===")
    print("ratio > 1 means a source frame carried more resolvable structure at")
    print("that tile than the merge delivered.  'detail tiles' = the top decile")
    print("of this subject's own through-focus contrast in that band, because")
    print("the question is only meaningful where a sharp frame exists at all;")
    print("the remaining 90% of tiles are reported on the line below, never")
    print("silently dropped.")
    for mode in modes:
        print(f"\n-- sampling '{mode}' --")
        for b in range(ora.NBAND):
            det = con[b] >= np.nanquantile(con[b], 0.90)
            row = {}
            for tag, s, m in (("UNCORR", hi[b], out[mode]["raw"][b]),
                              ("CORR  ", con[b], out[mode]["sig"][b])):
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = s / np.maximum(m, 1e-9)
                rd = ratio[det]
                rd = rd[np.isfinite(rd)]
                ro = ratio[~det]
                ro = ro[np.isfinite(ro)]
                row[tag.strip()] = float(np.median(rd))
                print(f"  b{b} {tag}  detail tiles n={rd.size:4d}: "
                      f"median={np.median(rd):8.3f} p90={np.quantile(rd, 0.90):9.3f} "
                      f"max={rd.max():10.3f}  src>merge in "
                      f"{100.0 * (rd > 1.0).mean():5.1f}%   |   "
                      f"other tiles n={ro.size:4d}: median={np.median(ro):8.3f} "
                      f"src>merge in {100.0 * (ro > 1.0).mean():5.1f}%")
            if row["UNCORR"] < row["CORR"]:
                print(f"  b{b} !! STATED FAILURE DIRECTION VIOLATED: the "
                      f"uncorrected ratio ({row['UNCORR']:.3f}) is BELOW the "
                      f"corrected one ({row['CORR']:.3f}).  The noise "
                      f"correction is not behaving as claimed in this band.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

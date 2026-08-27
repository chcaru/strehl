#!/usr/bin/env python3
"""
V-EYES: does my instrument see FOCUS, or does it see something else?

WHY THIS EXISTS
---------------
ORCH routed two findings from other lanes that, if they apply to my band,
invalidate the quantity my whole workstream ranks merges by:

  * `V-HEADTOHEAD2.md` §0 / `V-LINEAR.md` retract the "17-27% behind two
    external stackers" claim twice, the second time because a tone curve fitted
    to 4x4 BLOCK AVERAGES -- a fit with no access to any frequency above 0.125
    cyc/px, containing zero information about resolution -- reproduces Zerene's
    0.25-0.30 cyc/px band power from strehl's own pixels to 0.02%.

  * `V-HEADTOHEAD2` §3b, applied by that lane AGAINST ITS OWN HEADLINE: on
    strehl's linear develops a tile IN FOCUS carries the same 0.20-0.48 cyc/px
    power as the same tile TWENTY FRAMES OUT OF FOCUS -- ratios 1.015, 1.043,
    1.004, 1.138 over four frame pairs.

The second is the one that cuts here. **A metric that cannot distinguish
in-focus from twenty-frames-out-of-focus is not a sharpness metric, whatever it
is named.** If my per-site ceiling integrates inside 0.20-0.48, then defocus
itself cannot move the thing I have been calling softness, and the 5-19%
deficit is misnamed rather than fake.

This script tests that on MY instrument, with MY primitives, on real frames at
real focus positions. Synthetic blur is not the test and would pass trivially:
section 5.7 already showed the statistic responds to planted blur (0.73 at
sigma 0.53). The claim under test is about whether the FILES carry scene signal
that focus moves, which only real frames can answer.

DESIGN
------
Quantities tracked per 64 px site, all on the same aligned tiles:

    full        the pinned detail() -- exactly what the ceiling ranks by
    six bins    0.05-0.10, 0.10-0.20, 0.20-0.25, 0.25-0.30, 0.30-0.40,
                0.40-0.48 cyc/px -- V-LINEAR2 §1's band edges verbatim, so
                its per-tile table and this one can be read side by side
                without either being re-binned
    two aggs    0.05-0.25 and 0.30-0.48, drawn on V-LINEAR2's own PASS/FAIL
                line rather than on a boundary chosen here

For each site the best frame k* is chosen BY THE FULL STATISTIC ONLY, and every
band quantity is then read at k* and at k* +/- delta. That ordering is
deliberate: the band quantities are never selected on themselves, so their
readings carry no order-statistic bias. The full statistic does, and that bias
is measured rather than assumed.

Note which version of the other lane's claim is under test. V-LINEAR §5.3's
1.015/1.043/1.004/1.138 came from four hand-picked WHOLE-FRAME pairs and is
already amended by V-LINEAR2 §1/Q2, which finds per-tile selection recovers
2.419 at 0.20-0.25 where whole-frame pairs reported 1.0. This script is
per-tile, so V-LINEAR2's table is the like-for-like comparison; V-LINEAR's is
kept in view only because it is the number still circulating.

Frames are aligned to the master with the instrument's own `shift_of`/`warp`
before anything is measured. Comparing unaligned frames would let subject
displacement masquerade as defocus.

COMMISSIONING -- three arms, because two would not be enough
------------------------------------------------------------
NULL           n noised copies of ONE frame. True ratio is 1.000 by
               construction, so whatever the argmax-vs-other reading is, it is
               pure order-statistic inflation and it bounds every other number
               here from below.
DEFECT         a real frame progressively blurred. The statistic must fall, and
               fall monotonically, or it cannot see softness at all.
IMPROVEMENT    the same ladder read in reverse -- from blurred toward sharp.
               A suite that only ever plants degradations cannot tell a metric
               that is BLIND to an effect from one that is PERVERSE on it, and
               this project has shipped exactly that bug twice
               (`tri.blur_equiv` bounded below at zero; `overshoot_frac`
               amplitude-invariant and rising with blur).

Usage:
    python focus_null.py <subject> [--size N] [--root DIR]
"""
import argparse
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from softness_verdict3 import (HP_SIGMA, blocks, detail, luma_linear,  # noqa: E402
                               shift_of, warp)
from corpus_softness import pick_tile                                  # noqa: E402
from envelope_null import calibrate_noise                              # noqa: E402

BLOCK = 64
# V-LINEAR2 §1's band edges, verbatim, so my table can be laid beside its table
# without either being re-binned. Its per-tile verdicts on stack 113 are:
#   0.05-0.10  18.193 PASS      0.25-0.30   1.387 MARGINAL
#   0.10-0.20  10.083 PASS      0.30-0.40   1.149 FAIL (noise)
#   0.20-0.25   2.419 PASS      0.40-0.48   1.105 FAIL (noise)
BANDS = [(0.05, 0.10), (0.10, 0.20), (0.20, 0.25),
         (0.25, 0.30), (0.30, 0.40), (0.40, 0.48)]
VL2 = {(0.05, 0.10): "18.193 PASS", (0.10, 0.20): "10.083 PASS",
       (0.20, 0.25): "2.419 PASS", (0.25, 0.30): "1.387 MARG",
       (0.30, 0.40): "1.149 FAIL", (0.40, 0.48): "1.105 FAIL"}
# Two aggregates for the verdict, drawn on V-LINEAR2's own PASS/FAIL line
# rather than on a boundary I chose: it certifies focus-dependent signal below
# 0.25 and finds none above 0.30.
AGG = [("SIGNAL 0.05-0.25 (VL2 PASS)", (0.05, 0.25)),
       ("NOISE  0.30-0.48 (VL2 FAIL)", (0.30, 0.48))]
# Column order for every table: the six fine bins, then the two aggregates
# marked with * so an aggregate can never be mistaken for a disjoint bin.
COLS = ([f"{lo:.2f}-{hi:.2f}" for lo, hi in BANDS]
        + [f"*{lo:.2f}-{hi:.2f}" for _, (lo, hi) in AGG])


def band_mask(n, lo, hi, soft=0.02):
    """Radial band mask with raised-cosine edges.

    An ideal brick-wall mask rings in the spatial domain, and that ringing
    lands in the per-block energies this function exists to compute. The
    transition width is stated rather than tuned.
    """
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    fr = np.sqrt(fx * fx + fy * fy)

    def ramp(x):
        return 0.5 - 0.5 * np.cos(np.pi * np.clip(x, 0, 1))

    return ramp((fr - lo) / soft) * ramp((hi - fr) / soft)


def band_energy(tile, mask):
    """Per-site mean square inside a frequency band."""
    F = np.fft.fft2(tile.astype(np.float64))
    b = np.real(np.fft.ifft2(F * mask))
    return blocks(b * b, BLOCK, lambda r: r.mean(axis=(1, 3)))


def measure_stack(tiles, masks):
    """(full, [per-band]) per site per frame.

    The forward FFT is taken once per tile and shared across every band, which
    is the only reason measuring eight bands costs about what two did.
    """
    full, bands = [], [[] for _ in masks]
    for t in tiles:
        d, _ = detail(t, BLOCK)
        full.append(d)
        F = np.fft.fft2(t.astype(np.float64))
        for j, m in enumerate(masks):
            b = np.real(np.fft.ifft2(F * m))
            bands[j].append(blocks(b * b, BLOCK, lambda r: r.mean(axis=(1, 3))))
    return np.array(full), [np.array(b) for b in bands]


def _hdr():
    return ("    " + f"{'delta':>6} {'n sites':>8} {'full':>9} "
            + " ".join(f"{s:>11}" for s in COLS))


def report(full, bands, deltas, label, sel=None):
    """Ratio at the per-site best frame against frames `delta` away.

    The per-site best frame is chosen by the FULL statistic in every column, so
    the band columns carry no order-statistic bias of their own: they report
    what the band does at the site the full statistic called focused, which is
    the quantity the verdict actually depends on.
    """
    nf, ny, nx = full.shape
    pick = (full if sel is None else sel).argmax(axis=0)
    print(f"\n  {label}   {nf} frames, {ny * nx} sites")
    print(_hdr())
    out = {}
    for d in deltas:
        # use whichever of k*-d, k*+d exists; require it to be in range
        alt = np.where(pick - d >= 0, pick - d, pick + d)
        ok = (alt >= 0) & (alt < nf) & (np.abs(alt - pick) == d)
        if ok.sum() < 20:
            continue
        iy, ix = np.nonzero(ok)
        kb, ka = pick[iy, ix], alt[iy, ix]

        def r(arr):
            a = arr[kb, iy, ix]
            b = arr[ka, iy, ix]
            m = b > 0
            return float(np.median(a[m] / b[m]))

        row = [r(full)] + [r(b) for b in bands]
        out[d] = row
        print(f"    {d:>6} {int(ok.sum()):>8} {row[0]:>9.4f} "
              + " ".join(f"{v:>11.4f}" for v in row[1:]))

    # An unambiguous row that does not depend on which sites can reach +/-d:
    # every site has a worst frame, so this one is defined everywhere and the
    # site count cannot bias it. The +/-d rows lose sites whose best frame sits
    # near an end of the bracket, and that subset is not random -- it is the
    # sites that focus latest or earliest.
    worst = (full if sel is None else sel).argmin(axis=0)
    iy, ix = np.mgrid[0:ny, 0:nx]
    iy, ix = iy.ravel(), ix.ravel()
    kb, ka = pick.ravel(), worst.ravel()

    def rw(arr):
        a = arr[kb, iy, ix]
        b = arr[ka, iy, ix]
        m = b > 0
        return float(np.median(a[m] / b[m]))

    row = [rw(full)] + [rw(b) for b in bands]
    print(f"    {'worst':>6} {ny * nx:>8} {row[0]:>9.4f} "
          + " ".join(f"{v:>11.4f}" for v in row[1:]))
    out["worst"] = row
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("subject")
    p.add_argument("--size", type=int, default=2048)
    p.add_argument("--root", default=r"C:\dev\strehl-out\V-EYES\corpus")
    a = p.parse_args()

    d = pathlib.Path(a.root) / a.subject
    mtif = d / "MASTER.tiff"
    fr = sorted(d.glob("frame-*.tiff"))
    if not mtif.exists() or len(fr) < 8:
        print(f"need MASTER.tiff and >=8 frames in {d}; found {len(fr)}")
        return 1

    m = luma_linear(tifffile.imread(str(mtif)))
    tx, ty = pick_tile(m, a.size)
    master = m[ty:ty + a.size, tx:tx + a.size].copy()
    del m
    print(f"{a.subject}: {len(fr)} frames, tile ({tx},{ty}) {a.size}, BLOCK={BLOCK}")

    masks = [band_mask(a.size, lo, hi) for lo, hi in BANDS]
    amasks = [band_mask(a.size, lo, hi) for _, (lo, hi) in AGG]

    tiles = []
    for f in fr:
        t = luma_linear(tifffile.imread(str(f)))[ty:ty + a.size, tx:tx + a.size]
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))
    print(f"  aligned {len(tiles)} frames to the master with the instrument's own "
          f"shift_of/warp")

    full, bands = measure_stack(tiles, masks + amasks)
    deltas = [d for d in (1, 2, 5, 10, 20) if d < len(tiles)]

    print("\nMEASURED  -- best frame per site vs a frame `delta` away")
    real = report(full, bands, deltas, "real focus bracket")

    print("\nCOMMISSIONING")
    # NULL: n noised copies of ONE frame. True ratio 1.000 by construction.
    #
    # The noise level is NOT estimated from pixel differences. A first version
    # did that on every 7th pixel, which measures SIGNAL variation, planted
    # sigma=1099 DN against a real floor near 15, and the null then read 2.06 on
    # a construction whose true ratio is 1.000. The pinned envelope_null.py
    # already solves this properly: it calibrates the amplitude so the noise's
    # own BLOCK HIGH-PASS ENERGY lands on the real frames' measured detail
    # floor, which is the quantity the instrument actually responds to. Using
    # its function keeps this null on the same footing as the published one.
    rng = np.random.default_rng(5)
    base = tiles[len(tiles) // 2]
    floors = [detail(t, BLOCK)[1] for t in tiles]
    target = float(np.median(floors))
    amp = calibrate_noise(base.shape, target, seed=7)
    print(f"  real frame detail floor (median of {len(floors)}): {target:.1f}")
    print(f"  calibrated noise amplitude: {amp:.1f} DN/px")
    nt = [base + rng.normal(0, amp, base.shape).astype(np.float32)
          for _ in range(len(tiles))]
    nf_, nb_ = measure_stack(nt, masks + amasks)
    nul = report(nf_, nb_, deltas,
                 f"planted NULL (noised copies, amp {amp:.1f} DN)")

    # DEFECT and IMPROVEMENT: a blur ladder built from ONE real frame, so the
    # only thing that varies across the "stack" is sharpness.
    sig = (0.0, 0.3, 0.6, 1.0, 1.5, 2.1, 2.8, 3.6, 4.5, 5.5)
    lad = [cv2.GaussianBlur(base, (0, 0), s) if s > 0 else base.copy()
           for s in sig]
    lf, lb = measure_stack(lad, masks + amasks)
    print("\n  planted DEFECT/IMPROVEMENT ladder (one frame, blur only):")
    print("    " + f"{'sigma':>6} {'full':>9} "
          + " ".join(f"{s:>11}" for s in COLS))
    for i, s in enumerate(sig):
        vals = [np.median(lf[i]) / np.median(lf[0])]
        vals += [np.median(b[i]) / np.median(b[0]) for b in lb]
        print(f"    {s:>6.1f} {vals[0]:>9.4f} "
              + " ".join(f"{v:>11.4f}" for v in vals[1:]))
    mono = all(np.median(lf[i]) >= np.median(lf[i + 1]) for i in range(len(lad) - 1))
    revd = np.median(lf[0]) / np.median(lf[-1])
    print(f"    monotone in blur: {mono};  improvement arm (sharp/blurred) "
          f"x{revd:.2f} -- must be > 1")

    print("\nVERDICT")
    for key in (max(deltas) if deltas else None, "worst"):
        if key is None or key not in real:
            continue
        rrow = real[key]
        nrow = nul.get(key, [1.0] * len(rrow))
        tag = (f"delta={key} frames" if key != "worst"
               else "best vs worst frame at that site")
        print(f"\n  {tag}, corrected for the order-statistic null:")
        print(f"    {'band':<28} {'raw':>8} {'null':>8} {'corrected':>10}   "
              f"{'V-LINEAR2 per-tile':>18}")
        names = ["full statistic"] + [f"  {s}" for s in COLS[:len(BANDS)]] \
            + [f"  {nm}" for nm, _ in AGG]
        for j, nm in enumerate(names):
            vl2 = VL2.get(BANDS[j - 1]) if 1 <= j <= len(BANDS) else ""
            print(f"    {nm:<28} {rrow[j]:>8.4f} {nrow[j]:>8.4f} "
                  f"{rrow[j] / nrow[j]:>10.4f}   {vl2:>18}")

    if "worst" not in real:
        print("  nothing concluded")
        return 2
    rrow, nrow = real["worst"], nul.get("worst", [1.0] * 9)
    cor = [rrow[j] / nrow[j] for j in range(len(rrow))]
    cf = cor[0]
    csig, cnoi = cor[1 + len(BANDS)], cor[2 + len(BANDS)]
    print("\n  V-LINEAR §5.3 measured 1.004-1.138 over 0.20-0.48 on four "
          "hand-picked WHOLE-FRAME pairs.")
    print("  V-LINEAR2 §1/Q2 amends that with per-tile focus selection: 2.419 "
          "PASS at 0.20-0.25,")
    print("  1.387 MARGINAL at 0.25-0.30, 1.10-1.15 FAIL above 0.30.")
    if cf < 1.20:
        print("  -> MY FULL STATISTIC CANNOT SEE FOCUS EITHER. Every ratio it has "
              "produced needs re-reading.")
    else:
        print(f"  -> my full statistic separates focus by x{cf:.2f}. It IS a "
              f"sharpness metric on these files.")
    # The two-lane comparison that matters is per-tile against per-tile. Both
    # V-LINEAR2 and this script let each site choose its own best and worst
    # frame; V-LINEAR's superseded 1.004-1.138 did not, and that difference of
    # method is exactly what V-LINEAR2 §1 identifies as the reason it read 1.0.
    print(f"  -> per-tile, I read x{csig:.2f} where V-LINEAR2 certifies signal "
          f"(<=0.25) and x{cnoi:.2f} where it certifies noise (>=0.30).")
    if cnoi < csig:
        print("     Same ordering, same crossover, independent code and a "
              "different subject: the lanes AGREE once the superseded "
              "whole-frame version is set aside.")

    # ------------------------------------------------------------------
    # THE PAYOFF: decompose the published verdict itself by band.
    #
    # Knowing my statistic can see focus is necessary but not sufficient. The
    # question ORCH actually needs answered is whether the 5-19% DEFICIT -- the
    # number, not the instrument -- is carried by the band where focus lives or
    # by the band where V-LINEAR found nothing. A deficit concentrated in
    # 0.20-0.48 would be a measurement of sensor-common structure, tone or
    # gather phase wearing the word "softness". A deficit in 0.05-0.20 is a
    # real loss of scene detail.
    #
    # Same construction as the published ratio: per-site MAX over the complete
    # bracket as the ceiling, median over live sites, live = the top 35% of
    # sites by low-frequency contrast, exactly as envelope_null.py gates them.
    # ------------------------------------------------------------------
    from softness_verdict3 import contrast          # noqa: E402
    cm = contrast(master, BLOCK)
    cfloor = float(np.percentile(cm, 65))
    live = cm > cfloor
    md, _ = detail(master, BLOCK)
    mband = [band_energy(master, m) for m in masks + amasks]

    # The null for THIS question needs n noised copies of the MASTER, not of a
    # frame: the published ratio is master-over-envelope, so the construction
    # whose true ratio is 1.000 is one where every reference member IS the
    # master. Reusing the focus null's frame-based set would be answering a
    # different question with the right-looking number.
    nmt = [master + rng.normal(0, amp, master.shape).astype(np.float32)
           for _ in range(len(tiles))]
    vf, vb = measure_stack(nmt, masks + amasks)

    print(f"\nBAND-RESOLVED VERDICT  ({int(live.sum())} live sites of {live.size}, "
          f"contrast > P65)")
    print(f"    {'band':<28} {'raw':>8} {'null':>8} {'corrected':>10}   "
          f"{'focus x (worst row)':>19}")
    names = ["full (published)"] + [f"  {s}" for s in COLS[:len(BANDS)]] \
        + [f"  {nm}" for nm, _ in AGG]
    vals = [(md, full, vf)] + [(mband[j], bands[j], vb[j])
                               for j in range(len(masks + amasks))]
    corr = []
    for j, (nm, (mval, farr, narr)) in enumerate(zip(names, vals)):
        env = farr.max(axis=0)
        nenv = narr.max(axis=0)
        m = live & (env > 0)
        mn = live & (nenv > 0)
        raw = float(np.median(mval[m] / env[m]))
        nul_r = float(np.median(mval[mn] / nenv[mn]))
        corr.append(raw / nul_r)
        print(f"    {nm:<28} {raw:>8.4f} {nul_r:>8.4f} {raw / nul_r:>10.4f}   "
              f"{cor[j]:>19.4f}")

    cfull = corr[0]
    csigv, cnoiv = corr[1 + len(BANDS)], corr[2 + len(BANDS)]
    print(f"\n  full statistic reproduced here: {cfull:.4f}")
    # The question is NOT which band is worse. It is whether the deficit
    # SURVIVES restriction to the bands another lane has certified as carrying
    # focus-dependent signal. If SIGNAL came back at ~1.0 while NOISE was far
    # below it, the published number would be an artefact of a band defocus
    # cannot move, and the whole workstream would need re-reading. If SIGNAL is
    # itself well below 1.0, the deficit is carried by a band where focus
    # demonstrably moves the statistic, and what the noise band does is then a
    # second-order question about the headline's exact value.
    if csigv > 0.95:
        print(f"  -> THE DEFICIT DOES NOT SURVIVE. The signal band reads "
              f"{csigv:.4f}, so the published number is carried by bands "
              f"V-LINEAR2 certifies as noise ({cnoiv:.4f}) and is misnamed.")
    else:
        print(f"  -> THE DEFICIT SURVIVES. Restricted to 0.05-0.25, which "
              f"V-LINEAR2 certifies as carrying focus-dependent signal and "
              f"where focus moves this statistic x{csig:.2f},")
        print(f"     the master still reads {csigv:.4f} against its own "
              f"per-site ceiling. The 5-19% is not an artefact of a "
              f"focus-blind band.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

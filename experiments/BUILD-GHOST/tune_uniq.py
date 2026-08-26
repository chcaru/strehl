"""Calibrate UNIQ_FLOOR instead of guessing it.

Three controls failed together -- C4 (heavy defocus, no motion), C6
(wrapped-text-1, a rigid subject) and C7 (the two greens of one exposure) -- and
the hypothesis is that all three failed for one reason: a tall but AMBIGUOUS
correlation peak.  Repetitive content offers rival peaks a period apart, a
blurred tile offers a flat plateau, and two green sub-lattices alias differently
near Nyquist.  rho cannot tell any of those from a good measurement.

This sweeps the uniqueness threshold over the three failing cases AND over the
cases that already passed, because a threshold that fixes the failures by
throwing away all the data is not a fix.  It prints the residual p99 and the
surviving tile count side by side at every threshold, so the trade is visible
rather than asserted.

It works on the PARABOLIC peak, skipping the expensive sub-pixel refinement:
the question here is whether whole-pixel outliers of 5-10 sensor px survive,
and 1/16 px refinement cannot change that answer.

    python experiments/BUILD-GHOST/tune_uniq.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G
import controls as C

GRID = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)



def fine_field(ga, gb, noise, excl=3):
    """Everything measure_pair does, but stopping at the parabolic residual and
    keeping the per-tile rho/uniq so a threshold can be applied afterwards.

    The COARSE stage carries no uniqueness gate, matching measure_pair: a 256 px
    tile has a broad correlation peak and a margin test rejects 397 of 400 of
    them, which collapses the similarity fit to the identity and makes every
    fine residual read as the whole warp.  That failure is why this file exists
    twice-checked against measure_pair (see debug_field.py)."""
    h, w = ga.shape
    cy0, cx0 = (h - 1) / 2.0, (w - 1) / 2.0
    k, r2 = noise

    def fg(A, B):
        hfa, sa = G.hf_modulation(A, k, r2)
        hfb, sb = G.hf_modulation(B, k, r2)
        st = (hfa >= G.HF_SIG_MIN_REL * sa) & (hfb >= G.HF_SIG_MIN_REL * sb)
        return st & (np.abs(np.log(np.maximum(hfa, 1e-12) / np.maximum(hfb, 1e-12)))
                     <= G.FOCUS_MATCH_MAX_LN)

    oc = G.tile_origins((h, w), G.TILE_COARSE, G.STRIDE_COARSE, G.MAX_SHIFT_COARSE)
    A = G.gather_tiles(ga, oc, G.TILE_COARSE)
    B = G.gather_tiles(gb, oc, G.TILE_COARSE)
    dC, rhoC, edC, _ = G.zncc_shift(A, B, G.MAX_SHIFT_COARSE)
    okC = fg(A, B) & (rhoC >= G.RHO_FLOOR) & ~edC & np.isfinite(dC).all(1)
    assert okC.sum() >= 8, f"coarse stage collapsed: {int(okC.sum())}/{oc.shape[0]}"
    dC[okC] = G.refine_shift(A[okC], B[okC], dC[okC], usfac=G.USFAC)
    del A, B
    pcC = ((oc[:, 1] + G.TILE_COARSE / 2 - cx0) + 1j * (oc[:, 0] + G.TILE_COARSE / 2 - cy0))[okC]
    sim = G.fit_similarity(pcC, dC[okC, 1] + 1j * dC[okC, 0], rhoC[okC])

    of = G.tile_origins((h, w), G.TILE_FINE, G.STRIDE_FINE, G.MAX_SHIFT_COARSE + G.MAX_RESID)
    pc = (of[:, 1] + G.TILE_FINE / 2 - cx0) + 1j * (of[:, 0] + G.TILE_FINE / 2 - cy0)
    dp = sim.predict(pc)
    si = np.stack([np.rint(dp.imag).astype(int), np.rint(dp.real).astype(int)], 1)
    ob = of + si
    inb = ((ob[:, 0] >= 0) & (ob[:, 0] <= h - G.TILE_FINE)
           & (ob[:, 1] >= 0) & (ob[:, 1] <= w - G.TILE_FINE))
    ob = np.clip(ob, [0, 0], [h - G.TILE_FINE, w - G.TILE_FINE])
    A = G.gather_tiles(ga, of, G.TILE_FINE)
    B = G.gather_tiles(gb, ob, G.TILE_FINE)
    fok = fg(A, B) & inb
    dF, rhoF, edF, unF = G.zncc_shift(A, B, G.MAX_RESID, excl=excl)
    del A, B
    rem = (si[:, 1] - dp.real) + 1j * (si[:, 0] - dp.imag)
    resid = (dF[:, 1] + 1j * dF[:, 0]) + rem
    base = fok & (rhoF >= G.RHO_FLOOR) & ~edF & np.isfinite(dF).all(1)
    return resid, base, unF, of.shape[0]


def row(label, resid, base, un, total):
    print(f"  {label:34s} " + " ".join(
        (lambda m: f"{np.percentile(np.abs(m) * 2, 99):6.2f}/{m.size:5d}"
         if m.size >= 20 else f"{'   --':>6}/{m.size:5d}")(resid[base & (un >= u)])
        for u in GRID), flush=True)


def main():
    excl = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"uniqueness sweep, exclusion radius {excl} plane px -- "
          f"p99 residual (sensor px) / tiles kept")
    print(f"  {'case':34s} " + " ".join(f"{'u>=%.2f' % u:>12s}" for u in GRID))
    rng = np.random.default_rng(7)
    ga = G.decode_plane(C.REF_A)["g"]
    k, r2 = G.photon_transfer(ga)

    # --- the three failures
    b = C.add_shot_noise(C.defocus_ramp(C.warp_similarity(ga, **C.TRUE), 5.0), k, r2, rng)
    row("C4 defocus 5.0 (NO motion)", *fine_field(ga, b, (k, r2), excl))
    del b

    for sname, si in [("wrapped-text-1", 60), ("highly-angled-ruler-mm-cpl", 150),
                      ("flat-on-ruler-cpl", 38)]:
        fr = G.frames_of(os.path.join(C.RAW_ROOT, sname))
        p = G.decode_plane(fr[si])["g"]
        q = G.decode_plane(fr[si + 1])["g"]
        row(f"C6 {sname}", *fine_field(p, q, G.photon_transfer(p), excl))
        del p, q

    import rawpy
    with rawpy.imread(C.REF_B) as rr:
        v = rr.raw_image_visible.astype(np.float32)
        pat = np.asarray(rr.raw_pattern)
        bl = float(rr.black_level_per_channel[0])
    hh, ww = v.shape
    q4 = v[: hh // 2 * 2, : ww // 2 * 2].reshape(hh // 2, 2, ww // 2, 2) - bl
    pos = {int(pat[oy, ox]): (oy, ox) for oy in range(2) for ox in range(2)}
    (gy1, gx1), (gy2, gx2) = pos[1], pos[3]
    G1 = np.ascontiguousarray(q4[:, gy1, :, gx1])
    G2 = np.ascontiguousarray(q4[:, gy2, :, gx2])
    row("C7 two greens", *fine_field(G1, G2, G.photon_transfer(G1), excl))
    del v, q4, G1, G2

    # --- the cases that must NOT be destroyed
    row("C1 identity (must stay 0)", *fine_field(ga, ga, (k, r2), excl))
    b = C.add_shot_noise(C.warp_similarity(ga, **C.TRUE), k, r2, rng)
    row("C2 planted similarity", *fine_field(ga, b, (k, r2), excl))
    del b
    cy, cx = C.pick_textured_site(ga, k, r2, 220.0)
    mask = C.disc_mask(ga.shape, cy, cx, 220.0, 24.0)
    moved = np.where(mask, C.shift_subpixel(ga, 1.0, 0.0), ga)
    b = C.add_shot_noise(C.warp_similarity(moved, **C.TRUE), k, r2, rng)
    print("  (C3 row below SHOULD stay high -- it contains real 2.0 sensor px motion)")
    row("C3 planted 2.0 sensor px motion", *fine_field(ga, b, (k, r2), excl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

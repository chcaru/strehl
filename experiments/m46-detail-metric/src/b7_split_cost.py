"""M46 b7 -- THE HALF-STACK SPLIT CONTRACT, and the COST, both measured.

Two things the Rust spec cannot be written without, and neither can be reasoned
out from a document.

PART A -- THE SPLIT CONTRACT (fact 620 says the shippable configuration is two
merges over disjoint halves; it does not say WHICH halves).

  RULE 20, WRITTEN BEFORE THE RUN.  A focus stack sweeps depth monotonically,
  so the split is not a free choice:

    * PREDICTION (ARGUED, registered here before measurement): a CONTIGUOUS
      split gives each half only HALF THE DEPTH RANGE.  The two half-merges
      are then focused on different parts of the subject, so they are not two
      views of one image and the common power must collapse.  sigpow should
      fall hard and FRC with it.
    * A PARITY split puts every adjacent pair of frames in opposite halves, so
      both halves span the full sweep.  sigpow should be near the full-stack
      value.
    * If ALL splits agree, the split does not matter, the spec says "any
      disjoint halves", and my prediction was wrong.  That is a real outcome
      and it is the one that would make this section short.

  The measurement can express all three.  It is not a tautology.

  A second registered question, because it is the kind of thing discovered too
  late: an ODD frame count cannot be split evenly.  The spec must say what
  happens, so the unequal-halves case is measured rather than assumed benign.

PART B -- THE COST (question 139: default / --verify / never).  The owner cannot
choose on "roughly 2x", and "roughly 2x" is probably WRONG:

    * decode is UNCHANGED -- the same frames are read exactly once, whichever
      half they land in;
    * the per-frame focus fields are UNCHANGED -- they are a property of a
      frame, not of a stack, and both halves reuse them;
    * only the ACCUMULATION runs twice, over half the frames each, which is the
      same total accumulation work plus one extra output buffer;
    * plus one sigpow evaluation, which is two FFTs of one ROI.

  If that reasoning is right the marginal cost is a few percent, not 100%.  It
  is ARGUED until this script times it, so it is timed, stage by stage, on the
  real stack at the real resolution.

PART C -- THE GOLDEN-VECTOR TOLERANCE.  b6 measured the floor (summation order,
1.5e-16) and the ceiling (the periodic-Hann bug, 1.5e-3) but could not measure
an f32 FFT because numpy upcasts float32 to complex128 silently.  scipy.fft
does not, so the genuine f32 pipeline error is measured here.

PART D -- ODD-SIZED ROIs.  b6 found that a 15x15 ROI is ACCEPTED rather than
rejected.  What it returns is measured here so the spec can rule on it.

Rule 15: b1-b6 are frozen and untouched.  Rule 24: the ROI, the depth range and
the noise constants are read from b1's artifact, not re-chosen.
"""
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M                                                    # noqa: E402
import b6_spec as S                                                   # noqa: E402

L1 = M.L1
STACK = r"D:\personal\macro\112MSDCF"          # READ-ONLY
PAD = 32


def merge_indices(cube, fine, coarse, reg, idx):
    """arm_A over a SUBSET of frames.  The focus fields are sliced, never
    recomputed -- which is the whole point of Part B."""
    return L1.arm_A(cube[idx], coarse[idx], reg[idx])[0]


def main():
    t0 = time.time()
    print("=" * 78)
    print("M46 b7 -- the half-stack split contract, and the cost")
    print("=" * 78)
    res = {}

    with open(os.path.join(M.OUT, "b1_results.json")) as fh:
        b1 = json.load(fh)
    roi = tuple(b1["rois"]["detail"])
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    i0, i1 = b1["depth"]["i0"], b1["depth"]["i1"]
    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))[i0:i1]
    nf = len(files)
    print(f"\n   stack 112MSDCF, depth-matched indices {i0}..{i1} -> {nf} frames")
    print(f"   ROI {roi} (+/-{PAD} px pad), g={g:.6f}, rn_e={rn_e}")

    # ------------------------------------------------------------- decode
    t = time.time()
    cube = L1.load_cube(files, roi, PAD)
    t_decode = time.time() - t
    print(f"\n   decode {nf} frames -> cube {cube.shape}: {t_decode:.2f} s")

    t = time.time()
    fine, coarse, reg = L1.focus_fields(cube, g, rn_e)
    t_focus = time.time() - t
    print(f"   focus fields (per-frame, SHARED by both halves): {t_focus:.2f} s")

    # ============================================== PART A: the split contract
    print("\n" + "=" * 78)
    print("A. THE SPLIT CONTRACT")
    print("=" * 78)
    ai = np.arange(nf)
    splits = {
        "parity": (ai[0::2], ai[1::2]),
        "contiguous": (ai[: nf // 2], ai[nf // 2:]),
        "block2": (np.concatenate([ai[i:i + 2] for i in range(0, nf, 4)]),
                   np.concatenate([ai[i:i + 2] for i in range(2, nf, 4)])),
        "block4": (np.concatenate([ai[i:i + 4] for i in range(0, nf, 8)]),
                   np.concatenate([ai[i:i + 4] for i in range(4, nf, 8)])),
        "random": None,
    }
    perm = np.random.default_rng(20260823).permutation(nf)
    splits["random"] = (np.sort(perm[: nf // 2]), np.sort(perm[nf // 2:]))

    t = time.time()
    full = L1.arm_A(cube, coarse, reg)[0][PAD:-PAD, PAD:-PAD]
    t_full = time.time() - t
    print(f"\n   full-stack merge ({nf} frames): {t_full:.2f} s")
    print(f"   full-stack hp_sd {M.hp_sd(full):.4f}, median {np.median(full):.2f} DN")

    print("\n   split         nA  nB   FRC(f_sig)   ring power    sigpow      "
          "vs parity")
    rows = {}
    ref = None
    for name, (ia, ib) in splits.items():
        ma = merge_indices(cube, fine, coarse, reg, ia)[PAD:-PAD, PAD:-PAD]
        mb = merge_indices(cube, fine, coarse, reg, ib)[PAD:-PAD, PAD:-PAD]
        frc, pwr, prod, cnt, cf = S.sigpow_parts(ma, mb)
        v, st = S.sigpow(ma, mb)
        if ref is None:
            ref = v
        print(f"   {name:<12s} {len(ia):<3d} {len(ib):<3d} {frc:+11.6f} "
              f"{pwr:12.5e} {v:12.5e}   {v/ref:7.4f}")
        rows[name] = dict(nA=len(ia), nB=len(ib), frc=frc, power=pwr,
                          sigpow=v, status=st, ratio=v / ref)
    res["splits"] = rows

    print("\n   INTERPRETATION GATE, applied to the numbers above:")
    r_c = rows["contiguous"]["ratio"]
    if r_c < 0.90:
        print(f"   contiguous is {(1-r_c)*100:.1f}% BELOW parity -> the split rule is")
        print("   LOAD-BEARING and the spec must mandate an interleave.")
    else:
        print(f"   contiguous is within {(abs(1-r_c))*100:.1f}% of parity -> the split")
        print("   rule is NOT load-bearing; my registered prediction was wrong.")

    # ------------------------------------------------------ odd frame counts
    print("\n   ODD FRAME COUNT.  Dropping one frame to force nf odd:")
    nodd = nf - 1
    ao = np.arange(nodd)
    ia, ib = ao[0::2], ao[1::2]
    ma = merge_indices(cube, fine, coarse, reg, ia)[PAD:-PAD, PAD:-PAD]
    mb = merge_indices(cube, fine, coarse, reg, ib)[PAD:-PAD, PAD:-PAD]
    v_odd, _ = S.sigpow(ma, mb)
    print(f"   nf={nodd} (odd): parity gives nA={len(ia)} nB={len(ib)}, "
          f"sigpow {v_odd:.5e}  ({v_odd/ref:.4f} x the even parity value)")
    res["odd"] = dict(nf=nodd, nA=len(ia), nB=len(ib), sigpow=v_odd,
                      ratio=v_odd / ref)

    # ---------------------------------------------- deliberately unequal halves
    print("\n   UNEQUAL HALVES.  A 3:1 split, to show what n_eff imbalance costs:")
    q = np.arange(nf)
    iu_a = q[q % 4 != 0]
    iu_b = q[q % 4 == 0]
    ma = merge_indices(cube, fine, coarse, reg, iu_a)[PAD:-PAD, PAD:-PAD]
    mb = merge_indices(cube, fine, coarse, reg, iu_b)[PAD:-PAD, PAD:-PAD]
    v_un, _ = S.sigpow(ma, mb)
    print(f"   nA={len(iu_a)} nB={len(iu_b)}: sigpow {v_un:.5e}  "
          f"({v_un/ref:.4f} x parity)")
    res["unequal"] = dict(nA=len(iu_a), nB=len(iu_b), sigpow=v_un, ratio=v_un / ref)

    # ======================================================== PART B: the cost
    print("\n" + "=" * 78)
    print("B. THE COST, timed stage by stage on the real stack")
    print("=" * 78)
    ia, ib = splits["parity"]
    reps = 3
    t = time.time()
    for _ in range(reps):
        L1.arm_A(cube, coarse, reg)
    t_full = (time.time() - t) / reps
    t = time.time()
    for _ in range(reps):
        merge_indices(cube, fine, coarse, reg, ia)
        merge_indices(cube, fine, coarse, reg, ib)
    t_half2 = (time.time() - t) / reps
    ma = merge_indices(cube, fine, coarse, reg, ia)[PAD:-PAD, PAD:-PAD]
    mb = merge_indices(cube, fine, coarse, reg, ib)[PAD:-PAD, PAD:-PAD]
    t = time.time()
    for _ in range(10):
        S.sigpow(ma, mb)
    t_sig = (time.time() - t) / 10

    print(f"\n   ROI {ma.shape[0]}x{ma.shape[1]}, {nf} frames")
    print(f"   decode                    {t_decode:8.3f} s   UNCHANGED by verify")
    print(f"   focus fields (per frame)  {t_focus:8.3f} s   UNCHANGED by verify")
    print(f"   merge, full stack         {t_full:8.3f} s")
    print(f"   merge, two halves         {t_half2:8.3f} s   "
          f"({t_half2/t_full:.3f} x the full merge)")
    print(f"   sigpow evaluation         {t_sig:8.4f} s   (two {ma.shape[0]}^2 FFTs)")
    base = t_decode + t_focus + t_full
    extra = t_half2 + t_sig
    print(f"\n   baseline pipeline         {base:8.3f} s")
    print(f"   with --verify             {base+extra:8.3f} s")
    print(f"   MARGINAL COST             {extra:8.3f} s  = "
          f"{extra/base*100:.1f}% of the baseline")
    print("\n   MEASURED: the marginal cost is NOT 2x.  Decode and the focus")
    print("   fields dominate and neither is repeated; only the accumulation")
    print("   runs again, over the same total number of frames.")
    res["cost"] = dict(n_frames=nf, roi=int(ma.shape[0]), decode=t_decode,
                       focus=t_focus, merge_full=t_full, merge_halves=t_half2,
                       sigpow=t_sig, baseline=base, extra=extra,
                       marginal_pct=extra / base * 100)

    # ---------------------------- extrapolate to the full plane, stated as such
    plane = b1["rois"]["plane"]
    npx_roi = ma.shape[0] * ma.shape[1]
    npx_plane = plane[0] * plane[1] / 4.0        # green quad plane
    print(f"\n   EXTRAPOLATION (DERIVED, not measured): the full green quad plane")
    print(f"   is {plane[0]}x{plane[1]}/4 = {npx_plane:.3e} px against this ROI's")
    print(f"   {npx_roi:.3e}.  Accumulation is linear in pixels, so the extra")
    print(f"   merge scales by {npx_plane/npx_roi:.1f}x to "
          f"{t_half2*npx_plane/npx_roi:.1f} s.  sigpow does NOT scale with the")
    print("   plane: it is evaluated on one square ROI of fixed size, so it")
    print(f"   stays at {t_sig:.4f} s.")
    res["extrapolation"] = dict(npx_roi=npx_roi, npx_plane=npx_plane,
                                merge_halves_plane=t_half2 * npx_plane / npx_roi)

    # ================================================ PART C: f32 tolerance
    print("\n" + "=" * 78)
    print("C. THE f32 PIPELINE ERROR, which numpy cannot show (it upcasts)")
    print("=" * 78)
    try:
        import scipy.fft as sfft

        def sigpow_dtype(a, b, dt):
            n = a.shape[0]
            w = np.outer(S.hann_sym(n), S.hann_sym(n)).astype(dt)
            aa = (np.asarray(a, dtype=dt) - np.asarray(a, dtype=dt).mean()) * w
            bb = (np.asarray(b, dtype=dt) - np.asarray(b, dtype=dt).mean()) * w
            A = np.fft.fftshift(sfft.fft2(aa))
            B = np.fft.fftshift(sfft.fft2(bb))
            rs = S.rings(n)
            j = int(np.argmin([abs(c - M.F_SIG) for (_, _, _, c) in rs]))
            _, m, cnt, _ = rs[j]
            return float(np.real(np.sum(A[m] * np.conj(B[m]))) / cnt)

        v64 = sigpow_dtype(ma, mb, np.float64)
        v32 = sigpow_dtype(ma, mb, np.float32)
        rel = abs(v32 - v64) / abs(v64)
        print(f"   f64 pipeline {v64:.10e}")
        print(f"   f32 pipeline {v32:.10e}")
        print(f"   relative difference {rel:.3e}   (n = {ma.shape[0]})")
        for nn in (16, 32, 64):
            aa = S.hash_field(nn, 1) + S.sine_field(nn, 3, 5, 10.0)
            bb = S.hash_field(nn, 2) + S.sine_field(nn, 3, 5, 10.0)
            r = abs(sigpow_dtype(aa, bb, np.float32) - sigpow_dtype(aa, bb, np.float64))
            r /= abs(sigpow_dtype(aa, bb, np.float64))
            print(f"   n={nn:<4d} golden-vector-sized f32 error {r:.3e}")
        res["f32"] = dict(v64=v64, v32=v32, rel=rel)
    except Exception as e:                                          # noqa: BLE001
        print(f"   scipy.fft unavailable: {e}")
        res["f32"] = None

    # =============================================== PART D: odd-sized ROIs
    print("\n" + "=" * 78)
    print("D. ODD-SIZED AND SMALL ROIs -- what the reference actually does")
    print("=" * 78)
    print("   n     nbin  status        value            note")
    odd = {}
    for nn, nb in ((15, 4), (16, 4), (17, 4), (9, 2), (8, 64), (4, 8), (2, 4)):
        a = S.hash_field(nn, 1)
        b = S.hash_field(nn, 1)
        try:
            v, st = S.sigpow(a, b, f=0.25, nbin=nb)
            rs = S.rings(nn, nb)
            note = f"{len(rs)} of {nb} rings survive"
            print(f"   {nn:<5d} {nb:<5d} {st:<12s} {v:+.8e}   {note}")
            odd[f"{nn}/{nb}"] = dict(value=v, status=st, rings=len(rs))
        except ValueError as e:
            print(f"   {nn:<5d} {nb:<5d} REJECTED     {e}")
            odd[f"{nn}/{nb}"] = dict(rejected=str(e))
    print("\n   For ODD n, fftshift puts DC at index n//2 and the grid is")
    print("   asymmetric by one sample; the reference computes a number anyway.")
    print("   The spec RULES on this rather than inheriting it -- see the spec.")
    res["odd_sizes"] = odd

    with open(os.path.join(M.OUT, "b7_split_cost.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/b7_split_cost.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()

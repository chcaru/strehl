#!/usr/bin/env python3
"""M111 -- the soft gate's n_eff prediction, tested on real data, before rendering.

ORCH asked for the falsifiable consequence: a soft weight must raise `n_eff`
where the merge draws seams and NOT raise it where there is real texture. If it
does not move where predicted, the fix is wrong and we learn it without
rendering anything.

HOW THIS IS A MEASUREMENT AND NOT A MODEL
=========================================
A soft-gate `n_eff` map would normally need the per-pixel, per-frame response
volume, which is not dumped and cannot be without editing `merge_cmd.rs`
(M97's lane). It is not needed.

The boolean gate at threshold g admits exactly the frames whose response gap to
the winner is <= g * sqrt(2) * FOCUS_NOISE_SD. So the dumped boolean `n_eff` map
at gate g IS the empirical CDF of the gap distribution, evaluated at g, at every
pixel independently. A ladder of gates samples that CDF at several points, and
any kernel-weighted sum is then a Stieltjes sum over the bins:

    sum_k w(gap_k) = integral w(z) dN(z) ~= sum_bins w(z_bin) * [N(hi) - N(lo)]

M111 already rendered the ladder 0.25 / 1 / 4 / 16 / 64 / 1e5, so the bins in
units of the gate-4 tolerance are

    [0, 0.0625]  (0.0625, 0.25]  (0.25, 1]  (1, 4]  (4, 16]  (16, inf)

The Gaussian weight is MONOTONE DECREASING in the gap, so evaluating every bin
at its lower edge gives a rigorous UPPER bound on the weighted sums and at its
upper edge a rigorous LOWER bound. Those two bracket the true soft `n_eff`.
Nothing here is fitted, assumed or simulated: the bounds are arithmetic on
measured counts, and they are reported as bounds.

Masks come from the SINGLE-FRAME CONTROL, never from a rendered arm, per
discipline 752 and M111's own section 13 retraction.
"""

import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage as ndi

RENDER = r"C:\dev\strehl-out\M111\render"
ORCH = r"C:\dev\strehl-out\ORCH-thennow"
OUT = r"C:\dev\strehl-out\M111"

FOCUS_NOISE_SD = 0.015_214
SQRT2 = np.sqrt(2.0)
DEFAULT_GATE = 4.0
TOL4 = DEFAULT_GATE * SQRT2 * FOCUS_NOISE_SD  # 0.086063
WEIGHT_FLOOR = 1.0 / 65536.0
CUTOFF = np.sqrt(-2.0 * np.log(WEIGHT_FLOOR))  # 4.7096 tolerances

# (gate, dumped file) -- the ladder M111 rendered.
LADDER = [(0.25, "state-g0p25/n_eff_gate0.25.npy"),
          (1.0, "state-g1/n_eff_gate1.00.npy"),
          (2.0, "state-g2/n_eff_gate2.00.npy"),
          (3.0, "state-g3/n_eff_gate3.00.npy"),
          (4.0, "state-g4/n_eff_gate4.00.npy"),
          (5.0, "state-g5/n_eff_gate5.00.npy"),
          (6.0, "state-g6/n_eff_gate6.00.npy"),
          (8.0, "state-g8/n_eff_gate8.00.npy"),
          (10.0, "state-g10/n_eff_gate10.00.npy"),
          (12.0, "state-g12/n_eff_gate12.00.npy"),
          (14.0, "state-g14/n_eff_gate14.00.npy"),
          (16.0, "state-g16/n_eff_gate16.00.npy"),
          (64.0, "state-g64/n_eff_gate64.00.npy"),
          (100000.0, "state-g100000/n_eff_gate100000.00.npy")]


def gauss(z):
    """The soft gate's kernel, truncated exactly as softgate.rs truncates it."""
    z = np.asarray(z, dtype=np.float64)
    w = np.exp(-0.5 * z * z)
    return np.where((z >= CUTOFF) | (w < WEIGHT_FLOOR), 0.0, w)


def tophat(z):
    """The BOOLEAN gate's kernel: admit inside one gate-4 tolerance, else not.

    This is the negative control per discipline 751 -- it disables the one thing
    under test (the kernel's shape) and leaves the masks, the bins, the Kish
    estimator and the verdict logic exactly as they are. It also has a known
    ground truth: summed over the ladder it must reconstruct the gate-4 map
    EXACTLY, which is the only check that the Stieltjes bin counts are right.
    """
    return (np.asarray(z, dtype=np.float64) <= 1.0).astype(np.float64)


KERNEL = gauss
SWAP_MASKS = False


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(p):
    y = luma(tifffile.imread(p))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndi.uniform_filter(y, k, mode="nearest")
    m2 = ndi.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def main():
    maps, edges = [], []
    for gate, rel in LADDER:
        n = np.load(os.path.join(RENDER, rel)).astype(np.float64)
        maps.append(n)
        edges.append(gate / DEFAULT_GATE)  # gap threshold in gate-4 tolerances
    h = min(m.shape[0] for m in maps)
    w = min(m.shape[1] for m in maps)
    # The state maps must all come from one registration, so a shape mismatch
    # among them is an error, not something to crop away. Only the control is
    # allowed a different crop.
    shapes = {m.shape for m in maps}
    if len(shapes) != 1:
        raise SystemExit(f"ladder maps disagree on shape: {sorted(shapes)}")
    maps = [m[:h, :w] for m in maps]

    yc = plane_luma(os.path.join(ORCH, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif"))
    # The control was cropped differently from the state dumps; take the common
    # extent across every array, cropping only (never resampling), so a single
    # index means the same sensor location in all of them.
    h = min(h, yc.shape[0])
    w = min(w, yc.shape[1])
    maps = [m[:h, :w] for m in maps]
    yc = yc[:h, :w]
    inner = np.zeros((h, w), bool)
    inner[64:-64, 64:-64] = True
    sdc = local_sd(yc)
    thr = float(np.percentile(sdc[inner], 40.0))
    flat = (sdc <= thr) & inner                       # subject has no texture here
    textured = (sdc >= float(np.percentile(sdc[inner], 90.0))) & inner

    # Monotonicity of the ladder is a precondition: N(g) must be non-decreasing
    # in g at every pixel, or the maps do not come from one gap distribution.
    bad = 0
    for a, b in zip(maps, maps[1:]):
        bad += int(np.count_nonzero(b < a - 1e-6))
    print("=" * 96)
    print("M111 -- soft-gate n_eff prediction, from the measured gap CDF")
    print("=" * 96)
    print(f"plane {w}x{h}   gate-4 tolerance {TOL4:.6f}   Gaussian cutoff {CUTOFF:.4f} tol")
    print(f"ladder monotonicity violations: {bad} of {len(maps[0].ravel())*(len(maps)-1)} "
          f"({'OK' if bad == 0 else 'THE LADDER IS NOT ONE DISTRIBUTION'})")
    if bad:
        raise SystemExit("ladder is not monotone; the CDF reading is invalid")

    # Stieltjes bounds. Bin j spans (edges[j-1], edges[j]]; count = N_j - N_{j-1}.
    lo_edges = [0.0] + edges[:-1]
    counts = [maps[0]] + [maps[j] - maps[j - 1] for j in range(1, len(maps))]

    sw_hi = np.zeros((h, w))
    sw_lo = np.zeros((h, w))
    sw2_hi = np.zeros((h, w))
    sw2_lo = np.zeros((h, w))
    for c, zlo, zhi in zip(counts, lo_edges, edges):
        whi, wlo = KERNEL(zlo), KERNEL(zhi)   # monotone decreasing => lower edge is heavier
        sw_hi += c * whi
        sw_lo += c * wlo
        sw2_hi += c * whi * whi
        sw2_lo += c * wlo * wlo

    with np.errstate(divide="ignore", invalid="ignore"):
        soft_hi = np.where(sw2_lo > 0, sw_hi ** 2 / np.maximum(sw2_lo, 1e-30), 0.0)
        soft_lo = np.where(sw2_hi > 0, sw_lo ** 2 / np.maximum(sw2_hi, 1e-30), 0.0)
    # Look the shipped arm up BY GATE VALUE, never by position. This line read
    # `maps[2]` and was correct for the six-rung ladder, where position 2 was
    # gate 4.0; inserting gates 2 and 3 silently moved it to the gate-2 map and
    # changed both the ratio's denominator and the seam population's own
    # definition, with no error and no shape change to give it away.
    hits = [i for i, (g, _) in enumerate(LADDER) if g == DEFAULT_GATE]
    if len(hits) != 1:
        raise SystemExit(f"ladder must contain gate {DEFAULT_GATE} exactly once, found {len(hits)}")
    boolean = maps[hits[0]]

    if KERNEL is tophat:
        # Ground truth. A top-hat at one gate-4 tolerance IS the boolean gate,
        # and its discontinuity sits exactly on a ladder edge, so within every
        # bin the kernel is constant at its right edge: the LOWER bound must
        # reconstruct the gate-4 map exactly. The upper bound evaluates each
        # bin at its LEFT edge, so it legitimately over-counts the one bin
        # (1.00, 1.25] -- the frames between gate 4 and gate 5 -- and nothing
        # else. Both halves are asserted, so this cannot be satisfied by a
        # reconstruction that is merely close.
        d_lo = float(np.max(np.abs(sw_lo - boolean)))
        print(f"  top-hat: lower bound vs the gate-4 map, max |diff| = {d_lo:.6g} (must be 0)")
        if d_lo > 1e-6:
            raise SystemExit("STIELTJES BIN COUNTS ARE WRONG -- the ladder does not "
                             "reconstruct a kernel whose answer is known")
        g5 = [i for i, (g, _) in enumerate(LADDER) if g == 5.0]
        if len(g5) != 1:
            raise SystemExit("control needs gate 5.0 in the ladder to predict the slack")
        slack = maps[g5[0]] - boolean
        d_hi = float(np.max(np.abs((sw_hi - sw_lo) - slack)))
        print(f"  top-hat: upper-minus-lower vs the gate4->gate5 count, max |diff| = {d_hi:.6g} (must be 0)")
        print(f"           that slack is up to {float(np.max(slack)):.0f} frames, which is why the")
        print("           top-hat is the loosest case for this machinery and the smooth")
        print("           Gaussian is the tightest.")
        if d_hi > 1e-6:
            raise SystemExit("STIELTJES UPPER BOUND IS NOT THE PREDICTED BIN -- the bound "
                             "arithmetic is wrong")

    if SWAP_MASKS:
        flat, textured = textured, flat

    print("\nPREDICTION: the soft/boolean n_eff ratio is LARGER in flat regions")
    print("            (where the merge draws seams) than in textured regions.\n")
    print("  %-26s %9s %14s %14s %12s" %
          ("population", "bool n_eff", "soft n_eff lo", "soft n_eff hi", "ratio range"))
    res = {}
    for nm, m in (("flat (control-defined)", flat),
                  ("  of which elected <=8", flat & (boolean <= 8)),
                  ("  of which averaged >=64", flat & (boolean >= 64)),
                  ("textured (control-defined)", textured),
                  ("whole inner plane", inner)):
        b = float(np.median(boolean[m]))
        sl = float(np.median(soft_lo[m]))
        sh = float(np.median(soft_hi[m]))
        rl, rh = sl / max(b, 1e-9), sh / max(b, 1e-9)
        res[nm.strip()] = {"n": int(m.sum()), "boolean_med": b,
                           "soft_lo_med": sl, "soft_hi_med": sh,
                           "ratio_lo": rl, "ratio_hi": rh}
        print("  %-26s %9.1f %14.2f %14.2f   %5.2f - %5.2f" % (nm, b, sl, sh, rl, rh))

    seam = res["of which elected <=8"]
    tex = res["textured (control-defined)"]
    print("\nVERDICT")
    print("  seam population  (flat, elected): ratio %.2f - %.2f" % (seam["ratio_lo"], seam["ratio_hi"]))
    print("  texture population              : ratio %.2f - %.2f" % (tex["ratio_lo"], tex["ratio_hi"]))
    # A zero-detection is never self-explaining. These are BOUNDS, so three
    # outcomes are possible and only two of them are about the fix: the
    # intervals can separate one way, separate the other way, or overlap --
    # and overlap is a statement about the ladder's resolution, not about the
    # soft gate. Reporting overlap as a refutation would be the same error as
    # reporting a null detection from an instrument never shown to be live.
    if seam["ratio_lo"] > tex["ratio_hi"]:
        print("  PREDICTION HELD -- the intervals are DISJOINT and ordered as predicted.")
        verdict = "HELD (disjoint)"
    elif tex["ratio_lo"] > seam["ratio_hi"]:
        print("  PREDICTION REFUTED -- the intervals are DISJOINT and ordered the")
        print("  WRONG WAY: the soft gate raises n_eff in texture more than at seams.")
        print("  On ORCH's own terms the fix is wrong.")
        verdict = "REFUTED (disjoint, wrong order)"
    else:
        print("  UNRESOLVED -- the intervals OVERLAP. This is the ladder's resolution,")
        print("  NOT a verdict on the fix. The Gaussian falls from 0.607 to 0.0003")
        print("  across z = 1 to 4, so a bin spanning that range cannot bound the")
        print("  weighted sum usefully. Refine the ladder in z = 1..4 and re-run;")
        print("  do not report this as a refutation.")
        verdict = "UNRESOLVED (bounds overlap)"
    print("  bound width: seam %.2fx, texture %.2fx  (1.00x would be an exact answer)"
          % (seam["ratio_hi"] / max(seam["ratio_lo"], 1e-9),
             tex["ratio_hi"] / max(tex["ratio_lo"], 1e-9)))

    # How much of the plane does the soft gate change at all?
    changed = float(np.mean((soft_lo > boolean + 0.5)[inner]))
    print("\n  soft n_eff exceeds boolean by >0.5 on %.2f%% of the inner plane" % (100 * changed))

    tag = ("tophat" if KERNEL is tophat else "gauss") + ("-swapped" if SWAP_MASKS else "")
    with open(os.path.join(OUT, f"softgate_prediction-{tag}.json"), "w") as fh:
        json.dump({"verdict": verdict, "populations": res, "tol4": TOL4,
                   "kernel": tag, "cutoff_tolerances": float(CUTOFF)}, fh, indent=1)
    print(f"\nwrote softgate_prediction-{tag}.json")
    return verdict


USAGE = """usage: softgate_prediction.py [test | control-tophat | control-swap]

  test            the Gaussian soft gate against the boolean gate. Expect HELD.
  control-tophat  same machinery, kernel replaced by the boolean gate's own
                  top-hat. The soft arm then IS the boolean arm, so the ratio
                  must be 1.00 in both populations and the verdict must NOT be
                  HELD. Fires if the separation comes from the bookkeeping or
                  the masks rather than from the kernel's shape.
  control-swap    Gaussian kernel, flat and textured masks exchanged. The
                  verdict must inv./REFUTED. Fires if the verdict logic is not
                  wired to the populations it names.
"""

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    if mode == "test":
        expect = ("HELD (disjoint)",)
    elif mode == "control-tophat":
        KERNEL = tophat
        expect = ("UNRESOLVED (bounds overlap)",)
    elif mode == "control-swap":
        SWAP_MASKS = True
        expect = ("REFUTED (disjoint, wrong order)",)
    else:
        raise SystemExit(USAGE)
    print(f"[mode {mode}]  expecting verdict in {expect}")
    got = main()
    ok = got in expect
    print(f"\n[mode {mode}]  verdict {got!r}  expected {expect}  -> {'PASS' if ok else 'FAIL'}")
    # Distinct codes so a harness fault can never be read as a measurement.
    sys.exit(0 if ok else 1)

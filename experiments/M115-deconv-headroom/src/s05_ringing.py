"""M115 s05 -- the ringing control, and the matched-contrast comparison.

The brief is explicit: ringing is the failure mode that will make this look good
and be wrong.  Deconvolution overshoots at edges; the overshoot reads as
'sharper' to the eye and to gradient metrics.  s03's control C3b already showed
a naive gradient metric being moved 8.25x by a post-filter carrying no
information, so that warning is not hypothetical here.

Two instruments, both of which can only fire on structure that was in NO input
frame:

  OUT-OF-RANGE.  For every output pixel, [min_k Y_k, max_k Y_k] over the aligned
  stack is the convex hull of the evidence.  Selection and averaging cannot
  leave it -- their outputs are convex combinations, so 0.000% is the reading
  they MUST give, and any nonzero reading is manufactured contrast.  M41
  measured 63.966%/81.249% for the unguarded estimator by this route.

  OVERSHOOT vs DISTANCE FROM EDGE.  Ringing is not merely out-of-range, it is
  out-of-range AT A CHARACTERISTIC DISTANCE from a hard edge.  A flat excess
  everywhere is noise amplification; a peak at 2-6 px is a halo.  Reporting the
  profile distinguishes them; reporting only a scalar cannot.

Then the matched-contrast test, which is the decision-relevant comparison:
control C3 proved SNR is invariant to any post-filter, so 'deconvolve' and
'gate then sharpen' can be compared directly by sharpening the gate output to
the SAME contrast and measuring what the noise did.
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner

DF = 0.01
STACKS = ["109MSDCF", "119MSDCF"]


def edge_distance(ref):
    """Distance in px to the nearest strong edge, by repeated dilation of a
    gradient-threshold mask.  Rule 23: sobel is applied to this single 2-D
    plane, not to a stack."""
    from scipy import ndimage
    gy, gx = np.gradient(ref.astype(np.float64))
    g = np.hypot(gy, gx)
    thr = np.percentile(g, 99.0)
    mask = g >= thr
    return ndimage.distance_transform_edt(~mask), mask


def ringing(stack, log):
    banner(f"ringing control -- {stack} EDGE ROI")
    roi = tuple(json.load(open(os.path.join(L.OUT, "s01_rois.json")))[stack]["edge_roi"])
    files = L.stack_files(os.path.join(
        json.load(open(os.path.join(L.OUT, "s01_rois.json")))[stack]["dir"]))
    cube = L.load_cube(files, roi)
    iso = L.iso_of(files[0])
    g, rn_e = L.noise_params(iso)
    B = roi[2]
    crop = L.crop_fn(L.PAD, B)
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s0, _, _ = L.calibrate_s(cube, coarse)
    arms = L.run_all_arms(cube, g, rn_e, s0)

    lo = crop(cube.min(0)).astype(np.float64)
    hi = crop(cube.max(0)).astype(np.float64)
    rng = np.maximum(hi - lo, 1e-6)
    ref = crop(arms["BEST1"]).astype(np.float64)
    dist, mask = edge_distance(ref)
    print(f"  edge mask covers {100*mask.mean():.2f}% of the ROI; "
          f"stack hull width median {np.median(rng):.1f} DN")

    bins = [(0, 1), (1, 2), (2, 4), (4, 8), (8, 16), (16, 10 ** 6)]
    out = {}
    print(f"\n  {'arm':12s} {'out-of-range %':>15s} {'p99.9 excess/hull':>18s}   "
          + " ".join(f"{a}-{b}px" for a, b in bins))
    for a in L.ARMS:
        o = crop(arms[a]).astype(np.float64)
        exc = np.maximum(o - hi, 0.0) + np.maximum(lo - o, 0.0)
        oor = exc > 0
        frac = float(100.0 * oor.mean())
        p999 = float(np.percentile(exc / rng, 99.9))
        prof = []
        for a0, b0 in bins:
            m = (dist >= a0) & (dist < b0)
            prof.append(float(100.0 * oor[m].mean()) if m.any() else float("nan"))
        out[a] = dict(oor_pct=frac, p999_excess=p999, profile=prof,
                      bins=[list(b) for b in bins])
        print(f"  {a:12s} {frac:15.4f} {p999:18.5f}   "
              + " ".join(f"{p:7.3f}" for p in prof))
    conv = all(out[a]["oor_pct"] < 0.001 for a in ["BEST1", "FRAME*", "FRAME_PIX",
                                                   "GATE", "MEAN"])
    print(f"\n  convex arms read 0.000%: {conv}  <- this is the control on the")
    print(f"  control: an instrument that cannot report 0 for a convex")
    print(f"  combination is not measuring manufactured contrast at all.")
    log.setdefault("ringing", {})[stack] = dict(rows=out, convex_zero=bool(conv),
                                                edge_frac=float(mask.mean()))
    return out


def matched_contrast(stack, log):
    """C3 proved SNR is invariant to post-filtering.  So the honest question is
    not 'is WIENER sharper than GATE' -- it is trivially arrangeable either way
    -- but 'at the SAME contrast, which is cleaner'.  Sharpen GATE to WIENER's
    measured contrast per frequency and compare the noise directly."""
    banner(f"matched-contrast comparison -- {stack} detail ROI")
    cube, g, rn_e, B = load_detail(stack)
    crop = L.crop_fn(L.PAD, B)
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s0, _, _ = L.calibrate_s(cube, coarse)
    sp = L.split_channel(cube, g, rn_e, s0, crop, want=["GATE", "WIENER", "FRAME*"])
    rb = L.RadialBins(B, DF)
    mid = rb.band_mask(*L.MIDBAND)
    st = {a: L.split_stats(rb, *sp[a]) for a in ["GATE", "WIENER", "FRAME*"]}

    # the gain that takes GATE's contrast to WIENER's, per radial bin
    ratio = np.sqrt(np.maximum(st["WIENER"][0], 0) / np.maximum(st["GATE"][0], 1e-30))
    c = rb.centres

    def af(f):
        return np.interp(f, c, ratio, left=ratio[0], right=ratio[-1])

    A2 = L.freq_gain(sp["GATE"][0], af)
    B2 = L.freq_gain(sp["GATE"][1], af)
    Ps2, Pn2, snr2, _ = L.split_stats(rb, A2, B2)
    gs = np.sqrt(Ps2[mid] / np.maximum(st["WIENER"][0][mid], 1e-30))
    gn = np.sqrt(Pn2[mid] / np.maximum(st["WIENER"][1][mid], 1e-30))
    print(f"  {'f':>7s} {'contrast match':>15s} {'noise: sharpened GATE / WIENER':>32s}")
    for i, f in enumerate(c[mid]):
        print(f"  {f:7.3f} {gs[i]:15.4f} {gn[i]:32.4f}")
    print(f"\n  mean over mid band: contrast match {gs.mean():.4f}, "
          f"noise ratio {gn.mean():.4f}")
    print(f"  a noise ratio near 1.00 means the deconvolution delivered nothing")
    print(f"  that sharpening the shipped gate does not already deliver.")
    log.setdefault("matched", {})[stack] = dict(
        f=c[mid].tolist(), contrast_match=gs.tolist(), noise_ratio=gn.tolist(),
        mean_contrast_match=float(gs.mean()), mean_noise_ratio=float(gn.mean()))
    return float(gn.mean())


def main():
    t0 = time.time()
    log = {}
    for st in STACKS:
        ringing(st, log)
    for st in STACKS:
        matched_contrast(st, log)
    json.dump(log, open(os.path.join(L.OUT, "s05_ringing.json"), "w"), indent=2)
    print(f"\nelapsed {time.time()-t0:.1f}s -> s05_ringing.json")


if __name__ == "__main__":
    main()

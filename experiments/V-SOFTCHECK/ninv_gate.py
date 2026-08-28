"""N-INVARIANCE ACCEPTANCE GATE -- callable by the re-certification harness.

THE CRITERION.  At a MATCHED focus range, doubling the number of frames must not make
the merge measurably softer at 0.30-0.35 cyc/output-px on the tiles where sharpness is
defined.

    depth_cost = median over high-contrast tiles of log10( S_fewer / S_more )

positive means the deeper merge is softer.  Normalised per doubling of N.

STANDING BASELINES, both measured at the SHIP-V4 pin 44C2F2CD2E5B2894, matched range,
identical development gain, top two contrast deciles, 0.30-0.35 cyc/output-px:

    113MSDCF    N= 32 ->  63   +0.0712 dex   92.2% of tiles   (N=63 is 14.9% softer)
    bee-1-cpl   N=149 -> 299   +0.0748 dex   86.9% of tiles   (N=299 is 18.8% softer)

Two subjects, a 4.7x difference in depth, the same cost per doubling to within 0.004
dex.  THRESHOLD is set at +0.0200 dex per doubling: below both baselines by 3.5x and
above the widest measured CI half-width (+-0.014 dex on bee) by 1.4x, so a pass is
distinguishable from the present state rather than merely inside the error bar.

WHY THE GATE READS HIGH-CONTRAST TILES AND REPORTS THE FLAT ONES SEPARATELY.
Pooled over a uniform tile grid this effect reads ZERO, because the deeper merge loses
detail on texture (+0.075 dex) and simultaneously adds energy on flat ground
(-0.045 dex), and the two cancel.  A gate that pooled them would certify a merge with
two defects as clean.  So the gate reports both ends and never averages them.

TWO WAYS A FIX COULD PASS THIS GATE WITHOUT IMPROVING THE IMAGE, both blocked here:
  1. Make the SHALLOW arm worse.  The ratio improves with no gain.  Blocked by
     `absolute_more`: the deep arm's own textured-tile band power is reported and the
     harness must require it not to fall against its recorded baseline.
  2. Blur both arms equally.  The ratio is unchanged, so this cannot pass -- but it
     would move `absolute_more`, which is why that number is mandatory, not advisory.

USAGE
    import ninv_gate
    r = ninv_gate.evaluate(fewer_tiff, more_tiff, n_fewer, n_more, subject="bee-1-cpl",
                           binary_sha=sha256_of_the_binary_that_rendered_both_arms)
    assert r["verdict"] == "PASS", r["why"]

INSTRUMENT IDENTITY.  This is not a print gate.  Three instruments in this project now emit
PASS/FAIL: `orch_printready.py` (PASS/FAIL/ACQUITTED), `printcert4.py` (blotch/rim/sharp/dust)
and this one (N-invariance only).  They are not comparable and must not be reconciled.
Every result carries `instrument` so a verdict cannot be quoted without its source.
"""
import os, sys, json, numpy as np, softcheck as S, hsel as HS
import dmeasure as DM
import d113recon as RC
import ncurve as NC

BAND = DM.B_MAIN            # 0.30-0.35 cyc/output-px
TOP_FRAC = 0.20             # top two contrast deciles
FLAT_FRAC = 0.20
THRESHOLD = 0.0200          # dex per doubling of N, pre-registered above
MIN_TILES = 60
# The baselines were measured at the SHIP-V4 pin and belong to THAT binary.  Dividing a
# HEAD measurement by them is a cross-binary comparison and will manufacture a win out of
# nothing -- the same error class as the withdrawn 17 PASS / 5 FAIL print-gate diff.  The
# PASS/FAIL verdict itself is binary-independent, because depth_cost compares two arms
# rendered by the SAME binary; only fraction_of_baseline_removed is unsafe, and it is now
# withheld unless the caller states a binary that matches.
BASELINE_BINARY = "44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490"
BASELINE = {"113MSDCF": 0.0712, "bee-1-cpl": 0.0748}
INSTRUMENT = "ninv_gate.py (V-SOFTCHECK N-invariance)"

def _audit(paths):
    """Trap 1: both sides of every ratio must be developed identically."""
    seen = {}
    for p in paths:
        lg = p + ".log"
        if not os.path.exists(lg): raise RuntimeError("no render log for %s" % p)
        ln = [l.strip() for l in open(lg, encoding="utf-8", errors="replace")
              if l.startswith("exposure")]
        if not ln: raise RuntimeError("no exposure line in %s" % lg)
        seen[p] = ln[0]
    if len(set(seen.values())) != 1:
        raise RuntimeError("arms developed at DIFFERENT gain, no ratio is valid: %s" % seen)
    return list(seen.values())[0]

def _bands(path_fewer, path_more):
    ref = DM.load(path_more)
    oy, ox = HS.all_tiles(ref.shape)
    d_lo = RC.lopow(ref, oy, ox)
    p_more, _ = DM.bandpow(ref, oy, ox)
    im = DM.load(path_fewer)
    sy, sx, _ = HS.align(ref, im, oy, ox)
    p_few, _ = DM.bandpow(im, oy + sy, ox + sx)
    del im, ref
    return p_few, p_more, d_lo, (sy, sx)

def evaluate(path_fewer, path_more, n_fewer, n_more, subject=None, band=BAND,
             binary_sha=None):
    if n_more <= n_fewer: raise ValueError("n_more must exceed n_fewer")
    gauge = _audit([path_fewer, path_more])
    p_few, p_more, d_lo, shift = _bands(path_fewer, path_more)
    x = p_few[:, band]; y = p_more[:, band]
    g = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(d_lo)
    idx = np.where(g)[0]; order = idx[np.argsort(d_lo[idx])]
    if len(order) < MIN_TILES:
        return dict(verdict="REFUSED", why="only %d usable tiles, floor is %d"
                    % (len(order), MIN_TILES))
    top = order[int(round(len(order) * (1 - TOP_FRAC))):]
    flat = order[:int(round(len(order) * FLAT_FRAC))]
    cost = float(np.median(np.log10(x[top] / y[top])))
    ci = RC.boot_mor(x[top], y[top])
    doub = float(np.log2(n_more / n_fewer))
    per = cost / doub
    res = dict(subject=subject, n_fewer=int(n_fewer), n_more=int(n_more),
               band="%.2f-%.2f cyc/output-px" % (DM.E[band], DM.E[band + 1]),
               gauge=gauge, shift=list(shift), tiles_top=int(len(top)),
               tiles_flat=int(len(flat)),
               depth_cost=cost, ci=[float(ci[0]), float(ci[1])],
               doublings=doub, depth_cost_per_doubling=per,
               sign_frac=float((x[top] > y[top]).mean()),
               flat_excess=float(np.median(np.log10(x[flat] / y[flat]))),
               absolute_more=float(np.median(y[top])),
               threshold=THRESHOLD)
    res["instrument"] = INSTRUMENT
    res["binary_sha"] = binary_sha
    same_binary = (binary_sha is not None
                   and binary_sha.upper() == BASELINE_BINARY.upper())
    res["baseline_comparable"] = bool(same_binary)
    if subject in BASELINE and BASELINE[subject] > 0:
        if same_binary:
            res["fraction_of_baseline_removed"] = float(1.0 - per / BASELINE[subject])
        else:
            res["fraction_of_baseline_removed"] = None
            res["baseline_withheld"] = (
                "baseline %+.4f dex was measured at binary %s; caller stated %s. A ratio "
                "across binaries measures the two builds, not the fix." %
                (BASELINE[subject], BASELINE_BINARY[:16],
                 (binary_sha or "NO BINARY STATED")[:16]))
    res["verdict"] = "PASS" if per <= THRESHOLD else "FAIL"
    res["why"] = ("%+.4f dex per doubling of N at matched range, %s threshold %+.4f"
                  % (per, "within" if per <= THRESHOLD else "OVER", THRESHOLD))
    return res

def commission(path_fewer, path_more, n_fewer, n_more):
    """Both directions plus a null, on the real arms, before any verdict is believed.
      NULL      the same file on both sides -> exactly 0.0000 dex and must PASS
      DEGRADE   blur the DEEP arm -> depth_cost must RISE and the gate must FAIL
      IMPROVE   sharpen the DEEP arm -> depth_cost must FALL
    A gate that only ever moves one way cannot score a fix, so IMPROVE is mandatory."""
    print("COMMISSIONING the N-invariance gate")
    p_few, p_more, d_lo, _ = _bands(path_fewer, path_more)
    x = p_few[:, BAND]; y = p_more[:, BAND]
    if np.allclose(y[np.isfinite(y)], y[np.isfinite(y)][0]):
        sys.exit("  ABORT: band power is constant, a null on it would be trivial")
    def cost_of(a, b):
        g = (a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b) & np.isfinite(d_lo)
        i = np.where(g)[0]; o = i[np.argsort(d_lo[i])]
        t = o[int(round(len(o) * (1 - TOP_FRAC))):]
        return float(np.median(np.log10(a[t] / b[t])))
    base = cost_of(x, y)
    print("    live arms      depth_cost %+.6f dex" % base)
    nul = cost_of(y, y)
    print("    NULL same arm  depth_cost %+.6f dex   (must be exactly 0)" % nul)
    # The plants are applied to PIXELS and pushed back through the whole statistic.
    # Scaling the band-power array instead would shift depth_cost by exactly
    # log10(1/s) whatever the image contained -- arithmetic that cannot fail, which is
    # the short-circuited-control failure this project has now seen three times.
    ref = DM.load(path_more)
    oy, ox = HS.all_tiles(ref.shape)
    plants = {"DEGRADE blur sigma 1.0": NC.gauss(ref, 1.0),
              "IMPROVE unsharp +0.7": (ref + 0.7 * (ref - NC.gauss(ref, 1.0))).astype(np.float32)}
    got = {}
    for tag, arr in plants.items():
        if np.array_equal(arr, ref): sys.exit("  ABORT: %s is an INERT plant" % tag)
        moved = float(np.mean(np.abs(arr - ref)))
        pw, _ = DM.bandpow(arr, oy, ox)
        got[tag] = cost_of(x, pw[:, BAND])
        print("    %-24s depth_cost %+.6f dex   (mean |dpx| %.4f)" % (tag, got[tag], moved))
    del ref, plants
    deg = got["DEGRADE blur sigma 1.0"]; imp = got["IMPROVE unsharp +0.7"]
    ok = (abs(nul) < 1e-12) and (deg > base + 0.02) and (imp < base - 0.02)
    if not ok: sys.exit("  COMMISSIONING FAILED -- gate is not free to move in both directions")
    print("    verdict flips: DEGRADE %s / IMPROVE %s"
          % ("FAIL" if deg > THRESHOLD else "PASS", "FAIL" if imp > THRESHOLD else "PASS"))
    print("  COMMISSIONING PASSED\n")

PAIRS = [("113MSDCF", r"C:\dev\strehl-out\V-SOFTCHECK\dilut\113MSDCF\N032.tiff",
          r"C:\dev\strehl-out\V-SOFTCHECK\dilut\113MSDCF\N063.tiff", 32, 63),
         ("bee-1-cpl", r"C:\dev\strehl-out\V-SOFTCHECK\dilut\bee-1-cpl\R149x2.tiff",
          r"C:\dev\strehl-out\V-SOFTCHECK\dilut\bee-1-cpl\R299x1.tiff", 149, 299)]

if __name__ == "__main__":
    commission(*PAIRS[0][1:])
    out = []
    for subj, a, b, na, nb in PAIRS:
        r = evaluate(a, b, na, nb, subject=subj)
        out.append(r)
        print("%-12s N %3d -> %3d  %s" % (subj, na, nb, r["band"]))
        print("   depth_cost      %+.4f dex  CI [%+.4f,%+.4f]  %.1f%% of tiles"
              % (r["depth_cost"], r["ci"][0], r["ci"][1], 100 * r["sign_frac"]))
        print("   per doubling    %+.4f dex   threshold %+.4f   ==> %s"
              % (r["depth_cost_per_doubling"], r["threshold"], r["verdict"]))
        print("   flat_excess     %+.4f dex   (same pixels, opposite defect, never pooled)"
              % r["flat_excess"])
        print("   absolute_more   %.6g   (deep arm textured band power; must not fall)\n"
              % r["absolute_more"])
    d = r"C:\dev\strehl-out\V-SOFTCHECK\dilut\ninv_gate.json"
    json.dump(out, open(d, "w"), indent=1, default=float)
    print("machine-readable: %s" % d)

"""N-invariance read on the tiles where sharpness is DEFINED, at depth.

WHY THIS EXISTS.  d113measure.py read the 113MSDCF pair over a uniform tile grid and
got -0.0007 dex -- no depth effect.  d113recon.py then showed that number is the sum of
two defects of opposite sign that cancel:

    flattest decile   -0.1708 dex   the 63-frame merge holds 48% MORE 0.30-0.35 energy
    top two deciles   +0.0712 dex   the 63-frame merge holds 15% LESS 0.30-0.35 energy

A merge that both loses real detail on texture AND injects energy into flat areas gets
a clean bill of health from any statistic that averages the two.  That is the trap this
project has hit repeatedly ("on blotch alone the worst arm wins"), and it is why every
number below is reported per contrast decile with the flat end shown, never pooled.

ARMS (bee-1-cpl, all rendered by drender.py at the SHIP-V4 pin, --srgb --exposure 1.50):
  P = R150x1  N=150 step 1 range 0-149
  Q = R149x2  N=149 step 2 range 0-298
  R = R299x1  N=299 step 1 range 0-298

  A1p  Q -> R   RANGE HELD 0-298, N 149->299.  No range confound, no mask needed.
                The deep analogue of 113MSDCF N=32 -> N=63.
  A3   P -> Q   N held ~150, step doubles.  Noise-matched by construction.
                Range differs, so it is read on the NEAR tiles only and flagged.

Contrast deciles are cut on low-band (0.02-0.05 cyc/px) energy of ONE arm, a scene
property in a band disjoint from every reported band, so the cut cannot prefer tiles
where either arm happens to be sharp in the band being reported.
"""
import os, sys, json, numpy as np, softcheck as S, hsel as HS
import dmeasure as DM
import d113recon as RC

DIL = DM.DIL
T = DM.T
ARM = {"P": os.path.join(DIL, "R150x1.tiff"),
       "Q": os.path.join(DIL, "R149x2.tiff"),
       "R": os.path.join(DIL, "R299x1.tiff")}
CMP = [("A1p", "Q", "R", 149, 299, "RANGE HELD 0-298, N 149->299", True),
       ("A3",  "P", "Q", 150, 149, "N held ~150, step 1->2, range differs", False)]

def audit():
    print("EXPOSURE AUDIT")
    seen = {}
    for k, p in ARM.items():
        ln = [l.strip() for l in open(p + ".log", encoding="utf-8", errors="replace")
              if l.startswith("exposure")]
        if not ln: sys.exit("ABORT: %s has no exposure line" % k)
        print("  %s  %s" % (k, ln[0])); seen[k] = ln[0]
    if len(set(seen.values())) != 1: sys.exit("ABORT: arms at different gain: %s" % seen)
    print("  identical -- ratios are gain-free\n")

def _top(x, y, d, frac):
    g = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(d)
    idx = np.where(g)[0]; order = idx[np.argsort(d[idx])]
    sl = order[int(round(len(order) * (1 - frac))):]
    return float(np.median(np.log10(x[sl] / y[sl]))), float((x[sl] > y[sl]).mean()), len(sl)

def cutcheck(pw, d_R, d_Q):
    """Is the contrast cut moved by the defect it is stratifying?

    The deciles are cut on 0.02-0.05 cyc/px energy of ONE arm.  Mottle is
    low-frequency, so a merge that injects mottle could in principle inflate its own
    cut variable and sort tiles differently.  Two controls:

      (a) cut on the OTHER arm (Q, N=149) instead of R (N=299).  If the reported
          effect moves materially, the cut is contaminated.
      (b) sweep the cut fraction.  A real contrast dependence is a gradient, not a
          threshold, so the number must vary smoothly and keep its sign.
    """
    x = pw["Q"][:, DM.B_MAIN]; y = pw["R"][:, DM.B_MAIN]
    g = np.isfinite(d_R) & np.isfinite(d_Q)
    print("CUT ROBUSTNESS  (A1p, 0.30-0.35 cyc/output-px)")
    sp = float(np.log10(np.nanmax(d_R[g]) / np.nanmin(d_R[g][d_R[g] > 0])))
    dif = float(np.nanmedian(np.abs(np.log10(d_Q[g] / d_R[g]))))
    print("    cut variable spans %.2f dex; arms differ on it by %.4f dex (median |log ratio|)"
          % (sp, dif))
    if dif > 0.25 * sp:
        sys.exit("    ABORT: arms disagree on the cut variable by more than a quarter of its span")
    print("    -> the arm-to-arm disagreement is %.1f%% of the span, so rank is set by scene"
          % (100 * dif / sp))
    rr = np.corrcoef(np.log10(d_R[g]), np.log10(d_Q[g]))[0, 1]
    print("    rank agreement between arms: pearson r = %.5f on log cut variable" % rr)
    print("    frac   cut on R (N=299)          cut on Q (N=149)")
    for fr in (0.10, 0.20, 0.30, 0.40):
        mR, sR, nR = _top(x, y, d_R, fr)
        mQ, sQ, nQ = _top(x, y, d_Q, fr)
        print("    %.2f   %+.4f dex %5.1f%% n=%3d    %+.4f dex %5.1f%% n=%3d"
              % (fr, mR, 100*sR, nR, mQ, 100*sQ, nQ))
    m1, _, _ = _top(x, y, d_R, 0.20); m2, _, _ = _top(x, y, d_Q, 0.20)
    if m1 * m2 <= 0:
        sys.exit("    ABORT: the two cuts disagree in SIGN -- stratification is not trustworthy")
    print("    -> both cuts agree in sign at every fraction; effect is a gradient, not a threshold\n")

def main():
    audit()
    ref = DM.load(ARM["R"])
    oy, ox = HS.all_tiles(ref.shape)
    print("uniform grid: %d tiles of %d px on %s\n" % (len(oy), T, str(ref.shape)))
    d_lo = RC.lopow(ref, oy, ox)
    pw = {}; alt = {}
    for k, p in ARM.items():
        im = ref if k == "R" else DM.load(p)
        sy, sx, _ = HS.align(ref, im, oy, ox)
        a, _ = DM.bandpow(im, oy + sy, ox + sx)
        pw[k] = a
        if k == "Q": alt["Q"] = RC.lopow(im, oy + sy, ox + sx)
        print("  arm %s  shift(%+d,%+d)  in bounds %d" % (k, sy, sx, int(np.isfinite(a[:, 0]).sum())))
        if k != "R": del im
    print()
    cutcheck(pw, d_lo, alt["Q"])
    out = {}
    for tag, lo_arm, hi_arm, nlo, nhi, desc, clean in CMP:
        a = pw[lo_arm]; b = pw[hi_arm]
        print("=" * 74)
        print("%s   %s (N=%d)  ->  %s (N=%d)   %s" % (tag, lo_arm, nlo, hi_arm, nhi, desc))
        if not clean:
            print("  RANGE DIFFERS -- confounded in favour of any depth story; read with care")
        for band, bname in ((DM.B_MAIN, "0.30-0.35"), (DM.B_PROM, "0.20-0.25")):
            x = a[:, band]; y = b[:, band]
            g = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(d_lo)
            idx = np.where(g)[0]; order = idx[np.argsort(d_lo[idx])]
            k10 = len(order) // 10
            pooled = float(np.median(np.log10(x[order] / y[order])))
            print("  band %s cyc/output-px   %d tiles   POOLED %+.4f dex" % (bname, len(order), pooled))
            print("    decile   n    median lowband     dex      %% tiles fewer-N sharper")
            rows = []
            for d in range(10):
                sl = order[d*k10:(d+1)*k10] if d < 9 else order[9*k10:]
                m = float(np.median(np.log10(x[sl] / y[sl])))
                fr = float((x[sl] > y[sl]).mean())
                rows.append(dict(decile=d, n=len(sl), lowband=float(np.median(d_lo[sl])),
                                 dex=m, sign=fr))
                print("      %2d    %3d   %15.4g   %+.4f      %5.1f%%"
                      % (d, len(sl), np.median(d_lo[sl]), m, 100*fr))
            top = order[8*k10:]
            mt = float(np.median(np.log10(x[top] / y[top])))
            ft = float((x[top] > y[top]).mean())
            ci = RC.boot_mor(x[top], y[top])
            print("    TOP TWO DECILES (%d tiles): %+.4f dex CI [%+.4f,%+.4f]  %.1f%% -- N=%d is %+.1f%% %s"
                  % (len(top), mt, ci[0], ci[1], 100*ft, nhi, abs(100*(10**mt - 1)),
                     "SOFTER" if mt > 0 else "sharper"))
            bot = order[:2*k10]
            mb = float(np.median(np.log10(x[bot] / y[bot])))
            print("    FLAT TWO DECILES (%d tiles): %+.4f dex -- N=%d holds %+.1f%% %s energy here"
                  % (len(bot), mb, nhi, abs(100*(10**(-mb) - 1)), "MORE" if mb < 0 else "LESS"))
            out["%s|%s" % (tag, bname)] = dict(pooled=pooled, top=mt, top_ci=list(ci),
                                               top_sign=ft, flat=mb, deciles=rows)
        # spectrum across every band, flat end vs textured end, same pixels
        idx = np.where(np.isfinite(d_lo) & np.isfinite(a[:, 0]) & np.isfinite(b[:, 0]))[0]
        order = idx[np.argsort(d_lo[idx])]; k10 = len(order) // 10
        print("  FULL SPECTRUM, dex, fewer-N over more-N, same pixels:")
        print("    %-18s %s" % ("band", "  ".join("%.2f-%.2f" % (DM.E[i], DM.E[i+1])
                                                  for i in range(DM.NB))))
        for lbl, sl in (("flat 2 deciles", order[:2*k10]), ("top 2 deciles", order[8*k10:])):
            vals = [float(np.median(np.log10(a[sl, i] / b[sl, i]))) for i in range(DM.NB)]
            print("    %-18s %s" % (lbl, "  ".join("%+9.4f" % v for v in vals)))
            out["%s|spectrum|%s" % (tag, lbl)] = vals
        print()
    np.savez_compressed(os.path.join(DIL, "dstrat_tiles.npz"), d_lo=d_lo,
                        **{"pw_" + k: pw[k] for k in ARM})
    p = os.path.join(DIL, "dstrat.json"); json.dump(out, open(p, "w"), indent=1, default=float)
    print("machine-readable: %s" % p)

if __name__ == "__main__":
    main()

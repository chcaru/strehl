"""Why does flower-bud-alone-cpl read >1?  Either the merge really sharpens on
this subject, or my registration failed and the denominator is read at the
wrong place.  Distinguish them."""
import numpy as np
from analyze import load
for subj in ("119MSDCF","coffee-bubbles","109MSDCF","flower-bud-alone-cpl"):
    c = load(subj,"lin",128); N=int(c["N"])
    rms = np.asarray(c["reg_rms"]); kept = np.asarray(c["reg_kept"])
    F = np.asarray(c["f_mid_none"]); M = np.asarray(c["m_mid_none"]); lo=np.asarray(c["m_lo"])
    sel = lo>=np.quantile(lo,0.50)
    lm = np.asarray(c["m_lv"]); lf = np.asarray(c["f_lv"])
    print(f"\n=== {subj}  N={N}")
    print(f"  fit rms px: median {np.median(rms):.2f} p90 {np.quantile(rms,.9):.2f} max {rms.max():.2f}"
          f" | rms>2px {(rms>2).sum()}/{N}  rms>8px {(rms>8).sum()}/{N} | anchors kept median {np.median(kept):.0f}")
    print(f"  LEVEL gauge master/mean-frame = {lm[sel].mean()/lf.mean(0)[sel].mean():.5f}  (1.0 = identically developed)")
    am = F[:,sel].argmax(0)
    print(f"  distinct winning frames {len(np.unique(am))}/{N}")
    # displacement sensitivity measured ON THIS SUBJECT
    r0 = np.median(M[sel]/F[:,sel].max(0))
    for k in ("off_0_0","off_8_0","off_24_24"):
        Fk = np.asarray(c[f"f_mid_{k}"])
        print(f"  deliberate reference offset {k:10s} -> {np.median(M[sel]/Fk[:,sel].max(0)):.4f}"
              + ("   <-- baseline" if k=="off_0_0" else ""))
    good = rms <= 2.0
    if 3 <= good.sum() < N:
        rg = np.median(M[sel]/F[good][:,sel].max(0))
        print(f"  ratio, all {N} frames                 = {r0:.4f}")
        print(f"  ratio, {good.sum()} frames with rms<=2px      = {rg:.4f}"
              f"   (fewer frames => order stat biases UP; a FALL means the bad frames were inflating)")
        wr = rms[am]
        print(f"  rms of the WINNING frame: median {np.median(wr):.2f}, "
              f"{100*(wr>2).mean():.0f}% of sites won by an rms>2px frame")

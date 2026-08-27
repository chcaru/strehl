"""Is the half-pair primitive viable at all?

The smoke test found A and B offset by dx=-2 on the first ROI and coherence
collapsing to ~0 above 0.20 cyc/px.  Either that is uncorrected translation --
in which case an integer shift fixes it -- or the two independent align solves
put real sub-pixel structure in different places, in which case the primitive
cannot see the band this whole investigation is about, and that is the finding.

The warpmap digest is enforced (warpmap.rs:108: "this warp map was fitted on
stack X ... but was applied to Y"), so the halves CANNOT share a solve; the
misregistration is structural, not an oversight.  What saves the pre/post
comparison is that 113-A-g0 and 113-A-g1 share ONE warpmap and 113-B-g0 and
113-B-g1 share ANOTHER, so whatever A-vs-B residual exists is IDENTICAL in the
g0 pair and the g1 pair and divides out of C_g1/C_g0.  It does not divide out
of any absolute comparison.  This script measures how big it is.
"""
import sys

import numpy as np

import h2
import rois

R = r"C:\dev\strehl-out\V-H2H2\renders"
L = r"C:\dev\strehl-out\V-H2H2\logs"
T = 256
PAD = 32


def load(tag):
    return h2.Render(rf"{R}\{tag}.tiff", log=rf"{L}\{tag}.log", name=tag)


def fine_coherence(fa, fb, t, nbin=48):
    """gamma(f) on a fine radial grid, accumulated across ROIs by the caller."""
    r = h2.radial(t)
    edges = np.linspace(0.0, 0.5, nbin + 1)
    idx = np.clip(np.digitize(r.ravel(), edges) - 1, 0, nbin - 1)
    pa = (np.abs(fa) ** 2).ravel()
    pb = (np.abs(fb) ** 2).ravel()
    cc = np.real(fa * np.conj(fb)).ravel()
    PA = np.bincount(idx, pa, nbin)
    PB = np.bincount(idx, pb, nbin)
    CC = np.bincount(idx, cc, nbin)
    return PA, PB, CC, edges


def run(subject, gather, roiset, label, shifts_from=None):
    A = load(f"{subject}-A-{gather}")
    B = load(f"{subject}-B-{gather}")
    nbin = 48
    accPA = np.zeros(nbin)
    accPB = np.zeros(nbin)
    accCC = np.zeros(nbin)
    accCC_raw = np.zeros(nbin)
    shifts = []
    used = 0
    dropped_clip = 0
    dropped_peak = 0
    for (y, x) in roiset:
        ca, na = A.crop(y, x, T)
        if shifts_from is not None:
            dy, dx, pk = shifts_from[(y, x)]
        else:
            cb0, _ = B.crop(y, x, T)
            dy, dx, pk = h2.integer_shift(ca, cb0)
        if abs(dy) > PAD or abs(dx) > PAD:
            dropped_peak += 1
            continue
        cb, nb = B.crop(y + dy, x + dx, T)
        if na or nb:
            dropped_clip += 1
            continue
        shifts.append((dy, dx, pk))
        fa = h2.contrast_fft(ca)
        fb = h2.contrast_fft(cb)
        if fa is None or fb is None:
            dropped_clip += 1
            continue
        PA, PB, CC, edges = fine_coherence(fa, fb, T, nbin)
        accPA += PA
        accPB += PB
        accCC += CC
        cb_raw, _ = B.crop(y, x, T)
        fbr = h2.contrast_fft(cb_raw)
        accCC_raw += fine_coherence(fa, fbr, T, nbin)[2]
        used += 1
    tot = len(roiset)
    assert used + dropped_clip + dropped_peak == tot
    print(f"\n[{subject} {gather} {label}] ROIs: {tot} = used {used} + "
          f"clipped-after-shift {dropped_clip} + shift-out-of-range {dropped_peak}")
    if used == 0:
        return None
    sh = np.array([(s[0], s[1]) for s in shifts])
    print(f"  integer shift A->B  dy median {np.median(sh[:,0]):+.1f} "
          f"[{sh[:,0].min():+d},{sh[:,0].max():+d}]   "
          f"dx median {np.median(sh[:,1]):+.1f} [{sh[:,1].min():+d},{sh[:,1].max():+d}]")
    uniq = len(set(map(tuple, sh)))
    print(f"  distinct shifts {uniq} of {used} ROIs "
          f"({'UNIFORM translation' if uniq == 1 else 'field-varying -> scale/rotation between solves'})")
    g = accCC / np.sqrt(np.maximum(accPA * accPB, 1e-300))
    graw = accCC_raw / np.sqrt(np.maximum(accPA * accPB, 1e-300))
    ctr = 0.5 * (edges[:-1] + edges[1:])
    print("   f      gamma(shifted)  gamma(raw)   P_A")
    for i in range(nbin):
        if ctr[i] > 0.5:
            break
        print(f"  {ctr[i]:.3f}   {g[i]:+8.4f}      {graw[i]:+8.4f}   {accPA[i]:.3e}")
    return dict(f=ctr, gamma=g, gamma_raw=graw, PA=accPA, PB=accPB, C=accCC,
                shifts=sh, used=used)


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "113"
    ref = load(f"{subject}-A-g1")
    detail, flat, counts = rois.census(ref, t=T, pad=PAD)
    rng = np.random.default_rng(11)
    d = [detail[i] for i in rng.permutation(len(detail))[:40]]
    f = [flat[i] for i in rng.permutation(len(flat))[:25]]
    for gather in ("g0", "g1"):
        run(subject, gather, d, "DETAIL")
    run(subject, "g1", f, "FLAT")


if __name__ == "__main__":
    sys.exit(main())

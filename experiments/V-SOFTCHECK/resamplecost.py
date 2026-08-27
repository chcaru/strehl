"""Price the coverage/alignment resample that the reference frames receive.

Compares STREHL_ONLY_FRAME=k rendered with alignment ON (a CatmullRom warp at
coverage ~0.9974) against the SAME frame with STREHL_ALIGN=0 (no warp at all),
in the same band, at registered tiles.  If this ratio is ~1.0 the reference is
effectively unresampled and the master's own per-frame warp is NOT common-mode.
"""
import os, numpy as np, softcheck as S
from analyze import load
c = load("119MSDCF","lin",128); oy, ox = c["oy"], c["ox"]; T = 128
d = os.path.join(S.ROOT,"lin","119MSDCF"); dn = os.path.join(S.ROOT,"noalign","119MSDCF")
lo = c["m_lo"]; sel = lo >= np.quantile(lo, 0.50)
for k in (9,16,25):
    A = S.load_luma(os.path.join(d, f"f{k:03d}.tiff"), "lin")     # warped (my reference)
    B = S.load_luma(os.path.join(dn, f"f{k:03d}.tiff"), "lin")    # unwarped
    coef, rms, kp, tot = S.register(A, B)
    dd = S.disp_at(coef, oy+T/2.0, ox+T/2.0)
    ry = np.clip(np.round(oy+dd[:,0]).astype(int),0,A.shape[0]-T)
    rx = np.clip(np.round(ox+dd[:,1]).astype(int),0,A.shape[1]-T)
    a = S.tile_means(S.dog(A,S.S_MID)**2, oy, ox, T)
    b = S.tile_means(S.dog(B,S.S_MID)**2, ry, rx, T)
    ah = S.tile_means(S.dog(A,S.S_HI)**2, oy, ox, T)
    bh = S.tile_means(S.dog(B,S.S_HI)**2, ry, rx, T)
    print(f"frame {k:2d}: warped/unwarped E_mid = {np.median(a[sel]/b[sel]):.4f}   "
          f"E_hi = {np.median(ah[sel]/bh[sel]):.4f}   (reg rms {rms:.2f}px, kept {kp}/{tot})")

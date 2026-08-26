"""V-bestframe controls. Every one of these can come out red; that is the point.

C1  merge pushed through the FRAME-side code path at s=1, t=0.
    Must reproduce the merge-side numbers EXACTLY. Tests the tile mapping,
    the band scaling and the tone fit as an identity.
C2  synthetic frame = merge resampled by a KNOWN (s, t). Registration must
    recover (s, t). Also measures the resampling penalty, since the synthetic
    frame is the only arm in this whole study that was ever resampled.
C3  a BLURRED merge fed in as a frame. The merge must now WIN by a large
    margin -- the sign must reverse. An instrument that cannot report a large
    positive is not able to report a large negative either.
"""
import numpy as np
from pathlib import Path
from scipy import ndimage
import bestframe as B

GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
SUBJ = ("bee-1-cpl", "flowers-cpl")


def frame_path_on(img, mL, m8, s, t, ye, xe):
    xs, ys, cov = B.fit_tone(m8, B.boxdown(img, 8), s, t)
    fT = B.apply_tone_fast(img, B.tone_lut(xs, ys))
    st, oob = B.frame_tile_stats(fT, s, t, ye, xe)
    return st, oob, cov


for subj in SUBJ:
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    h, w = mL.shape
    ye = B.tile_edges(h, B.NTY); xe = B.tile_edges(w, B.NTX)
    m8 = B.boxdown(mL, 8); m16 = B.boxdown(mL, 16)
    mt = B.tile_stats(mL, ye, xe)
    print(f"\n===== {subj}  merge {h}x{w}")

    # ---- C1 --------------------------------------------------------------
    st, oob, cov = frame_path_on(mL, mL, m8, 1.0, (0.0, 0.0), ye, xe)
    for b, lab in ((1, "FINE"), (2, "MID ")):
        dmax = float(np.nanmax(np.abs(st[:, :, b] - mt[:, :, b])))
        rel = dmax / float(np.nanmedian(mt[:, :, b]))
        print(f"  C1 {lab} identity: max|frame-path - merge-path| = {dmax:.3e} DN "
              f"({100*rel:.4f}% of median)  {'PASS' if rel < 1e-6 else 'FAIL'}  "
              f"oob={oob} tone_cov={cov:.4f}")

    # ---- C2 --------------------------------------------------------------
    for s_true, tx, ty in ((0.9400, 200.0, 150.0), (0.9900, -40.0, 60.0)):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        syn = ndimage.map_coordinates(mL, [s_true * yy + ty, s_true * xx + tx],
                                      order=3, mode="nearest").astype(np.float32)
        # syn(Q) = merge(s*Q + t) -- so registering merge against syn should give
        # merge(Q) ~ syn(s'Q + t') with s' = 1/s_true ... no: syn IS the frame, and
        # by construction merge(P) is at syn((P - t)/s). Registration solves
        # merge(Q) ~ frame(s_r*Q + t_r); here frame=syn, so s_r = 1/s_true.
        sr, tr, peak = B.register2(m16, B.boxdown(syn, 16), down=16)
        print(f"  C2 planted s={s_true:.4f} t=({tx:+.0f},{ty:+.0f}) -> recovered "
              f"s={sr:.4f} (expect {1/s_true:.4f}, err {sr-1/s_true:+.4f}) "
              f"t=({tr[0]:+.1f},{tr[1]:+.1f}) peak={peak:.3f}")
        st, oob, cov = frame_path_on(syn, mL, m8, sr, tr, ye, xe)
        for b, lab in ((1, "FINE"), (2, "MID ")):
            mc, _ = B.corrected(mt[:, :, 0], mt[:, :, b])
            fc, _ = B.corrected(st[:, :, 0], st[:, :, b])
            r = np.nanmedian(np.where(fc > 0, mc / np.maximum(fc, 1e-9), np.nan))
            print(f"     C2 {lab} median merge/synthetic = {r:.3f}  "
                  f"(>1 = the resampling penalty on the synthetic arm)")

    # ---- C3 --------------------------------------------------------------
    for sig in (0.8, 1.5, 3.0):
        bl = ndimage.gaussian_filter(mL, sig)
        st, oob, cov = frame_path_on(bl, mL, m8, 1.0, (0.0, 0.0), ye, xe)
        line = f"  C3 blur sigma={sig:4.1f} as a frame:"
        for b, lab in ((1, "FINE"), (2, "MID")):
            mc, _ = B.corrected(mt[:, :, 0], mt[:, :, b])
            fc, fl = B.corrected(st[:, :, 0], st[:, :, b])
            r = np.where(fc > 0, mc / np.maximum(fc, 1e-9), np.nan)
            win = np.nanmean(r > 1.0)
            line += f"   {lab} median merge/blur = {np.nanmedian(r):7.3f}, merge wins {100*win:5.1f}% of tiles"
        print(line)

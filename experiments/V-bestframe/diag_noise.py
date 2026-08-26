"""Is 'merge < best frame in 88.6% of tiles' detail, or is it the max of 36 noise
draws? Look at the raw per-frame distribution inside single tiles before believing
any summary built on top of it."""
import sys
import numpy as np
import analyse as A

for subj in sys.argv[1:]:
    d = A.load(subj, "base")
    mt, ft = d["merge_tiles"], d["frame_tiles"]
    nf = ft.shape[0]
    print(f"\n===== {subj}  {nf} frames")
    for band, lab in ((1, "FINE"), (2, "MID")):
        E = ft[:, :, :, band] ** 2                  # per-frame band POWER per tile
        Em = mt[:, :, band] ** 2
        F = np.nanpercentile(E, 10, axis=0)         # per-tile floor FROM THE FRAMES
        Emax = np.nanmax(E, axis=0)
        Emed = np.nanmedian(E, axis=0)
        exc = Emax / np.maximum(F, 1e-12)
        print(f"  --- {lab}: Emax/F over 352 tiles  "
              f"p05 {np.percentile(exc,5):.3f}  p25 {np.percentile(exc,25):.3f}  "
              f"med {np.median(exc):.3f}  p75 {np.percentile(exc,75):.3f}  "
              f"p95 {np.percentile(exc,95):.3f}  max {exc.max():.1f}")
        print(f"      frac of tiles with Emax/F < 1.25 (indistinguishable from a "
              f"36-draw noise max): {100*np.mean(exc<1.25):.1f}%")
        rel = np.nanstd(E, axis=0) / np.maximum(np.nanmean(E, axis=0), 1e-12)
        print(f"      per-tile relative spread of E across frames: med {np.median(rel):.4f} "
              f"(pure-noise expectation ~sqrt(2/Neff))")
        print(f"      merge power / frame p10 floor: med {np.median(Em/np.maximum(F,1e-12)):.4f}")
    # a few named tiles, FINE band
    E = ft[:, :, :, 1] ** 2; Em = mt[:, :, 1] ** 2
    F = np.nanpercentile(E, 10, axis=0); exc = np.nanmax(E, axis=0) / np.maximum(F, 1e-12)
    order = np.argsort(-exc.ravel())
    picks = list(order[:3]) + list(order[len(order)//2:len(order)//2+2]) + list(order[-3:])
    print(f"  tile        merge_rms  fr_p10   fr_med   fr_max   Emax/F   merge/fr_p10  argmax_k")
    for o in picks:
        i, j = np.unravel_index(o, exc.shape)
        e = E[:, i, j]
        print(f"  ({i:2d},{j:2d})   {np.sqrt(Em[i,j]):8.2f} {np.sqrt(F[i,j]):8.2f} "
              f"{np.sqrt(np.median(e)):8.2f} {np.sqrt(e.max()):8.2f} {exc[i,j]:8.2f} "
              f"{np.sqrt(Em[i,j]/max(F[i,j],1e-12)):11.3f}  k={int(d['frame_index'][int(np.argmax(e))])}")

"""Are MY masters clipped?  ORCH reports 11 of 18 HEAD --auto-exposure masters BLOWN.

My arms are neither HEAD nor --auto-exposure: pin 44C2F2CD2E5B2894 with an explicit
--exposure.  But +2.33 stops is a 5.03x push and the question is empirical, so this
measures it instead of asserting it.

The metrological point ORCH makes is the one that matters here: a saturated region has
no structure, and every number I reported is band POWER on textured tiles.  So the
audit is not only whole-frame -- it is run on the EXACT top-two-decile tiles the
+0.0748 dex headline was measured on.  Clipping outside those tiles cannot touch it;
clipping inside them would.
"""
import os, sys, numpy as np, tifffile, softcheck as S, hsel as HS
import dmeasure as DM
import d113recon as RC

HI = 65535
NEAR = 65000
ARMS = [("113MSDCF", r"C:\dev\strehl-out\V-SOFTCHECK\dilut\113MSDCF\N032.tiff", None),
        ("113MSDCF", r"C:\dev\strehl-out\V-SOFTCHECK\dilut\113MSDCF\N063.tiff", "ref113"),
        ("bee-1-cpl", r"C:\dev\strehl-out\V-SOFTCHECK\dilut\bee-1-cpl\R149x2.tiff", None),
        ("bee-1-cpl", r"C:\dev\strehl-out\V-SOFTCHECK\dilut\bee-1-cpl\R299x1.tiff", "refbee")]

def top_tiles(ref_path):
    ref = DM.load(ref_path)
    oy, ox = HS.all_tiles(ref.shape)
    d = RC.lopow(ref, oy, ox)
    g = np.isfinite(d); idx = np.where(g)[0]
    order = idx[np.argsort(d[idx])]
    top = order[int(round(len(order) * 0.8)):]
    del ref
    return oy[top], ox[top]

def main():
    print("CLIP AUDIT -- pin 44C2F2CD2E5B2894, --srgb --exposure, no --auto-exposure\n")
    tiles = {"ref113": top_tiles(ARMS[1][1]), "refbee": top_tiles(ARMS[3][1])}
    key = {"113MSDCF": "ref113", "bee-1-cpl": "refbee"}
    print("%-10s %-9s %9s %9s %9s %10s %12s" %
          ("subject", "arm", "clip_all", "clip_any", "near_any", "median", "clip_in_top"))
    worst = 0.0
    for subj, path, _ in ARMS:
        a = tifffile.imread(path)
        assert a.ndim == 3 and a.shape[2] == 3, (path, a.shape)
        mx = a.max(axis=2); mn = a.min(axis=2)
        n = a.shape[0] * a.shape[1]
        clip_all = 100.0 * float((mn >= HI).sum()) / n
        clip_any = 100.0 * float((mx >= HI).sum()) / n
        near_any = 100.0 * float((mx >= NEAR).sum()) / n
        lum = 0.25 * a[:, :, 0].astype(np.float32) + 0.5 * a[:, :, 1] + 0.25 * a[:, :, 2]
        med = float(np.median(lum))
        oy, ox = tiles[key[subj]]
        T = DM.T; sat = (mx >= HI)
        cnt = 0; tot = 0
        for y, x in zip(oy, ox):
            if y < 0 or x < 0 or y + T > a.shape[0] or x + T > a.shape[1]: continue
            cnt += int(sat[y:y+T, x:x+T].sum()); tot += T * T
        in_top = 100.0 * cnt / max(tot, 1)
        worst = max(worst, in_top, clip_any)
        print("%-10s %-9s %8.4f%% %8.4f%% %8.4f%% %10.0f %11.4f%%" %
              (subj, os.path.basename(path).replace(".tiff", ""),
               clip_all, clip_any, near_any, med, in_top))
        del a, mx, mn, lum, sat
    print("\nORCH's BLOWN threshold is >25%% clipped; a pure-white median is %d." % HI)
    if worst > 1.0:
        print("VERDICT: CLIPPING PRESENT above 1%% -- band-power numbers must be re-taken.")
        sys.exit(2)
    print("VERDICT: worst reading %.4f%%, below 1%%. No saturated structure in the measured"
          % worst)
    print("         tiles, so the +0.0748 dex headline is not a clipping artifact.")

if __name__ == "__main__":
    main()

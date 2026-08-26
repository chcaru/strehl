"""V-bestframe driver. Two passes:

  PASS 1 (cheap)  raw Bayer green per frame -> per-frame (s, t, peak), then a
                  robust linear fit of s(k), tx(k), ty(k). Focus breathing and
                  stage drift are smooth in k, so frames too defocused to
                  register directly are still placed. Frames placed by model
                  rather than measurement are COUNTED, never silently mixed in.
  PASS 2 (full)   rawpy postprocess -> tone match -> per-tile band RMS on the
                  frame's own grid at the mapped tile.

Every per-tile number is cached to npz; all analysis is offline.
"""
import argparse, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage
import bestframe as B

RAW = Path(r"D:\personal\macro")
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--nframes", type=int, default=24)
    ap.add_argument("--plant-sigma", type=float, default=0.0)
    ap.add_argument("--plant-tiles", default="")
    ap.add_argument("--reg-bias", default="")     # "ds,dtx,dty" sensitivity control
    ap.add_argument("--merge-only", default="")   # reuse frame side from this tag
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    subj = a.subject
    OUT.mkdir(parents=True, exist_ok=True)

    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    mh, mw = mL.shape
    ye = B.tile_edges(mh, B.NTY); xe = B.tile_edges(mw, B.NTX)
    plant = (-1, -1, -1, -1)
    if a.plant_sigma > 0:
        i0, i1, j0, j1 = (int(v) for v in a.plant_tiles.split(","))
        msk = np.zeros((mh, mw), np.float32); msk[ye[i0]:ye[i1], xe[j0]:xe[j1]] = 1.0
        msk = ndimage.gaussian_filter(msk, 32.0)   # feather: a step edge would ADD hf
        mL = mL * (1 - msk) + ndimage.gaussian_filter(mL, a.plant_sigma) * msk
        plant = (i0, i1, j0, j1)
        print(f"PLANT gaussian sigma={a.plant_sigma} over tiles rows[{i0}:{i1}] "
              f"cols[{j0}:{j1}] = {(i1-i0)*(j1-j0)} of {B.NTY*B.NTX} tiles")
    m_tiles = B.tile_stats(mL, ye, xe)
    m_reg = B.boxdown(mL, 16); m8 = B.boxdown(mL, 8)
    del mL

    if a.merge_only:
        src = np.load(OUT / f"{subj}__{a.merge_only}.npz", allow_pickle=False)
        d = {k: src[k] for k in src.files}
        d["merge_tiles"] = m_tiles
        d["plant_sigma"] = a.plant_sigma
        d["plant_tiles"] = np.array(plant)
        np.savez_compressed(OUT / f"{subj}__{a.tag}.npz", **d)
        print(f"MERGE-ONLY: frame side reused verbatim from {subj}__{a.merge_only}.npz "
              f"({d['frame_tiles'].shape[0]} frames) -> {subj}__{a.tag}.npz")
        return

    fs = sorted((RAW / subj).glob("*.ARW"))
    if not fs:
        print(f"NO FRAMES for {subj}"); sys.exit(2)
    pick = np.unique(np.linspace(0, len(fs) - 1, min(a.nframes, len(fs))).round().astype(int))
    nf = len(pick)
    print(f"{subj}: merge {mh}x{mw}  {len(fs)} ARW on disk  reading {nf} "
          f"(every ~{len(fs)/nf:.1f}th)  grid {B.NTY}x{B.NTX}={B.NTY*B.NTX} tiles")

    # ---- PASS 1 -----------------------------------------------------------
    t00 = time.time()
    raw = np.zeros((nf, 4))
    for n, k in enumerate(pick):
        g = B.raw_green_half(fs[k])
        s, t, peak = B.register2(m_reg, B.boxdown(g, 8), down=16)
        raw[n] = (s, t[0], t[1], peak)
    w = np.where(raw[:, 3] >= B.PEAK_OK, raw[:, 3] ** 2, 0.0)
    if w.sum() == 0:
        w = raw[:, 3] ** 2
    cs, ks = B.robust_line(pick, raw[:, 0], w)
    cx, kx = B.robust_line(pick, raw[:, 1], w)
    cy, ky = B.robust_line(pick, raw[:, 2], w)
    inl = ks & kx & ky
    S = np.polyval(cs, pick); TX = np.polyval(cx, pick); TY = np.polyval(cy, pick)
    direct = raw[:, 3] >= B.PEAK_OK
    use_s = np.where(direct, raw[:, 0], S)
    use_x = np.where(direct, raw[:, 1], TX)
    use_y = np.where(direct, raw[:, 2], TY)
    res = np.abs(raw[inl, 0] - S[inl])
    print(f"  PASS1 {time.time()-t00:.0f}s  s(k) = {cs[0]:+.6f}*k {cs[1]:+.4f}  "
          f"inliers {int(inl.sum())}/{nf}  |s residual| med {np.median(res) if res.size else np.nan:.4f} "
          f"max {res.max() if res.size else np.nan:.4f}")
    print(f"  PASS1 placed DIRECTLY (peak>={B.PEAK_OK}): {int(direct.sum())}/{nf}   "
          f"placed BY MODEL: {int((~direct).sum())}/{nf}")
    if a.reg_bias:
        ds, dtx, dty = (float(v) for v in a.reg_bias.split(","))
        use_s = use_s + ds; use_x = use_x + dtx; use_y = use_y + dty
        print(f"  REG-BIAS control: s{ds:+.4f} tx{dtx:+.1f} ty{dty:+.1f}")

    # ---- PASS 2 -----------------------------------------------------------
    F = np.full((nf, B.NTY, B.NTX, 3), np.nan)
    oobs = np.zeros(nf, int); cov = np.zeros(nf)
    for n, k in enumerate(pick):
        t0 = time.time()
        fL = B.luma(B.decode(fs[k])).astype(np.float32)
        s, t = float(use_s[n]), (float(use_x[n]), float(use_y[n]))
        xs, ys, frac = B.fit_tone(m8, B.boxdown(fL, 8), s, t)
        fT = B.apply_tone_fast(fL, B.tone_lut(xs, ys)); del fL
        st, oob = B.frame_tile_stats(fT, s, t, ye, xe); del fT
        F[n] = st; oobs[n] = oob; cov[n] = frac
        print(f"  [{n+1:3d}/{nf}] {fs[k].name} s={s:.4f} t=({t[0]:+7.1f},{t[1]:+7.1f}) "
              f"{'direct' if direct[n] else 'MODEL '} peak={raw[n,3]:.3f} cov={frac:.3f} "
              f"oob={oob} {time.time()-t0:.1f}s", flush=True)

    tag = a.tag or ("plant" if a.plant_sigma > 0 else "base")
    np.savez_compressed(
        OUT / f"{subj}__{tag}.npz",
        merge_tiles=m_tiles, frame_tiles=F, reg_raw=raw,
        reg_used=np.stack([use_s, use_x, use_y], 1), reg_direct=direct,
        oob=oobs, tone_cov=cov, frame_index=pick,
        frame_names=np.array([fs[k].name for k in pick]), n_on_disk=len(fs),
        ye=ye, xe=xe, mh=mh, mw=mw, plant_sigma=a.plant_sigma,
        plant_tiles=np.array(plant), fine=np.array(B.FINE), mid=np.array(B.MID))
    print(f"{subj}: {nf} frames in {time.time()-t00:.0f}s -> {subj}__{tag}.npz")


if __name__ == "__main__":
    main()


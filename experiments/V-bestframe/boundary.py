"""Measure the path-boundary handicap on REAL PIXELS, with a null and a potency control.

resample_price.py says the modelled handicap at this instrument's FINE band is
1.013x-1.028x, not the 1.43x BUILD-SHARP quotes at f=0.35, because DoG(1.0, 2.0)
peaks at f=0.153 cyc/px. That is a model. This measures it.

METHOD. Take the arm that pays NO resample (the rawpy frame, tone-mapped into
merge space exactly as paircov.band_of does) and push it through a reconstruction
of the chain the merge pays:

  align gather : Catmull-Rom at a phase swept across the field by a scale term
                 g = 2e-3, reproducing the near-uniform phase BUILD-SHARP 20.2
                 measured (mean distance-to-integer 0.2369)
  chroma co-site : Catmull-Rom at fixed phi = 0.25 on both axes, R and B only,
                 which is what BUILD-SHARP 20.3 says the co-site is

Then read the per-tile FINE band amplitude before and after. The ratio is the
handicap, per tile, on this subject's actual spectrum. Also run it on the merge
itself, whose grid makes the frequency mapping exact but whose spectrum has
already paid the chain once -- the two bracket the answer from opposite sides.

CONTROLS. NULL: zero resample must return exactly 1.000000 on every tile.
POTENCY: an extra planted phi=0.5 resample must drop the retention to the value
resample_price.py predicts independently. An instrument that cannot see a
resample cannot be trusted to have excluded one.
"""
import argparse
import os
import numpy as np
from pathlib import Path
import bestframe as B
from resample_price import cr_weights

GAL = Path(os.environ.get("VBF_GAL", r"C:\dev\strehl-out\GALLERY-FIXED-SRGB"))
RAW = Path(r"D:\personal\macro")
OUT = Path(os.environ.get("VBF_OUT", r"C:\dev\strehl-out\V-BESTFRAME"))
VOUT = Path(r"C:\dev\strehl-out\V-BOUNDARY")
GSCALE = 2e-3          # BUILD-SHARP 20.2: per-frame scale term of the real warp


def cr_axis(a, coord, axis):
    """Catmull-Rom resample of 2-D `a` along `axis` at source coords `coord`."""
    n = a.shape[axis]
    i0 = np.floor(coord).astype(np.int64)
    W = cr_weights(coord - i0).astype(np.float32)          # (4, m)
    out = None
    for t, k in enumerate((-1, 0, 1, 2)):
        idx = np.clip(i0 + k, 0, n - 1)
        g = a[idx, :] if axis == 0 else a[:, idx]
        g = g * (W[t][:, None] if axis == 0 else W[t][None, :])
        out = g if out is None else out + g
    return out


def sweep_coords(n, g):
    """Source coords for a scale warp about the centre: sweeps phase across the field."""
    i = np.arange(n, dtype=np.float64)
    return np.clip(i + g * (i - (n - 1) / 2.0), 1.0, n - 3.0)


def shift_coords(n, phi):
    return np.clip(np.arange(n, dtype=np.float64) + phi, 1.0, n - 3.0)


def chain(rgb, do_align=True, do_cosite=True, plant=0.0):
    """Apply the modelled merge chain to a float32 HxWx3 and return luma."""
    H, W = rgb.shape[:2]
    ay = sweep_coords(H, GSCALE) if do_align else np.arange(H, dtype=np.float64)
    ax = sweep_coords(W, GSCALE) if do_align else np.arange(W, dtype=np.float64)
    out = np.zeros((H, W), np.float32)
    for c in range(3):
        p = rgb[:, :, c]
        if do_align:
            p = cr_axis(cr_axis(p, ay, 0), ax, 1)
        if do_cosite and c in (0, 2):
            p = cr_axis(cr_axis(p, shift_coords(H, 0.25), 0), shift_coords(W, 0.25), 1)
        if plant:
            p = cr_axis(cr_axis(p, shift_coords(H, plant), 0), shift_coords(W, plant), 1)
        out += B.LUMA[c] * p
        del p
    return out


def tile_amp(lum, ye, xe, sig):
    f2 = B.dog(lum, sig[0], sig[1]).astype(np.float64) ** 2
    out = np.empty((len(ye) - 1, len(xe) - 1))
    for i in range(len(ye) - 1):
        for j in range(len(xe) - 1):
            out[i, j] = np.sqrt(f2[ye[i]:ye[i + 1], xe[j]:xe[j + 1]].mean())
    return out


def frame_arm(subj, k):
    """The tone-mapped frame in merge photometric space, plus its scale s."""
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    m8, m16 = B.boxdown(mL, 8), B.boxdown(mL, 16)
    del mL
    fs = sorted((RAW / subj).glob("*.ARW"))
    path = fs[k]
    rgb = B.decode(path)
    assert rgb.dtype == np.uint16, f"decode returned {rgb.dtype}, NOT uint16"
    s, t, peak = B.register2(m16, B.boxdown(B.raw_green_half(path), 8), down=16)
    xs, ys, cov = B.fit_tone(m8, B.boxdown(B.luma(rgb), 8), s, t)
    lut = B.tone_lut(xs, ys)
    ton = np.empty(rgb.shape, np.float32)
    for c in range(3):
        ton[:, :, c] = B.apply_tone_fast(rgb[:, :, c], lut)
    del rgb
    return ton, s, peak, path.name, len(fs)


def report(name, r, detail=None):
    q = np.nanpercentile(r, [5, 25, 50, 75, 95])
    line = (f"  {name:<34} median {np.nanmedian(r):.5f}  "
            f"p05 {q[0]:.4f} p25 {q[1]:.4f} p75 {q[3]:.4f} p95 {q[4]:.4f}")
    if detail is not None and detail.any():
        line += f"  | detail-tile median {np.nanmedian(r[detail]):.5f}"
    print(line, flush=True)
    return float(np.nanmedian(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--frac", type=float, default=0.5, help="which frame, as a fraction")
    a = ap.parse_args()
    VOUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for subj in a.subjects:
        print(f"\n{'=' * 78}\n{subj}\n{'=' * 78}", flush=True)
        m = B.read_merge(GAL / f"{subj}.tiff")
        assert m.dtype == np.uint16, f"merge is {m.dtype}, NOT uint16"
        ye = B.tile_edges(m.shape[0], B.NTY); xe = B.tile_edges(m.shape[1], B.NTX)
        mf = m.astype(np.float32); del m

        # ---- detail mask, taken from the SURVEY so it is the same tile set ----
        detail = None
        try:
            from curve import arms
            ar = arms(subj)
            detail = np.isfinite(ar["snr"]) & (ar["snr"] >= 1.0)
            print(f"  detail tiles from survey: {int(detail.sum())}/{detail.size}")
        except Exception as e:
            print(f"  (no survey arms: {e})")

        # ---- MERGE-GRID arm: exact frequency mapping, once-depleted spectrum ----
        a0 = tile_amp(chain(mf, False, False), ye, xe, B.FINE)
        aN = tile_amp(chain(mf, False, False), ye, xe, B.FINE)
        nul = aN / a0
        print(f"  CONTROL NULL  merge vs itself, no resample: median {np.nanmedian(nul):.9f} "
              f"min {np.nanmin(nul):.9f} max {np.nanmax(nul):.9f} "
              f"-> {'PASS' if np.allclose(nul, 1.0, atol=0, rtol=0) else 'FAIL'}")

        aA = tile_amp(chain(mf, True, False), ye, xe, B.FINE)
        aC = tile_amp(chain(mf, True, True), ye, xe, B.FINE)
        aP = tile_amp(chain(mf, True, True, plant=0.5), ye, xe, B.FINE)
        del mf
        rA = report("merge grid: align only", aA / a0, detail)
        rC = report("merge grid: align + co-site", aC / a0, detail)
        rP = report("merge grid: + PLANTED phi=0.5", aP / a0, detail)

        # ---- FRAME arm: unresampled spectrum, ~1/s frequency error ----
        fs = sorted((RAW / subj).glob("*.ARW"))
        k = int(round(a.frac * (len(fs) - 1)))
        ton, s, peak, fname, nfr = frame_arm(subj, k)
        fye = B.tile_edges(ton.shape[0], B.NTY); fxe = B.tile_edges(ton.shape[1], B.NTX)
        sig = (B.FINE[0] * s, B.FINE[1] * s)
        print(f"  frame k={k} {fname} of {nfr}  s={s:.4f} peak={peak:.3f}  "
              f"band radii scaled to {sig[0]:.3f}/{sig[1]:.3f}")
        f0 = tile_amp(chain(ton, False, False), fye, fxe, sig)
        fA = tile_amp(chain(ton, True, False), fye, fxe, sig)
        fC = tile_amp(chain(ton, True, True), fye, fxe, sig)
        fP = tile_amp(chain(ton, True, True, plant=0.5), fye, fxe, sig)
        del ton
        gA = report("frame grid: align only", fA / f0)
        gC = report("frame grid: align + co-site", fC / f0)
        gP = report("frame grid: + PLANTED phi=0.5", fP / f0)
        res[subj] = (rA, rC, rP, gA, gC, gP)
    print("\n" + "=" * 78)
    print("SUMMARY -- amplitude retention of the FINE band through the modelled chain")
    print("=" * 78)
    print(f"  {'subject':<28} {'MERGE GRID':>28} | {'FRAME GRID':>28}")
    print(f"  {'':<28} {'align':>8} {'+cosite':>9} {'+plant':>9} | "
          f"{'align':>8} {'+cosite':>9} {'+plant':>9}   handicap")
    for s_, (rA, rC, rP, gA, gC, gP) in res.items():
        print(f"  {s_:<28} {rA:8.4f} {rC:9.4f} {rP:9.4f} | "
              f"{gA:8.4f} {gC:9.4f} {gP:9.4f}   {1.0/gC:8.4f}x")


if __name__ == "__main__":
    main()
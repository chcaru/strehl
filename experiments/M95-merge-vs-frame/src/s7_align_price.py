"""S7 -- the price of the aligned path, which is the DEFAULT and is what the
owner's stacks were made with.

Three renders of the same 299 frames at gate 0:

  M   STREHL_ALIGN=0     no registration, NO RESAMPLER at all, native grid
  Z   STREHL_ALIGN=zoom  registration DISCARDED, but the same global zoom and
                         the same Catmull-Rom resample are still paid
  C   default            full registration, same zoom, same resampler

so  Z / M  isolates the resampler, and  C / Z  isolates what registration adds
on top of it. C / M is the whole price of the aligned path.

C and Z live on a grid magnified by k = 1/0.9315: the merge scales the field of
view to 0.9315 so every frame covers every output pixel, then upsamples back to
the original dimensions. A scene frequency f (cycles per M-pixel) therefore
appears at f/k cycles per C-pixel. The comparison is made at matched SCENE
frequency, and each curve is normalised by its own mean over the reference band
[0.02, 0.06] where an interpolator's response is flat -- so no absolute power
calibration between grids is needed.

The measured resampler response is checked against the analytic Catmull-Rom
MTF, derived here from the kernel rather than taken on report.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402
from s6_spectral import F_HI, F_LO, plant_blur, psd, sigma_eq  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
WIN = 512
FOV = 0.9315  # printed by the merge: "field of view scaled to 0.9315"
REF_LO, REF_HI = 0.02, 0.06
PLANE_W, PLANE_H = 3516, 2344


def catmull_rom(t: np.ndarray) -> np.ndarray:
    """Catmull-Rom (a = -0.5) cubic kernel."""
    x = np.abs(t)
    w = np.zeros_like(x)
    m1 = x < 1
    m2 = (x >= 1) & (x < 2)
    w[m1] = 1.5 * x[m1] ** 3 - 2.5 * x[m1] ** 2 + 1.0
    w[m2] = -0.5 * x[m2] ** 3 + 2.5 * x[m2] ** 2 - 4.0 * x[m2] + 2.0
    return w


def catmull_rom_mtf(f: np.ndarray, phase: float | None = None) -> np.ndarray:
    """|MTF| of Catmull-Rom interpolation at source frequency f (cy/source px).

    For a shift-varying resample the response depends on the sub-pixel phase, so
    unless a phase is given this returns the RMS over phase -- which is what an
    upsample by a non-integer factor delivers, since every output pixel lands at
    a different phase.
    """
    taps = np.arange(-2, 3)
    if phase is not None:
        w = catmull_rom(phase - taps)
        w = w / w.sum()
        return np.abs(np.sum(w[None, :] * np.exp(-2j * np.pi * f[:, None] * taps[None, :]), axis=1))
    ph = np.linspace(0, 1, 129)[:-1]
    acc = np.zeros((f.size, ph.size))
    for j, p in enumerate(ph):
        w = catmull_rom(p - taps)
        w = w / w.sum()
        acc[:, j] = np.abs(
            np.sum(w[None, :] * np.exp(-2j * np.pi * f[:, None] * taps[None, :]), axis=1)
        )
    return np.sqrt((acc**2).mean(axis=1))


def scene_window(img, cx, cy, n, scale):
    """Window of `n*scale` px on `img`, centred on the scene point that sits at
    (cx, cy) on the unzoomed plane."""
    c0x, c0y = (PLANE_W - 1) / 2.0, (PLANE_H - 1) / 2.0
    zx = (cx - c0x) / scale + c0x
    zy = (cy - c0y) / scale + c0y
    m = int(round(n / scale))
    m -= m % 2
    x0 = int(round(zx - m / 2))
    y0 = int(round(zy - m / 2))
    x0 = max(0, min(PLANE_W - m, x0))
    y0 = max(0, min(PLANE_H - m, y0))
    return img[y0 : y0 + m, x0 : x0 + m], (x0, y0, m)


def norm_curve(f, p):
    ref = np.nanmean(p[(f >= REF_LO) & (f < REF_HI)])
    return p / ref


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    names = [n for n in rois if n != "ROI-FLAT"]
    k = 1.0 / FOV
    print(f"field of view scale {FOV}  =>  output magnification k = {k:.5f}")

    imgs = {
        "M": L.read_tif_green(os.path.join(L.OUT, "armM-gate0-binlin.tif")),
        "Z": L.read_tif_green(os.path.join(L.OUT, "armZ-zoomnull-gate0.tif")),
        "C": L.read_tif_green(os.path.join(L.OUT, "armC-aligned-gate0.tif")),
    }
    for nm, im in imgs.items():
        print(f"  arm {nm}: {im.shape[1]} x {im.shape[0]}")

    # ---- registration control: does the assumed zoom centre actually land? ----
    # Cross-correlate a scene window from Z against the same window from M,
    # after resampling M by k. If the geometric model is wrong the peak will not
    # be at zero and everything downstream is meaningless.
    from scipy.ndimage import zoom as ndzoom

    print()
    print("=" * 78)
    print("GEOMETRY CONTROL -- does the assumed zoom map put Z on top of M?")
    print("=" * 78)
    geom = {}
    for nm in names:
        cx = rois[nm]["x"] + WIN / 2
        cy = rois[nm]["y"] + WIN / 2
        mt, mw = scene_window(imgs["M"], cx, cy, WIN, 1.0)
        for arm in ("Z", "C"):
            zt, zw = scene_window(imgs[arm], cx, cy, WIN, k)
            up = ndzoom(mt.astype(np.float64), zt.shape[0] / mt.shape[0], order=3)
            a = up - up.mean()
            b = zt.astype(np.float64) - zt.mean()
            F = np.fft.rfft2(a) * np.conj(np.fft.rfft2(b))
            cc = np.fft.irfft2(F, s=a.shape)
            pk = np.unravel_index(np.argmax(cc), cc.shape)
            dy = pk[0] if pk[0] < a.shape[0] / 2 else pk[0] - a.shape[0]
            dx = pk[1] if pk[1] < a.shape[1] / 2 else pk[1] - a.shape[1]
            r = float(cc[pk] / (np.sqrt((a**2).sum()) * np.sqrt((b**2).sum())))
            print(f"  {nm:<14} {arm} vs M: peak offset ({dx:+4d},{dy:+4d}) px, corr {r:+.4f}")
            geom[f"{nm}/{arm}"] = dict(dx=int(dx), dy=int(dy), corr=r, win_m=mw, win_z=zw)

    # ---- the ratio curves ----
    print()
    print("=" * 78)
    print("ALIGNMENT PRICE -- at matched scene frequency, normalised on [0.02,0.06]")
    print("=" * 78)
    res = {}
    fgrid = None
    for nm in names:
        cx = rois[nm]["x"] + WIN / 2
        cy = rois[nm]["y"] + WIN / 2
        mt, _ = scene_window(imgs["M"], cx, cy, WIN, 1.0)
        fm, pm = psd(mt)
        pm_n = norm_curve(fm, pm)
        fgrid = fm
        row = {}
        for arm in ("Z", "C"):
            zt, _ = scene_window(imgs[arm], cx, cy, WIN, k)
            fz, pz = psd(zt)
            fz_scene = fz * k  # cycles per M-pixel
            pz_n = norm_curve(fz, pz)
            pz_on_m = np.interp(fm, fz_scene, pz_n, left=np.nan, right=np.nan)
            s, nb = sigma_eq(fm, pz_on_m, pm_n)
            row[arm] = dict(sigma_eq_vs_M=s, nbins=nb, curve=[float(v) for v in pz_on_m])
            print(f"  {nm:<14} {arm} vs M : sigma_eq {s:+7.4f} px  ({nb} bins)")
        # C vs Z: same grid, same zoom, same resampler. Registration only.
        zt, _ = scene_window(imgs["Z"], cx, cy, WIN, k)
        ct, _ = scene_window(imgs["C"], cx, cy, WIN, k)
        fz, pz = psd(zt)
        fc, pc = psd(ct)
        s_cz, nb = sigma_eq(fz * k, norm_curve(fz, pc), norm_curve(fz, pz))
        row["C_vs_Z"] = dict(sigma_eq=s_cz, nbins=nb)
        print(f"  {nm:<14} C vs Z : sigma_eq {s_cz:+7.4f} px  ({nb} bins)  [registration only]")
        row["M_curve"] = [float(v) for v in pm_n]
        res[nm] = row

    # ---- analytic Catmull-Rom, to check the measured resampler response ----
    print()
    print("=" * 78)
    print("ANALYTIC CHECK -- Catmull-Rom MTF at this upsample, derived from the kernel")
    print("=" * 78)
    f = np.linspace(1e-4, 0.5, 400)
    mtf = catmull_rom_mtf(f / k)  # source-grid frequency
    p_ratio = mtf**2
    s_pred, _ = sigma_eq(f, p_ratio, np.ones_like(f))
    print(f"  Catmull-Rom MTF (rms over phase) at f = 0.1/0.25/0.4 cy/px : "
          f"{np.interp(0.1, f, mtf):.4f} / {np.interp(0.25, f, mtf):.4f} / {np.interp(0.4, f, mtf):.4f}")
    print(f"  equivalent Gaussian of that response, same fit, same band    : "
          f"sigma_eq = {s_pred:+.4f} px")
    print(f"  MEASURED  Z vs M, median over the three detail ROIs          : "
          f"sigma_eq = {np.median([res[n]['Z']['sigma_eq_vs_M'] for n in names]):+.4f} px")
    # Sanity: the kernel must be interpolating (unit at 0, zero at other taps).
    taps = np.arange(-2, 3)
    w0 = catmull_rom(0.0 - taps)
    assert abs(w0.sum() - 1.0) < 1e-12 and abs(w0[2] - 1.0) < 1e-12, w0

    out = dict(
        fov=FOV, k=k, geometry=geom, price=res,
        catmull_rom=dict(
            f=[float(v) for v in f], mtf=[float(v) for v in mtf], sigma_eq_pred=s_pred
        ),
        f_grid=[float(v) for v in fgrid],
    )
    dst = os.path.join(OUTDIR, "s7_alignment_price.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

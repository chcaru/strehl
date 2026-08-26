"""BUILD-RESAMP -- commission `slanted_edge.py` before any number it prints
counts for anything.

Arms, all at FIXED sites with the edge line PINNED from the reference arm, so
every arm is scored on the same edges with the same geometry and nothing is
decided by site selection or by re-fitting:

  NULL       the same render twice. Every ROI must return the identical MTF50,
             ratio exactly 1.000000. A non-zero answer means the chain is not a
             function of its input and nothing downstream is a measurement.

  POTENCY    a known Gaussian blur. The prediction is not a hand-wave: a
             Gaussian's MTF is exp(-2 pi^2 sigma^2 f^2) in closed form, so the
             measured MTF_blur(f)/MTF_sharp(f) must equal that curve at EVERY
             frequency, not merely fall somewhere.

  NOISE      the arm that exists because the previous instrument failed exactly
             here. Add white Gaussian noise heavy enough to move band power
             substantially -- the statistic that produced the 17-27% deficit --
             and require MTF50 not to move. Both are printed side by side so
             the immunity is demonstrated against the failure, not asserted.

  NEAREST    the fixed point of the whole exercise. band_ratio.py ranks
             `--resampler nearest` FIRST, by +29% / +42%. If a slanted edge
             also ranks it first, this instrument is no better than the last
             one and must be thrown away too.

  RESAMPLE   an absurd-value control in the sense AGENTS demands: rescale the
             image by 1.20x with a good kernel. MTF50 in cycles per pixel must
             then fall by 1/1.20, because the same scene detail now occupies
             20% more pixels. If it does not, the instrument is not reading a
             spatial frequency at all. This is also the calibration for the
             cross-tool comparison, where the two rasters differ in scale.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slanted_edge as se  # noqa: E402

FGRID = np.round(np.arange(0.01, 0.201, 0.005), 4)


def green(path):
    a = tifffile.imread(path)
    if a.ndim == 3:
        a = a[:, :, 1]
    return a.astype(np.float64)


def blur(img, sigma):
    fy = np.fft.fftfreq(img.shape[0])[:, None]
    fx = np.fft.rfftfreq(img.shape[1])[None, :]
    h = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return np.fft.irfft2(np.fft.rfft2(img) * h, s=img.shape)


def rescale(img, k):
    """Exact band-limited resample by k, so the control introduces scale and
    as little else as possible."""
    h, w = img.shape
    nh, nw = int(round(h * k)), int(round(w * k))
    F = np.fft.rfft2(img)
    out = np.zeros((nh, nw // 2 + 1), complex)
    ky = min(h, nh) // 2
    kx = min(w // 2 + 1, nw // 2 + 1)
    out[:ky, :kx] = F[:ky, :kx]
    out[-ky:, :kx] = F[-ky:, :kx]
    return np.fft.irfft2(out, s=(nh, nw)) * (nh * nw) / (h * w)


def band_power(img, sites, lo=0.20, hi=0.40, tile=96):
    """The statistic that failed, so the noise arm can show it moving."""
    fy = np.fft.fftfreq(tile)[:, None]
    fx = np.fft.rfftfreq(tile)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    mask = (r >= lo) & (r < hi)
    win = np.hanning(tile)[:, None] * np.hanning(tile)[None, :]
    out = []
    for s in sites:
        y = min(max(s["y"] + s["h"] // 2 - tile // 2, 0), img.shape[0] - tile)
        x = min(max(s["x"] + s["w"] // 2 - tile // 2, 0), img.shape[1] - tile)
        t = img[y:y + tile, x:x + tile]
        t = (t - t.mean()) * win
        out.append((np.abs(np.fft.rfft2(t)) ** 2)[mask].mean())
    return float(np.median(out))


def measure_at(img, sites, pin=True):
    """MTF50 + full curve at fixed sites, edge line pinned from the sites."""
    v, curves = [], []
    for s in sites:
        r = se.measure_roi(se.cut(img, s), line=s["line"] if pin else None)
        v.append(r["mtf50"] if r else np.nan)
        curves.append((r["f"], r["m"]) if r else None)
    return np.array(v), curves


def curve_ratio(ca, cb, fgrid=FGRID):
    acc = []
    for a, b in zip(ca, cb):
        if a is None or b is None:
            continue
        ma = np.interp(fgrid, a[0], a[1])
        mb = np.interp(fgrid, b[0], b[1])
        r = np.full(len(fgrid), np.nan)
        ok = mb > 0.08
        r[ok] = ma[ok] / mb[ok]
        acc.append(r)
    return np.nanmedian(np.array(acc), axis=0)


def show(f0s, rc, pred=None):
    for f0 in f0s:
        i = int(np.argmin(np.abs(FGRID - f0)))
        if pred is None:
            print(f"              f={FGRID[i]:.3f}  ratio {rc[i]:.4f}")
        else:
            print(f"              f={FGRID[i]:.3f}  measured {rc[i]:.4f}   "
                  f"predicted {pred[i]:.4f}   err {rc[i]-pred[i]:+.4f}")


def main():
    path = sys.argv[1]
    nearest_path = sys.argv[2] if len(sys.argv) > 2 else None
    g = green(path)
    print("commissioning slanted_edge.py")
    print(f"  base   : {path}")
    print(f"  raster : {g.shape[1]} x {g.shape[0]}, green channel")
    print(f"  geometry: ROI {se.LENGTH} along x {se.WIDTH} across, ESF support "
          f"+/-{se.HALF} px, {se.OVERSAMPLE}x bins, slant "
          f"{se.MIN_ANGLE_DEG}-{se.MAX_ANGLE_DEG} deg\n")

    sites = se.find_edges(g, stride=96, border=128)
    print(f"  usable slanted-edge sites: {len(sites)}   "
          f"(scan census {se.STATS})")
    if len(sites) < 20:
        print("  TOO FEW EDGES -- this subject cannot commission the instrument")
        return 2
    ang = np.array([s["angle"] for s in sites])
    print(f"  slant   : median {np.median(ang):.2f} deg, "
          f"5-95% {np.percentile(ang, 5):.2f}-{np.percentile(ang, 95):.2f}")
    print(f"  orient  : {sum(1 for s in sites if not s['t'])} vertical, "
          f"{sum(1 for s in sites if s['t'])} horizontal")

    base, cbase = measure_at(g, sites)
    ok = np.isfinite(base)
    print(f"  MTF50 on {ok.sum()} sites: median {np.median(base[ok]):.5f} cyc/px, "
          f"IQR {np.percentile(base[ok], 25):.5f}-"
          f"{np.percentile(base[ok], 75):.5f}\n")

    # ---- NULL ------------------------------------------------------------
    v2, _ = measure_at(g, sites)
    d = np.abs(v2[ok] - base[ok])
    print(f"  NULL      same render twice, max |dMTF50| = {d.max():.3e}   "
          f"ratio {np.median(v2[ok]/base[ok]):.6f}   "
          f"{'PASS' if d.max() == 0.0 else 'FAIL'}\n")

    # ---- POTENCY ---------------------------------------------------------
    for sigma in (0.5, 1.0):
        vb, cb = measure_at(blur(g, sigma), sites)
        okb = ok & np.isfinite(vb)
        rc = curve_ratio(cb, cbase)
        pred = np.exp(-2.0 * np.pi**2 * sigma**2 * FGRID**2)
        band = (FGRID >= 0.02) & (FGRID <= 0.15)
        err = np.nanmax(np.abs(rc[band] - pred[band]))
        print(f"  POTENCY   Gaussian sigma={sigma} px on {okb.sum()} sites")
        print(f"            MTF50 {np.median(base[okb]):.5f} -> "
              f"{np.median(vb[okb]):.5f} cyc/px "
              f"({np.median(vb[okb]/base[okb]):.4f}x)")
        print("            MTF ratio vs the Gaussian's own closed form "
              "exp(-2 pi^2 s^2 f^2):")
        show((0.02, 0.04, 0.06, 0.08, 0.10, 0.15), rc, pred)
        print(f"            worst |err| over 0.02-0.15 = {err:.4f}   "
              f"{'PASS' if err < 0.06 else 'FAIL'}\n")

    # ---- RESAMPLE (absurd-value scale control) ---------------------------
    k = 1.20
    gk = rescale(g, k)
    sk = [dict(s, y=int(round(s["y"] * k)), x=int(round(s["x"] * k)))
          for s in sites]
    sk = [s for s in sk
          if s["y"] + s["h"] < gk.shape[0] - 4 and s["x"] + s["w"] < gk.shape[1] - 4]
    vk, _ = measure_at(gk, sk, pin=False)
    okk = np.isfinite(vk)
    bb = np.array([base[i] for i, s in enumerate(sites)
                   if int(round(s["y"] * k)) + s["h"] < gk.shape[0] - 4
                   and int(round(s["x"] * k)) + s["w"] < gk.shape[1] - 4])
    okk &= np.isfinite(bb)
    rat = float(np.median(vk[okk] / bb[okk]))
    print(f"  RESAMPLE  band-limited {k}x enlargement, {okk.sum()} sites")
    print(f"            MTF50 {np.median(bb[okk]):.5f} -> "
          f"{np.median(vk[okk]):.5f} cyc/px   ratio {rat:.4f}, "
          f"expected {1/k:.4f}")
    print(f"            {'PASS' if abs(rat - 1/k) < 0.04 else 'FAIL'}   "
          f"(a cycles-per-pixel read-out MUST track the raster)\n")

    # ---- NOISE IMMUNITY --------------------------------------------------
    print("  NOISE     white Gaussian noise: MTF50 vs the band-power statistic "
          "that failed")
    print(f"    {'sigma DN':<10}{'band 0.20-0.40':>16}{'x base':>9}"
          f"{'MTF50':>10}{'x base':>9}")
    bp0 = band_power(g, sites)
    print(f"    {'0 (base)':<10}{bp0:>16.4g}{1.0:>9.3f}"
          f"{np.median(base[ok]):>10.5f}{1.0:>9.4f}")
    rng = np.random.default_rng(20260826)
    worst, lastbp = 0.0, 1.0
    for s in (100.0, 300.0, 1000.0):
        gn = g + rng.normal(0.0, s, g.shape)
        bp = band_power(gn, sites)
        vn, _ = measure_at(gn, sites)
        okn = ok & np.isfinite(vn)
        rat = float(np.median(vn[okn] / base[okn]))
        worst = max(worst, abs(rat - 1.0))
        lastbp = bp / bp0
        print(f"    {s:<10.0f}{bp:>16.4g}{bp/bp0:>9.3f}"
              f"{np.median(vn[okn]):>10.5f}{rat:>9.4f}")
    print(f"    worst |MTF50 ratio - 1| = {worst:.4f}   "
          f"{'PASS' if worst < 0.03 else 'FAIL'}")
    print(f"    bar: over the same range band power moved {lastbp:.2f}x\n")

    # ---- NEAREST ---------------------------------------------------------
    if nearest_path:
        gn = green(nearest_path)
        vn, cn = measure_at(gn, sites)
        okn = ok & np.isfinite(vn)
        rat = float(np.median(vn[okn] / base[okn]))
        bpn = band_power(gn, sites)
        print(f"  NEAREST   {nearest_path}")
        print(f"            band power 0.20-0.40 : {bpn/bp0:.4f}x   "
              f"(band_ratio.py ranked nearest FIRST)")
        print(f"            MTF50                : {rat:.4f}x   "
              f"({np.median(vn[okn]):.5f} vs {np.median(base[okn]):.5f} cyc/px)")
        show((0.02, 0.05, 0.10, 0.15), curve_ratio(cn, cbase))
        print("            " + ("PASS -- MTF50 does not reward nearest"
                                if rat < 1.0 else
                                "FAIL -- MTF50 rewards nearest too; discard "
                                "this instrument"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

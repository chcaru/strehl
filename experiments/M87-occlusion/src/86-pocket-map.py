"""M87 s31b -- render the pocket as a map, and de-confound the veil profile.

Two defects in 84-banding.py that I am repairing here rather than reporting.

  1. VEIL PROFILE CONFOUND.  84 measured "median DN at distance d from the
     silhouette".  Distance from the subject is not independent of WHERE in
     the frame a pixel is: the subject fills the upper left, so large-d
     pixels are all lower-right.  The scene's own background gradient is
     therefore aliased into the falloff curve, and the d>=90 "asymptote"
     (50392 DN) is a different part of the sky from the d=34 peak.  Repaired
     by fitting a smooth background model to far-field pixels only and
     profiling the RESIDUAL, which cancels any gradient the model can hold.

  2. I HAVE BEEN EYEBALLING "SPECKLE".  Discipline 677 says render the
     spatial statistic as a map before interpreting a scalar summary of it.
     84 gave me scalars that disagreed with what I thought I saw.  So this
     script renders four registered views of the same pixels at 2x nearest
     neighbour, and the map decides.

The direct measurement that settles the banding question is the ratio

     noise_sd(DN) / dn_per_code

Posterisation needs the quantiser step to be COARSE relative to the noise.
If one output code is many noise sigma, a smooth field lands in plateaus and
bands.  If one code is a fraction of a sigma, the noise self-dithers and no
band can form.  This is not an opinion about the figure, it is a property of
the data, and it predicts the B1 dither ratio 84 already measured.

  BAR B4, three branches, registered before running:
     code/noise >= 3.0  -> BANDING EXPECTED (self-dither impossible)
     code/noise <= 1.0  -> BANDING IMPOSSIBLE (noise self-dithers)
     otherwise          -> MARGINAL
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

SRC = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl.tif")
OUTDIR = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

X0, Y0, W, H = 700, 3150, 1100, 900
POCKET = (690, 790, 720, 890)
FAR = (200, 400, 830, 1070)
ZOOM = (550, 900, 600, 1100)      # y0,y1,x0,x1 -- claw + its pocket, for the map
FARFIELD_D = 80                   # px; pixels beyond this define the background
B4_EXPECT, B4_IMPOSSIBLE = 3.0, 1.0


def noise_sd(x):
    """Per-pixel high-frequency sd in DN, robust to gradient and to outliers."""
    hp = x - ndimage.median_filter(x, size=5)
    return float(1.4826 * np.median(np.abs(hp - np.median(hp))))


def quad_fit(g, mask):
    """Least-squares 2-D quadratic over masked pixels; returns the full field."""
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]].astype(np.float64)
    yn, xn = yy / g.shape[0], xx / g.shape[1]
    basis = [np.ones_like(xn), xn, yn, xn * xn, xn * yn, yn * yn]
    A = np.stack([b[mask] for b in basis], axis=1)
    coef, *_ = np.linalg.lstsq(A, g[mask].astype(np.float64), rcond=None)
    return sum(c * b for c, b in zip(coef, basis)), coef


def main():
    a = tifffile.imread(SRC)
    g = a[Y0:Y0 + H, X0:X0 + W, 1].astype(np.float32)
    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    dn_per_code = span / 127.0
    out = {"dn_per_code": dn_per_code}

    # ---- B4: can a band form at all? -----------------------------------
    print("=== B4  is the quantiser coarse relative to the noise? ===")
    print(f"  one output code = {dn_per_code:.1f} DN")
    for nm, (y0, y1, x0, x1) in (("POCKET", POCKET), ("FAR", FAR)):
        sd = noise_sd(g[y0:y1, x0:x1])
        ratio = dn_per_code / max(sd, 1e-9)
        br = ("BANDING EXPECTED" if ratio >= B4_EXPECT else
              "BANDING IMPOSSIBLE" if ratio <= B4_IMPOSSIBLE else "MARGINAL")
        print(f"  {nm:7s} noise sd {sd:7.1f} DN   code/noise {ratio:6.2f}x"
              f"   -> {br}")
        out[f"B4_{nm}"] = {"noise_sd": sd, "code_over_noise": ratio, "branch": br}

    # ---- veil, de-confounded -------------------------------------------
    dark_thr = med - span
    subj = ndimage.binary_opening(
        ndimage.binary_closing(g < dark_thr, np.ones((5, 5))), np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)
    far = dist >= FARFIELD_D
    print(f"\n=== veil, de-confounded against a background model ===")
    print(f"  subject {100*subj.mean():.1f}% of crop;"
          f"  far field (d>={FARFIELD_D}) {100*far.mean():.1f}%"
          f"  ({int(far.sum())} px)")
    model, coef = quad_fit(g, far)
    resid = g - model
    print(f"  quadratic background model, residual sd on the far field"
          f" {float(resid[far].std()):.1f} DN")

    print(f"  {'d':>4} {'raw median':>11} {'residual':>10} {'n':>8}")
    prof = []
    for d in range(1, 121):
        m = (dist >= d) & (dist < d + 1) & ~subj
        if m.sum() >= 200:
            prof.append((d, float(np.median(g[m])), float(np.median(resid[m])),
                         int(m.sum())))
    for d, rawv, rv, n in prof:
        if d in (1, 3, 5, 10, 15, 20, 30, 40, 60, 80, 100, 120):
            print(f"  {d:4d} {rawv:11.0f} {rv:+10.1f} {n:8d}")
    tail = [p[2] for p in prof if p[0] >= FARFIELD_D]
    base = float(np.median(tail)) if tail else 0.0
    inner = [(d, rv) for d, _, rv, _ in prof if 2 <= d <= 60]
    pk_d, pk_v = max(inner, key=lambda t: t[1])
    amp = pk_v - base
    print(f"  far-field residual baseline {base:+.1f} DN")
    print(f"  peak residual {pk_v:+.1f} DN at d={pk_d} px"
          f"  ->  veil amplitude {amp:+.0f} DN = {amp/dn_per_code:+.1f} codes"
          f" = {100*amp/65535:.2f}% of full scale")
    out["profile"] = prof
    out["resid_baseline"] = base
    out["peak_d"] = pk_d
    out["veil_amplitude_dn"] = amp
    out["veil_amplitude_codes"] = amp / dn_per_code
    out["quad_coef"] = [float(c) for c in coef]

    # ---- the map (discipline 677) ---------------------------------------
    zy0, zy1, zx0, zx1 = ZOOM
    z = g[zy0:zy1, zx0:zx1]
    v = (z - med) / span * 127.0 + 127.0
    u8 = np.clip(v, 0, 255).astype(np.uint8)
    parity = ((u8.astype(np.int32) % 2) * 255).astype(np.uint8)
    zsd = noise_sd(z)
    zmed = float(np.median(z))
    localv = np.clip((z - zmed) / (8.0 * zsd) * 127.0 + 127.0, 0, 255).astype(np.uint8)
    hp = z - ndimage.median_filter(z, size=5)
    hpv = np.clip(hp / (4.0 * zsd) * 127.0 + 127.0, 0, 255).astype(np.uint8)

    lab = [("A as ORCH renders it", u8), ("B uint8 code parity", parity),
           (f"C local stretch, span 8 sd = {8*zsd:.0f} DN", localv),
           (f"D high pass, span 4 sd = {4*zsd:.0f} DN", hpv)]
    ph, pw = z.shape
    canvas = np.zeros((2 * ph + 6, 2 * pw + 6), np.uint8)
    for i, (_, img) in enumerate(lab):
        r, c = divmod(i, 2)
        canvas[r * (ph + 6):r * (ph + 6) + ph, c * (pw + 6):c * (pw + 6) + pw] = img
    im = Image.fromarray(canvas).resize(
        (canvas.shape[1] * 2, canvas.shape[0] * 2), Image.NEAREST)
    dst = OUTDIR / "POCKET-MAP.png"
    im.save(dst)
    print(f"\n=== map, 2x nearest neighbour, zoom y {zy0}:{zy1} x {zx0}:{zx1} ===")
    for t, _ in lab:
        print(f"  {t}")
    print(f"  wrote {dst}")
    print(f"  distinct uint8 codes in zoom: {int(np.unique(u8).size)};"
          f"  distinct DN: {int(np.unique(z.astype(np.int32)).size)}")
    out["zoom"] = list(ZOOM)
    out["zoom_codes"] = int(np.unique(u8).size)
    out["zoom_dn"] = int(np.unique(z.astype(np.int32)).size)
    out["zoom_noise_sd"] = zsd

    DATA.mkdir(exist_ok=True)
    (DATA / "86-pocket-map.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"wrote {DATA / '86-pocket-map.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

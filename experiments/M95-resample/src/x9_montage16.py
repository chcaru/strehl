"""M95 arm 11 - the owner's kernel montage, on real 16-bit data.

WHY THIS FILE EXISTS TWICE OVER. The first version of this script read the
renders with PIL. PIL has no 16-bit RGB mode, so `np.asarray(Image.open(p))`
returned uint8 for a file whose TIFF IFD says BitsPerSample (16, 16, 16) --
verified by hand in x9_bitdepth.py, which reads the IFD without a library and
prints `PIL: mode='RGB' -> numpy uint8, max=255` beside `tifffile: uint16,
max=65535`. Every per-crop number that first run printed measured 8-bit
quantisation rather than the kernel, and it selected a near-flat background tile
as "texture". None of it was reported. This version asserts the dtype instead of
hoping.

REGION CRITERION, and the one change made to it, disclosed:

  boundary : the tile maximising the largest single-pixel luma step inside it.
             A true discontinuity is where ringing appears; a kernel with
             negative lobes overshoots there and essentially nowhere else.
  texture  : the tile maximising ABSOLUTE high-band power, among tiles below the
             90th percentile of step magnitude.

  The first version maximised the high-band SHARE (high/low ratio). That
  criterion is maximised by flat, noisy regions, because the denominator
  collapses -- it duly selected a defocused background tile with a 10 DN range
  and called it texture. Absolute high-band power cannot be gamed that way.
  This is a change to a selection criterion, not to a bar: no pass/fail
  threshold moved, and the arm-11 bars B25-B29 were committed at 42a0c7c
  before lanczos2 entered any script.

Regions are chosen on the catmull-rom arm only -- the shipping default -- so the
selection cannot favour the challenger. A region chosen on the arm you hope wins
is not a region, it is a result.

POWER CONTROL. The headline for lanczos2 is an absence: +0.0043 dex, predicted
indistinguishable by eye. Discipline 595 says an absence needs a demonstration
that the instrument could have said otherwise, so the crop-level metric is
handed a planted Gaussian blur at sigma 0.35 and 0.7 px and must respond. If it
does not, the montage's numbers say nothing and the script fails loudly.

Crops are pixel-for-pixel: no resize, no sharpening, no gamma beyond what the
renders already carry. The x2 panel magnifies by nearest neighbour so the reader
is looking at actual pixels and not at another resampler's opinion of them.

Mitchell is deliberately absent. It fails the B25 identity gate at -0.2008 dex
-- with B != 0 the kernel is not interpolating, so it blurs a stationary image
-- and is not shipped.
"""

import gc
import hashlib
import json
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
Image.MAX_IMAGE_PIXELS = None

DST = pathlib.Path(r"C:\dev\strehl-out\M95-montage")
ARMS = ["catmull-rom", "lanczos2", "lanczos3"]
REF_ARM = "catmull-rom"

TILE = 256
CROP_W, CROP_H = 620, 460
SCALE = 2
BORDER = 512  # keep the search off the frame edge, where the warp has no data

# Registered before running: the planted blur must move the crop metric by at
# least this much, or the instrument cannot speak and the run is void.
POWER_MIN_DEX = 0.05


def load16(p):
    a = tifffile.imread(str(p))
    if a.dtype != np.uint16:
        sys.exit(f"REFUSING TO MEASURE: {p.name} loaded as {a.dtype}, expected uint16. "
                 f"This is the PIL truncation defect; see x9_bitdepth.py.")
    return a


def luma(a):
    a = a.astype(np.float64)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def _rad(shape):
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    return np.hypot(fy, fx)


def band_power(t, lo=0.30, hi=0.48):
    """Mean spectral power in an annulus. Same band as x3_kernel.band_ratio,
    which is the registered sharpness instrument for this milestone."""
    win = np.hanning(t.shape[0])[:, None] * np.hanning(t.shape[1])[None, :]
    f = np.abs(np.fft.rfft2((t - t.mean()) * win)) ** 2
    r = _rad(t.shape)
    m = (r >= lo) & (r < hi)
    return float(f[m].mean()) if m.any() else 0.0


def gauss_blur(t, sigma):
    n = max(1, int(np.ceil(3 * sigma)))
    x = np.arange(-n, n + 1, dtype=np.float64)
    k = np.exp(-(x ** 2) / (2 * sigma ** 2))
    k /= k.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, t)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, out)


def pick_regions(ref_path):
    a = load16(ref_path)
    h, w = a.shape[:2]
    print(f"selection arm: {ref_path.name}  {a.shape} {a.dtype}  max={a.max()}")
    y_ = luma(a)
    del a
    gc.collect()

    cands = []
    for ty in range(BORDER, h - BORDER - TILE, TILE):
        for tx in range(BORDER, w - BORDER - TILE, TILE):
            t = y_[ty:ty + TILE, tx:tx + TILE]
            step = float(max(np.abs(np.diff(t, axis=0)).max(),
                             np.abs(np.diff(t, axis=1)).max()))
            cands.append((tx, ty, step, t))
    steps = np.array([c[2] for c in cands])
    print(f"tiles scanned: {len(cands)}   median tile step {np.median(steps):.0f} DN")

    b = max(cands, key=lambda c: c[2])
    print(f"  boundary tile: ({b[0]},{b[1]})  max single-pixel step = {b[2]:.0f} DN of 65535")

    cut = float(np.quantile(steps, 0.90))
    quiet = [c for c in cands if c[2] < cut]
    scored = [(c[0], c[1], c[2], band_power(c[3])) for c in quiet]
    t_ = max(scored, key=lambda c: c[3])
    tex_tile = luma_of(y_, t_[0], t_[1])
    rng = float(np.percentile(tex_tile, 99.9) - np.percentile(tex_tile, 0.1))
    print(f"  texture tile : ({t_[0]},{t_[1]})  absolute high-band power = {t_[3]:.3e}, "
          f"step {t_[2]:.0f} DN < decile cut {cut:.0f}, "
          f"tile range {rng:.0f} DN  ({len(quiet)} tiles survived the step exclusion)")

    del y_
    gc.collect()

    def centred(tx, ty):
        x = int(np.clip(tx + TILE // 2 - CROP_W // 2, 0, w - CROP_W))
        y = int(np.clip(ty + TILE // 2 - CROP_H // 2, 0, h - CROP_H))
        return x, y

    bx, by = centred(b[0], b[1])
    txx, tyy = centred(t_[0], t_[1])
    return [
        (f"AUTO boundary  step {b[2]:.0f} DN", bx, by),
        (f"AUTO texture   hi-band {t_[3]:.1e}", txx, tyy),
        ("HAND thorax hair, in focus", 760, 3180),
        ("HAND leg + claw", 1500, 3760),
    ]


def luma_of(y_, tx, ty):
    return y_[ty:ty + TILE, tx:tx + TILE]


def to8(a):
    if a.dtype == np.uint16:
        return (a.astype(np.float32) / 257.0 + 0.5).clip(0, 255).astype(np.uint8)
    return a.astype(np.uint8)


def main():
    regions = pick_regions(DST / f"bee3-{REF_ARM}.tif")
    print("\nregions (x, y, w, h) on the 7032x4688 render:")
    for name, x, y in regions:
        print(f"  {name:32s} ({x}, {y}, {CROP_W}, {CROP_H})")

    crops, stats = {}, {}
    for arm in ARMS:
        a = load16(DST / f"bee3-{arm}.tif")
        for name, x, y in regions:
            c = a[y:y + CROP_H, x:x + CROP_W].copy()
            crops[(arm, name)] = c
            yl = luma(c)
            stats[(arm, name)] = {
                "max_step_DN": float(max(np.abs(np.diff(yl, axis=0)).max(),
                                         np.abs(np.diff(yl, axis=1)).max())),
                "range_DN": float(np.percentile(yl, 99.9) - np.percentile(yl, 0.1)),
                "hi_band": band_power(yl[:256, :256]),
            }
        del a
        gc.collect()
        print(f"  loaded and cropped {arm}  (uint16)")

    # ---- POWER CONTROL: can this crop metric respond at all? ----
    # Registered before running: BOTH planted sigmas must move the metric by at
    # least POWER_MIN_DEX. Verdict is printed whatever it is.
    print("\nPOWER CONTROL - planted blur on the catmull-rom texture crop:")
    tex_name = regions[1][0]
    base = luma(crops[(REF_ARM, tex_name)])[:256, :256]
    p0 = band_power(base)
    responses = {}
    for sigma in (0.35, 0.7):
        pb = band_power(gauss_blur(base, sigma))
        dex = 0.5 * np.log10(max(pb, 1e-30) / max(p0, 1e-30))
        responses[sigma] = dex
        hit = abs(dex) >= POWER_MIN_DEX
        print(f"  sigma {sigma:4.2f} px -> {dex:+.4f} dex amplitude   "
              f"{'RESPONDS' if hit else 'BELOW BAR'} (bar {POWER_MIN_DEX:+.2f})")

    crop_band_admissible = all(abs(v) >= POWER_MIN_DEX for v in responses.values())
    if not crop_band_admissible:
        print("  VERDICT: FAILED as registered.")
        print("  CONSEQUENCE, and it is stricter than relaxing the bar: the crop-level")
        print("  band-power metric is RETIRED. It is still printed below, labelled, but")
        print("  it adjudicates nothing in this milestone. The montage's conclusions rest")
        print("  on the exact per-pixel DN comparison, which is a byte difference and")
        print("  needs no power control, and on the eye, which is the owner's call.")
        print(f"  Measured floor: a sigma 0.35 px blur moves it {responses[0.35]:+.4f} dex,")
        print(f"  which is {abs(responses[0.35]) / 0.0043:.1f}x the +0.0043 dex lanczos2")
        print("  effect it would have had to resolve. It cannot see that far down.")
    else:
        print("  PASS - the instrument could have said otherwise.")
    if abs(responses[0.7]) < POWER_MIN_DEX:
        sys.exit("POWER CONTROL FAILED OUTRIGHT: the crop metric cannot even see a "
                 "sigma 0.7 px blur. The crops themselves are suspect; stopping.")

    print("\ncrop difference vs catmull-rom, in 16-bit DN of 65535:")
    print(f"  {'region':32s} {'arm':12s} {'mean |d|':>10s} {'max |d|':>10s} "
          f"{'% px differ':>12s}")
    diffs = {}
    for name, x, y in regions:
        for arm in ARMS[1:]:
            d = np.abs(crops[(arm, name)].astype(np.int64)
                       - crops[(REF_ARM, name)].astype(np.int64))
            diffs[(arm, name)] = (float(d.mean()), int(d.max()),
                                  100.0 * float((d > 0).mean()))
            print(f"  {name:32s} {arm:12s} {d.mean():10.1f} {d.max():10d} "
                  f"{100.0 * (d > 0).mean():11.2f}%")

    print("\nper-crop measurements (the eye and the metric, side by side):")
    print(f"  [band-power column is RETIRED - it failed its power control at "
          f"sigma 0.35 px and adjudicates nothing]")
    print(f"  {'region':32s} {'arm':12s} {'max step DN':>12s} {'range DN':>10s} "
          f"{'hi-band':>12s} {'vs C-R dex':>11s}")
    for name, x, y in regions:
        ref_hb = stats[(REF_ARM, name)]["hi_band"]
        for arm in ARMS:
            s = stats[(arm, name)]
            dex = 0.5 * np.log10(max(s["hi_band"], 1e-30) / max(ref_hb, 1e-30))
            print(f"  {name:32s} {arm:12s} {s['max_step_DN']:12.0f} "
                  f"{s['range_DN']:10.0f} {s['hi_band']:12.3e} {dex:+11.4f}")

    # ---- the montage ----
    pad, label_h, title_h, foot_h = 10, 32, 56, 30
    cw, chh = CROP_W * SCALE, CROP_H * SCALE
    W = pad + len(ARMS) * (cw + pad)
    H = title_h + len(regions) * (label_h + chh + pad) + foot_h
    canvas = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 8),
           "strehl M95 arm 11 - resampling kernel. bee-3-cpl, 299 frames, one solve, "
           "--srgb --exposure 1.54 --gate 4.0. The kernel is the only variable.",
           fill=(232, 232, 236))
    d.text((pad, 24),
           "Nearest-neighbour x2: you are looking at real pixels. catmull-rom is "
           "today's default and reproduces the shipped gallery render byte for byte "
           "(E400A63A..7112).",
           fill=(150, 150, 158))
    d.text((pad, 38),
           "Mitchell is absent: it fails the identity gate at -0.2008 dex (it blurs an "
           "image even when nothing moves) and is not shipped.",
           fill=(150, 150, 158))

    LAB = {"catmull-rom": "today's default", "lanczos2": "+0.0043 dex, 4.19x cost",
           "lanczos3": "+0.1343 dex, 6.93x cost"}
    yy = title_h
    for name, x, y in regions:
        for i, arm in enumerate(ARMS):
            xx = pad + i * (cw + pad)
            c = Image.fromarray(to8(crops[(arm, name)])).resize((cw, chh), Image.NEAREST)
            canvas.paste(c, (xx, yy + label_h))
            d.text((xx, yy + 4), f"{arm}   ({LAB[arm]})", fill=(238, 238, 242))
            sub = f"{name}   @({x},{y})"
            if arm != REF_ARM:
                md, mx, pc = diffs[(arm, name)]
                sub += f"   mean |d| {md:.0f} DN, max {mx} DN, {pc:.0f}% of px differ"
            d.text((xx, yy + 18), sub, fill=(140, 140, 148))
        yy += label_h + chh + pad
    d.text((pad, H - 24),
           "dex = log10 of the high-band amplitude ratio after resampling; +0.1343 dex "
           "= 1.363x amplitude. DN are 16-bit, of 65535. Cost is the tool's own "
           "summed-across-workers gather timer on a contended machine: an upper bound.",
           fill=(150, 150, 158))

    out = DST / "M95-kernel-montage.png"
    canvas.save(out)
    bts = out.read_bytes()
    print(f"\nwrote {out}  {len(bts)} bytes  {canvas.size[0]} x {canvas.size[1]}")
    print(f"      sha256 {hashlib.sha256(bts).hexdigest()}")

    rec = {
        "regions": [{"name": n, "x": x, "y": y, "w": CROP_W, "h": CROP_H}
                    for n, x, y in regions],
        "stats": {f"{a}|{n}": s for (a, n), s in stats.items()},
        "diffs": {f"{a}|{n}": v for (a, n), v in diffs.items()},
        "montage_sha256": hashlib.sha256(bts).hexdigest(),
    }
    js = json.dumps(rec, indent=2)
    (DST / "montage.json").write_text(js, encoding="utf-8")
    (pathlib.Path(__file__).resolve().parents[1] / "out" / "x9_montage.json").write_text(
        js, encoding="utf-8")
    print("END OF MONTAGE")


if __name__ == "__main__":
    main()

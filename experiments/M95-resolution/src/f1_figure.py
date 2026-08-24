"""The deliverable: before/after 100 % crops of bee-3-cpl.

LEFT is the shipped default -- the binned 8.2 MP render, upscaled 2x with
Lanczos so it occupies the same display area as the right panel. Lanczos, not
nearest, is deliberate: nearest would make the default look blocky and would be
a strawman. The default is given the most flattering upscale available.

RIGHT is the same stack rendered through `--demosaic`, 32.9 MP, shown 1:1.

CROP SELECTION IS BLIND TO THE EFFECT. Tiles are ranked by gradient energy
measured on the LEFT panel only -- the same criterion r0_recon.py used, computed
on the before-image, which cannot know where the right panel gains most.

Panels carry no sharpness number. The one number in the caption is the
destroyed-fraction measured on that exact crop by s6's estimator.

A DEFECT IN THE FIRST VERSION OF THIS SCRIPT, RECORDED BECAUSE IT MATTERED. It
extracted the G1/G2 pair by sub-sampling the BINNED render on a quincunx. That
is wrong: the binned render's green is already mean(G1, G2), one value per quad,
so sub-sampling it yields two interleaved copies of the mean and not the two
greens at all. The per-crop percentages it printed were measuring nothing
meaningful. The pair must come from the FULL-RESOLUTION LINEAR render, where the
demosaic passes green through untouched at G sites (demosaic.rs:218-231), and
where G-plane pixel (i, j) maps one-to-one onto binned pixel (i, j).
"""

import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

REN = r"C:\dev\strehl-out\M95-resolution"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s6_signal as S6  # noqa: E402

CROP = 384          # binned px; 768 full-res px


def font(sz):
    for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def to8(a):
    return np.clip(a.astype(np.float64) / 257.0, 0, 255).astype(np.uint8)


def registration_control(binned, demo):
    """The two panels must be the same region. Verify by cross-correlation on a
    central patch; the mapping binned(r,c) -> demosaic(2r,2c) must read (0,0)."""
    br, bc = binned.shape[0] // 2, binned.shape[1] // 2
    n = 256
    b = binned[br:br + n, bc:bc + n, 1].astype(np.float64)
    bu = np.asarray(Image.fromarray(to8(b)).resize((2 * n, 2 * n), Image.LANCZOS),
                    dtype=np.float64)
    d = demo[2 * br:2 * br + 2 * n, 2 * bc:2 * bc + 2 * n, 1].astype(np.float64) / 257.0
    bu -= bu.mean()
    d -= d.mean()
    C = np.fft.ifft2(np.conj(np.fft.fft2(bu)) * np.fft.fft2(d)).real
    pk = np.unravel_index(np.argmax(C), C.shape)
    dy = pk[0] - (2 * n if pk[0] > n else 0)
    dx = pk[1] - (2 * n if pk[1] > n else 0)
    return int(dy), int(dx)


def main():
    binned = tifffile.imread(os.path.join(REN, "ship-binned.tif"))
    demo = tifffile.imread(os.path.join(REN, "ship-demosaic.tif"))
    print("binned   %s = %.2f MP" % (binned.shape, binned.shape[0] * binned.shape[1] / 1e6))
    print("demosaic %s = %.2f MP" % (demo.shape, demo.shape[0] * demo.shape[1] / 1e6))
    assert demo.shape[0] == 2 * binned.shape[0] and demo.shape[1] == 2 * binned.shape[1]

    dy, dx = registration_control(binned, demo)
    print("\n   REGISTRATION CONTROL: peak offset (%+d, %+d) px, must be (0, 0)" % (dy, dx))
    if (dy, dx) != (0, 0):
        print("   -> panels are NOT the same region; refusing to build the figure")
        return 2
    print("   -> panels are the same region")

    g = binned[:, :, 1].astype(np.float64)
    step, cands = 128, []
    for y in range(step, binned.shape[0] - CROP - step, step):
        for x in range(step, binned.shape[1] - CROP - step, step):
            t = g[y:y + CROP, x:x + CROP]
            if t.mean() < 4000:
                continue
            cands.append((float(np.hypot(*np.gradient(t)).mean()), y, x))
    cands.sort(reverse=True)

    picks, used = [], []
    for sc, y, x in cands:
        if all(abs(y - py) > CROP or abs(x - px) > CROP for _s, py, px in used):
            picks.append((sc, y, x))
            used.append((sc, y, x))
        if len(picks) == 4:
            break
    print("\n   crops ranked by gradient of the LEFT panel only (blind to the effect):")
    for i, (sc, y, x) in enumerate(picks):
        print("     C%d  binned (y=%d, x=%d)  gradient %.1f" % (i + 1, y, x, sc))

    # The G1/G2 pair for the caption number comes from the LINEAR full-resolution
    # render at the same gate as the panels -- never from the binned render, whose
    # green is already the mean of the two. Linear, so no tone curve or colour
    # matrix has touched the values. G-plane (i, j) maps onto binned (i, j).
    lin = tifffile.imread(os.path.join(REN, "lin-g2-demosaic.tif"))[:, :, 1].astype(np.float64)
    g1p, g2p = lin[0::2, 1::2], lin[1::2, 0::2]
    assert g1p.shape[0] >= binned.shape[0] - 2 and g1p.shape[1] >= binned.shape[1] - 2, \
        "green plane %s does not correspond to the binned grid %s" % (g1p.shape, binned.shape)
    f_lab, f_cap = font(30), font(21)
    made = []
    for i, (_sc, y, x) in enumerate(picks):
        lo = binned[y:y + CROP, x:x + CROP]
        hi = demo[2 * y:2 * y + 2 * CROP, 2 * x:2 * x + 2 * CROP]
        L = Image.fromarray(to8(lo)).resize((2 * CROP, 2 * CROP), Image.LANCZOS)
        R = Image.fromarray(to8(hi))

        s = min(CROP, g1p.shape[0] - y, g1p.shape[1] - x)
        rep = S6.report(g1p[y:y + s, x:x + s], g2p[y:y + s, x:x + s])
        pct = 100 * rep["destroyed_top_octave"]

        W, H, pad, top, bot = 2 * CROP, 2 * CROP, 12, 46, 62
        cv = Image.new("RGB", (2 * W + 3 * pad, H + top + bot), (18, 18, 20))
        cv.paste(L, (pad, top))
        cv.paste(R, (2 * pad + W, top))
        dr = ImageDraw.Draw(cv)
        dr.text((pad, 10), "BEFORE  default render, 8.2 MP, upscaled 2x (Lanczos)",
                font=f_lab, fill=(255, 210, 120))
        dr.text((2 * pad + W, 10), "AFTER  --demosaic, 32.9 MP, shown 1:1",
                font=f_lab, fill=(150, 235, 150))
        dr.text((pad, top + H + 8),
                "bee-3-cpl, 299 frames, --gate 2.0 --srgb.  Same stack, same crop, "
                "same tone curve; only the output branch differs.", font=f_cap,
                fill=(190, 190, 195))
        dr.text((pad, top + H + 34),
                "Green signal power destroyed by binning on this crop, top octave: "
                "%.1f %%  (measured on this crop, not on the panels)" % pct,
                font=f_cap, fill=(190, 190, 195))
        p = os.path.join(REN, "M95-resolution-C%d.png" % (i + 1))
        cv.save(p)
        made.append({"crop": i + 1, "y": y, "x": x, "destroyed_top_octave_pct": pct,
                     "path": p})
        print("     wrote %s  (destroyed %.1f %%)" % (os.path.basename(p), pct))

    with open(os.path.join(OUT, "f1_figure.json"), "w", encoding="utf-8") as f:
        json.dump({"registration_offset": [dy, dx], "crops": made,
                   "binned_mp": binned.shape[0] * binned.shape[1] / 1e6,
                   "demosaic_mp": demo.shape[0] * demo.shape[1] / 1e6}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""M116-promotion — CA crops. The deliverable the owner actually looks at.

Window selection is NON-COMPARED. Windows are ranked by gradient energy in the
GREEN plane, and green is the profile's reference channel: it has no
coefficient, `compose` leaves it untouched, and campaign 4 measured its
displacement between the arms at exactly 0.0000 px. So the ranking is
identical in both arms by construction and cannot have been chosen to flatter
the correction. This is the device M87 §16.10 used for the same reason.

Crops are cut from the --srgb renders, which exist ONLY for looking at; every
number in the report comes from the linear pair. Both arms share one frozen
exposure literal, so neither can move its own tone scale.

Captions state the measured displacement, not an impression. And per M110
discipline 59 the correction makes fringes FAINTER, NOT THINNER -- nothing
here is captioned as sharpening.

Run: python crops_ca.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy.ndimage import uniform_filter

CA = Path(r"C:\dev\strehl-out\M116\ca")
OUT = Path(r"C:\dev\strehl-out\M116\images-ca")

# Only the subjects whose instrument CALIBRATED are captioned with a number.
CALIBRATED = {"flat-on-ruler-cpl": 0.901, "tweezers-cpl": 0.952}
SUBJECTS = ["tweezers-cpl", "flat-on-ruler-cpl", "bee-3-cpl",
            "flower-bud-with-background-fern-cpl"]

CROP = 240         # 1:1 crop side, output px
ZOOM = 4           # nearest-neighbour magnification for the second sheet
NCROPS = 3
R_MIN = 0.55       # lateral CA is a radial effect: crop where it lives
PAD = 16


def to8(a: np.ndarray) -> np.ndarray:
    return (np.clip(a.astype(np.float32) / 65535.0, 0, 1) * 255).astype(np.uint8)


def pick_windows(g: np.ndarray, n: int):
    """Highest green-plane gradient energy, at radius >= R_MIN, non-overlapping."""
    gy, gx = np.gradient(g.astype(np.float32))
    energy = uniform_filter(np.hypot(gy, gx), size=CROP, mode="constant")
    h, w = g.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cy, cx))
    yy, xx = np.mgrid[0:h, 0:w]
    rad = np.hypot(yy - cy, xx - cx) / rmax
    energy = np.where(rad >= R_MIN, energy, -1.0)
    r = CROP // 2
    energy[:r + PAD, :] = -1; energy[-(r + PAD):, :] = -1
    energy[:, :r + PAD] = -1; energy[:, -(r + PAD):] = -1

    picks = []
    e = energy.copy()
    for _ in range(n):
        idx = int(np.argmax(e))
        py, px = divmod(idx, w)
        if e[py, px] <= 0:
            break
        picks.append((py, px, float(rad[py, px])))
        y0, y1 = max(0, py - CROP), min(h, py + CROP)
        x0, x1 = max(0, px - CROP), min(w, px + CROP)
        e[y0:y1, x0:x1] = -1
    return picks


def cut(a: np.ndarray, py: int, px: int) -> np.ndarray:
    r = CROP // 2
    return a[py - r:py + r, px - r:px + r, :]


def sheet(pairs, title, sub, zoom=1):
    """OFF | ON side by side, one row per crop, with a header."""
    cw = CROP * zoom
    head, gap, lab = 58, 14, 22
    W = cw * 2 + gap * 3
    H = head + len(pairs) * (cw + lab + gap)
    im = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(im)
    d.text((gap, 10), title, fill=(255, 255, 255))
    d.text((gap, 30), sub, fill=(170, 170, 170))
    y = head
    for (off, on, meta) in pairs:
        for i, img in enumerate((off, on)):
            a = np.repeat(np.repeat(img, zoom, 0), zoom, 1) if zoom > 1 else img
            im.paste(Image.fromarray(a), (gap + i * (cw + gap), y))
        d.text((gap, y + cw + 4),
               f"OFF (default)   |   ON (STREHL_FIX_CA)      "
               f"crop at normalised radius r = {meta['r']:.2f}"
               f"   {'1:1' if zoom == 1 else f'{zoom}x nearest-neighbour'}",
               fill=(200, 200, 200))
        y += cw + lab + gap
    return im


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    disp = json.loads((CA / "scores-ca-disp.json").read_text(encoding="utf-8"))
    made = []

    for s in SUBJECTS:
        p_off, p_on = CA / "view" / f"{s}__OFF.tif", CA / "view" / f"{s}__ON.tif"
        if not (p_off.exists() and p_on.exists()):
            continue
        off, on = tifffile.imread(p_off), tifffile.imread(p_on)
        g = off[:, :, 1]
        picks = pick_windows(g, NCROPS)
        if not picks:
            print(f"  {s}: no window passed the radius filter")
            continue

        pairs = []
        for (py, px, r) in picks:
            pairs.append((to8(cut(off, py, px)), to8(cut(on, py, px)),
                          {"r": r, "y": py, "x": px}))

        rec = disp["subjects"].get(s, {})
        if s in CALIBRATED:
            cap = (f"lateral CA removed: {100 * CALIBRATED[s]:.1f}%   "
                   f"(radial R-vs-G displacement "
                   f"{rec.get('support_rd_off', float('nan')):+.3f} px -> "
                   f"{rec.get('support_rd_on', float('nan')):+.3f} px, "
                   f"instrument CALIBRATED: planted 0.5 px recovered)")
        else:
            cap = ("INSTRUMENT NOT CALIBRATED on this subject -- a planted "
                   "0.500 px shift read back as <=0.12 px, so NO displacement "
                   "number is claimed here. Shown for looking only.")

        title = f"{s}  --  lateral chromatic aberration, OFF vs ON"
        subttl = (cap + "   |  sRGB, one frozen exposure, pinned SHA 4beac73."
                  "  Fringes get FAINTER, NOT THINNER -- this is not sharpening.")

        for z, tag in ((1, "1to1"), (ZOOM, f"{ZOOM}x")):
            im = sheet(pairs, title, subttl, zoom=z)
            dst = OUT / f"{s}__CA-{tag}.png"
            im.save(dst)
            made.append(str(dst))
            print(f"  wrote {dst.name}  ({im.size[0]}x{im.size[1]})")
        del off, on

    (OUT / "INDEX.txt").write_text(
        "M116 campaign 4 -- lateral chromatic aberration crops\n"
        "=====================================================\n\n"
        "Window selection is NON-COMPARED: windows are ranked by GREEN-plane\n"
        "gradient energy, and green is measured to move 0.0000 px between the\n"
        "arms, so the ranking is identical in both and cannot flatter either.\n\n"
        "CALIBRATED subjects (a planted 0.500 px shift was recovered):\n"
        "  tweezers-cpl        95.2% of lateral CA removed  (TRANSFER: M110 never used it)\n"
        "  flat-on-ruler-cpl   90.1% of lateral CA removed\n\n"
        "NOT CALIBRATED (planted 0.500 px read back as 0.015 / 0.120 px):\n"
        "  bee-3-cpl, flower-bud-with-background-fern-cpl\n"
        "  No displacement number is claimed on these two. Their earlier\n"
        "  Q = 0.400 / 0.330 are VOID, not small.\n\n"
        + "\n".join(made) + "\n", encoding="utf-8")
    print(f"\n{len(made)} sheets in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

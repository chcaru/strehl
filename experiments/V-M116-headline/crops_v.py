"""V-M116 probe 4: look at the arm that produced the headline.

M116's crops.py renders arms B0, M0, A0, A1..A4. It does NOT render B1u -- the
arm on the merge side of the headline comparison. So no picture of the headline
arm exists. This makes one, at 1:1, from the MEASUREMENT tiff (linear, binned,
camera-native), with a fixed tone curve shared by both arms so the arms differ
in the merge and not in the gain.
"""
import sys
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image, ImageDraw

M = Path(r"C:\dev\strehl-out\M116\measure")
OUT = Path(r"C:\dev\strehl-out\V-M116\images")
OUT.mkdir(parents=True, exist_ok=True)
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
ARMS = ["B0", "B1u", "M0u"]
CROP = 512


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16"
    return a


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    small = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    m1, m2 = box(small, 33), box(small * small, 33)
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    out = np.zeros(g.shape, np.float64)
    out[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def best_window(st, want_high):
    h, w = st.shape
    integ = box(st, CROP)          # centred box mean, edge replicated
    half = CROP // 2
    valid = integ[half:h - half, half:w - half]
    idx = np.argmax(valid) if want_high else np.argmin(valid)
    y, x = np.unravel_index(idx, valid.shape)
    return int(x), int(y)


def tone(a, scale):
    """shared linear->display curve; identical constant for every arm."""
    x = np.clip(a.astype(np.float64) / scale, 0, 1)
    return (255.0 * np.where(x <= 0.0031308, 12.92 * x,
                             1.055 * np.power(x, 1 / 2.4) - 0.055)).astype(np.uint8)


for s in SUBJECTS:
    ref = load(M / f"{s}__M0u.tif")
    st = structure(ref[:, :, 1].astype(np.float64))
    wins = {"detail": best_window(st, True), "flat": best_window(st, False)}
    scale = float(np.percentile(ref, 99.5))
    print(f"{s}: tone scale {scale:.0f}, windows {wins}")
    panels = {"detail": [], "flat": []}
    for arm in ARMS:
        a = load(M / f"{s}__{arm}.tif")
        for kind, (x, y) in wins.items():
            c = tone(a[y:y + CROP, x:x + CROP, :], scale)
            im = Image.fromarray(c)
            im.save(OUT / f"{s}__{arm}__{kind}.png")
            lab = Image.new("RGB", (CROP, CROP + 22), (16, 16, 16))
            lab.paste(im, (0, 22))
            ImageDraw.Draw(lab).text((5, 5), f"{arm}  {s}  {kind} @ {(x,y)}",
                                     fill=(255, 255, 255))
            panels[kind].append(lab)
    for kind, ps in panels.items():
        w = sum(p.width for p in ps) + 8 * (len(ps) + 1)
        sheet = Image.new("RGB", (w, ps[0].height + 16), (28, 28, 28))
        x = 8
        for p in ps:
            sheet.paste(p, (x, 8)); x += p.width + 8
        sheet.save(OUT / f"{s}__V-contact-{kind}.png")
        print(f"  wrote {s}__V-contact-{kind}.png")

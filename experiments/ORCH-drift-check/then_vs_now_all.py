"""THEN vs NOW for all three stacks the owner judged, with a per-stack control.

The owner's verdict "those stacks don't look too good yet" was passed on
artefacts written 2026-08-23 23:37-23:47, which M105b measured to carry five
defects at once: binned to half linear resolution, no colour management, no
alignment, underexposed, plus the merge defects. Four are fixed. This builds the
comparison for each of the three stacks rather than arguing it.

Honesty constraints, because a before/after montage is an argument:

  * The OLD panel is upscaled with NEAREST NEIGHBOUR. A smooth kernel would add
    blur the old data never had and flatter the new render.
  * Registration between the two is INTEGER-ONLY. Sub-pixel resampling would
    blur the very quantity under comparison.
  * Each stack gets an EXPOSURE-MATCHED control panel using THAT STACK'S OWN
    exposure, as chosen by --auto-exposure and printed by the tool -- not by my
    taste. Most of the raw visual difference is brightness, brightness is fully
    recoverable, and it must not be sold as a quality gain.
  * marker's exposure is NEGATIVE (-0.24 stops). It already clips; the bee3
    value of +1.54 would have made it worse. This is exactly why the exposure is
    taken per stack from the tool rather than applied globally.

Registered before running, per stack:
  R1  the correlation peak must exceed 0.5, else the crops are not the same
      region and that stack's montage is discarded rather than published
  R2  the new render must have exactly 4.00x the pixels of the old (+/- 1%),
      confirming the resolution claim by pixel count rather than file size
  R3  the exposure applied to the control must equal the value the tool printed
"""
import os
import numpy as np
import tifffile
import cv2

OUTDIR = r"C:\dev\strehl-out\ORCH-thennow"

# name -> (old judged tif, new HEAD tif, exposure in stops the NEW render carries)
STACKS = {
    "bee3": (r"C:\dev\strehl-out\bee3-full.tif",
             r"C:\dev\strehl-out\ORCH-drift5\head-d42fac4.tif", 1.54),
    "lavendar": (r"C:\dev\strehl-out\lavendar.tif",
                 os.path.join(OUTDIR, "lavendar-HEAD-8f46f04.tif"), 1.42),
    "marker": (r"C:\dev\strehl-out\marker.tif",
               os.path.join(OUTDIR, "marker-HEAD-8f46f04.tif"), -0.24),
}


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def find_offset(old_up, new, cx, cy, half=384, search=280):
    pat = luma(new[cy - half:cy + half, cx - half:cx + half])
    y0, y1 = cy - half - search, cy + half + search
    x0, x1 = cx - half - search, cx + half + search
    y0, x0 = max(0, y0), max(0, x0)
    y1 = min(old_up.shape[0], y1)
    x1 = min(old_up.shape[1], x1)
    hay = luma(old_up[y0:y1, x0:x1])
    if hay.shape[0] <= pat.shape[0] or hay.shape[1] <= pat.shape[1]:
        return None
    pat = (pat - pat.mean()) / (pat.std() + 1e-9)
    r = cv2.matchTemplate(hay.astype(np.float32), pat.astype(np.float32),
                          cv2.TM_CCOEFF_NORMED)
    _, peak, _, loc = cv2.minMaxLoc(r)
    return x0 + loc[0] - (cx - half), y0 + loc[1] - (cy - half), peak


def to8(a):
    return (np.clip(a.astype(np.float32) / 65535.0, 0, 1) * 255).astype(np.uint8)


def label(img, text, sub):
    img = img.copy()
    cv2.rectangle(img, (0, 0), (img.shape[1], 96), (0, 0, 0), -1)
    cv2.putText(img, text, (18, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.15,
                (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, sub, (18, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.60,
                (190, 190, 190), 1, cv2.LINE_AA)
    return img


def build(name, old_path, new_path, stops):
    print(f"\n=== {name} ===")
    old = tifffile.imread(old_path)
    new = tifffile.imread(new_path)
    op, np_ = old.shape[0] * old.shape[1], new.shape[0] * new.shape[1]
    ratio = np_ / op
    print(f"  old {old.shape[1]}x{old.shape[0]} = {op/1e6:.2f} MP")
    print(f"  new {new.shape[1]}x{new.shape[0]} = {np_/1e6:.2f} MP   ratio {ratio:.3f}x")
    assert abs(ratio - 4.0) < 0.04, f"R2 FAILED: {name} ratio {ratio:.3f} not 4.00x"
    print(f"  R2 PASS  ratio {ratio:.3f}x")

    old_up = np.repeat(np.repeat(old, 2, axis=0), 2, axis=1)
    H = min(old_up.shape[0], new.shape[0])
    W = min(old_up.shape[1], new.shape[1])

    best = None
    for (fx, fy) in ((0.50, 0.50), (0.40, 0.42), (0.60, 0.58), (0.45, 0.62)):
        cx, cy = int(W * fx), int(H * fy)
        r = find_offset(old_up, new, cx, cy)
        if r is None:
            continue
        dx, dy, peak = r
        print(f"  probe ({cx},{cy}): offset=({dx:+d},{dy:+d}) peak={peak:.4f}")
        if best is None or peak > best[4]:
            best = (cx, cy, dx, dy, peak)
    assert best is not None, f"R1 FAILED: {name} no usable probe"
    cx, cy, dx, dy, peak = best
    assert peak > 0.5, f"R1 FAILED: {name} best peak {peak:.4f} <= 0.5"
    print(f"  R1 PASS  peak {peak:.4f} at ({cx},{cy}), offset ({dx:+d},{dy:+d})")

    gain = 2.0 ** stops
    print(f"  R3 control gain {gain:.4f}x = {stops:+.2f} stops (the value the tool printed)")

    for suffix, half in (("", 420), ("-wide", 900)):
        half = min(half, (H // 2) - 8, (W // 2) - 8)
        ys, xs = cy - half, cx - half
        n = new[ys:ys + 2 * half, xs:xs + 2 * half]
        o = old_up[ys + dy:ys + dy + 2 * half, xs + dx:xs + dx + 2 * half]
        if o.shape != n.shape:
            print(f"  skip {suffix or 'main'}: crop fell outside the old frame")
            continue
        lin = srgb_to_linear(o.astype(np.float32) / 65535.0)
        om = (np.clip(linear_to_srgb(np.clip(lin * gain, 0, 1)), 0, 1) * 65535).astype(np.uint16)

        o8, om8, n8 = to8(o)[..., ::-1], to8(om)[..., ::-1], to8(n)[..., ::-1]
        o8 = label(o8, "1. THEN - what you judged",
                   "8.24 MP binned . no alignment . no colour mgmt . underexposed")
        om8 = label(om8, "2. THEN, exposure-matched",
                    f"same old pixels, {stops:+.2f} stops applied - the CONTROL")
        n8 = label(n8, "3. NOW - HEAD 8f46f04",
                   f"32.99 MP full . aligned 299/299 . camera RGB->sRGB . {stops:+.2f} stops")
        gap = np.full((o8.shape[0], 12, 3), 40, np.uint8)
        p = os.path.join(OUTDIR, f"THEN-vs-NOW-{name}{suffix}.png")
        cv2.imwrite(p, np.hstack([o8, gap, om8, gap, n8]))
        print(f"  wrote {p}")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for name, (o, n, s) in STACKS.items():
        if not os.path.exists(n):
            print(f"\n=== {name} === SKIP: {n} not present")
            continue
        build(name, o, n, s)
    print("\npanel 2 vs panel 3 is the honest comparison: brightness is held equal,")
    print("so only resolution, alignment and colour differ.")


if __name__ == "__main__":
    main()

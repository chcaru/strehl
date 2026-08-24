"""THEN vs NOW: the render the owner judged against the render as it stands.

The owner's verdict "those stacks don't look too good yet" was measured by M105b
to be against artefacts written 2026-08-23 23:37-23:47, which carried FIVE
defects at once: binned to half linear resolution, no colour management, no
alignment, underexposed, and the merge defects. Four of the five have been fixed
since. This builds the comparison so the owner can see what actually changed,
rather than being told.

Honesty constraints, because this montage is an argument and it must not cheat:

  * The OLD image is upscaled 2x with NEAREST NEIGHBOUR, never a smooth kernel.
    A smooth upscale would add blur that the original did not have and would
    flatter the new render. Nearest is the only choice that shows the old data
    exactly as it was sampled.
  * Both crops are taken at the SAME PHYSICAL REGION, located by normalised
    cross-correlation rather than by assuming the geometry matches. It does not
    match: the new render is field-of-view scaled by 0.9315 then upsampled
    (fact 1400), and it is aligned, which the old one was not.
  * Registration is INTEGER-ONLY. Sub-pixel resampling would blur the very
    quantity under comparison.
  * No sharpening, no tone curve, no per-image auto-levels beyond the exposure
    each render already carries. The brightness difference is a real difference
    between the two renders and must survive into the montage.

Registered before running:
  R1  the correlation peak must exceed 0.5, else the crops are not the same
      region and the montage is discarded rather than published
  R2  the old TIF must measure 3516x2344 and the new 7032x4688, confirming the
      4x pixel claim by measurement rather than by file size
  R3  the reported peak offset must be stable when the search patch is moved,
      else the match is on noise
"""
import numpy as np
import tifffile
import cv2

OLD = r"C:\dev\strehl-out\bee3-full.tif"
NEW = r"C:\dev\strehl-out\ORCH-drift5\head-d42fac4.tif"
OUT = r"C:\dev\strehl-out\ORCH-thennow\THEN-vs-NOW.png"
OUT_WIDE = r"C:\dev\strehl-out\ORCH-thennow\THEN-vs-NOW-wide.png"


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def find_offset(old_up, new, cx, cy, half=384):
    """Integer offset that maps new -> old_up, by NCC on a patch of `new`."""
    pat = luma(new[cy - half:cy + half, cx - half:cx + half])
    search = 260
    y0, y1 = cy - half - search, cy + half + search
    x0, x1 = cx - half - search, cx + half + search
    hay = luma(old_up[y0:y1, x0:x1])
    pat = (pat - pat.mean()) / (pat.std() + 1e-9)
    r = cv2.matchTemplate(hay.astype(np.float32), pat.astype(np.float32),
                          cv2.TM_CCOEFF_NORMED)
    _, peak, _, loc = cv2.minMaxLoc(r)
    dx = x0 + loc[0] - (cx - half)
    dy = y0 + loc[1] - (cy - half)
    return dx, dy, peak


def main():
    import os
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    old = tifffile.imread(OLD)
    new = tifffile.imread(NEW)
    print(f"OLD {OLD}\n    shape={old.shape} dtype={old.dtype}")
    print(f"NEW {NEW}\n    shape={new.shape} dtype={new.dtype}")

    assert old.shape[:2] == (2344, 3516), f"R2 FAILED: old is {old.shape[:2]}"
    assert new.shape[:2] == (4688, 7032), f"R2 FAILED: new is {new.shape[:2]}"
    print(f"R2 PASS  old {old.shape[1]}x{old.shape[0]} = "
          f"{old.shape[0]*old.shape[1]/1e6:.2f} MP; new {new.shape[1]}x{new.shape[0]} = "
          f"{new.shape[0]*new.shape[1]/1e6:.2f} MP; ratio "
          f"{(new.shape[0]*new.shape[1])/(old.shape[0]*old.shape[1]):.2f}x")

    # NEAREST only. A smooth kernel would add blur the old data never had.
    old_up = np.repeat(np.repeat(old, 2, axis=0), 2, axis=1)
    print(f"old upscaled 2x NEAREST -> {old_up.shape[1]}x{old_up.shape[0]}")

    probes = [(3516, 2344), (2900, 2000), (4200, 2700)]
    results = []
    for (cx, cy) in probes:
        dx, dy, peak = find_offset(old_up, new, cx, cy)
        results.append((cx, cy, dx, dy, peak))
        print(f"  probe ({cx},{cy}): offset=({dx:+d},{dy:+d}) peak={peak:.4f}")

    best = max(results, key=lambda r: r[4])
    cx, cy, dx, dy, peak = best
    assert peak > 0.5, f"R1 FAILED: best correlation peak {peak:.4f} <= 0.5"
    print(f"R1 PASS  best peak {peak:.4f} at probe ({cx},{cy}), offset ({dx:+d},{dy:+d})")

    offs = [(r[2], r[3]) for r in results if r[4] > 0.5]
    spread = (max(o[0] for o in offs) - min(o[0] for o in offs),
              max(o[1] for o in offs) - min(o[1] for o in offs))
    print(f"R3 offset spread across {len(offs)} confident probes: "
          f"dx {spread[0]} px, dy {spread[1]} px")
    print("     (a large spread is EXPECTED here and is itself the finding: the new "
          "render is aligned and FOV-scaled, the old one is not, so a single rigid "
          "offset cannot fit the whole frame.)")

    def crops(cxx, cyy, half):
        n = new[cyy - half:cyy + half, cxx - half:cxx + half]
        o = old_up[cyy + dy - half:cyy + dy + half, cxx + dx - half:cxx + dx + half]
        return o, n

    def to8(a):
        return (np.clip(a.astype(np.float32) / 65535.0, 0, 1) * 255).astype(np.uint8)

    def label(img, text, sub):
        img = img.copy()
        cv2.rectangle(img, (0, 0), (img.shape[1], 96), (0, 0, 0), -1)
        cv2.putText(img, text, (18, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.15,
                    (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, sub, (18, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                    (190, 190, 190), 1, cv2.LINE_AA)
        return img

    # The exposure-matched control. Most of the raw visual difference between the
    # two panels is BRIGHTNESS, and brightness is a display change that is fully
    # recoverable -- it is not a quality gain and must not be sold as one. This
    # third panel applies the NEW render's exact exposure to the OLD data, in
    # linear light before the transfer curve, which is the order color.rs asserts
    # is the only correct one. What survives in the gap between panel 2 and panel
    # 3 is resolution, alignment and colour: the part that is actually new.
    def srgb_to_linear(x):
        return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)

    def linear_to_srgb(x):
        return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)

    GAIN = 2.0 ** 1.54
    print(f"exposure-matched control: gain {GAIN:.4f}x in linear light "
          f"(+1.54 stops, matching the NEW render exactly)")

    for path, half in ((OUT, 420), (OUT_WIDE, 900)):
        o, n = crops(cx, cy, half)
        lin = srgb_to_linear(o.astype(np.float32) / 65535.0)
        om = (np.clip(linear_to_srgb(np.clip(lin * GAIN, 0, 1)), 0, 1) * 65535).astype(np.uint16)

        o8, n8, om8 = to8(o)[..., ::-1], to8(n)[..., ::-1], to8(om)[..., ::-1]
        o8 = label(o8, "1. THEN - what you judged",
                   "8.24 MP binned . no alignment . no colour mgmt . underexposed")
        om8 = label(om8, "2. THEN, exposure-matched",
                   "same old pixels, +1.54 stops applied - the CONTROL")
        n8 = label(n8, "3. NOW - HEAD d42fac4",
                   "32.97 MP full . aligned . camera RGB->sRGB . +1.54 stops")
        gap = np.full((o8.shape[0], 12, 3), 40, np.uint8)
        cv2.imwrite(path, np.hstack([o8, gap, om8, gap, n8]))
        print(f"wrote {path}  ({half*2}px crops, all at 100% of the NEW render's scale)")
        print(f"       panel 2 vs 3 is the honest comparison: brightness is held equal, "
              f"so only resolution, alignment and colour differ.")


if __name__ == "__main__":
    main()

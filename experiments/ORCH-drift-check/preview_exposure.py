"""Preview what M100's exposure fix will look like, without waiting for the patch.

M100 measured the viewing renders underexposed by +1.54 stops on bee-3 and
+3.74 on lead-1, and its patch is queued behind a contended file. This applies
the same per-stack gains to the EXISTING gallery so the result can be looked at
now, and so there is a before/after to judge in the morning either way.

THIS IS A PREVIEW, NOT THE FIX, and the difference is not cosmetic:

  - M100 applies its gain in LINEAR light BEFORE the clamp to 16-bit. This
    script only has the already-clamped, already-sRGB-encoded TIFF, so anything
    the render clipped is gone and no gain brings it back. Where a stack was
    over-exposed (coffee-bean, foam, both of which get NEGATIVE stops) the real
    fix recovers highlight detail that this preview cannot.
  - So the preview is faithful for the stacks being BRIGHTENED and pessimistic
    for the ones being DARKENED. Judge the darkened ones from the real render.

It decodes sRGB properly rather than scaling the encoded values, because a gain
applied to gamma-encoded data is the wrong operation and would shift colour as
well as brightness.

READ-ONLY on the source renders: every output goes to a new -EXPOSED.tif.
"""
import glob
import os
import sys

import numpy as np
import tifffile

# M100's measured per-stack choices, in stops.
STOPS = {
    "bee-2": 1.54,
    "bee-3": 1.54,
    "coffee-bean": -0.18,
    "flat-on-ruler": 1.96,
    "foam": -0.32,
    "highly-angled-ruler": 1.19,
    "lead-1": 3.74,
}


def srgb_decode(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb_encode(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def stops_for(name):
    """Longest matching key, so 'bee-3-cpl-g0' resolves to 'bee-3' not 'bee-2'."""
    best = None
    for k in STOPS:
        if name.startswith(k) and (best is None or len(k) > len(best)):
            best = k
    return best, (STOPS[best] if best else None)


def main(pattern):
    paths = sorted(glob.glob(pattern))
    paths = [p for p in paths if "-EXPOSED" not in p and "GATE-STRIP" not in p]
    if not paths:
        sys.exit(f"nothing matched {pattern}")

    print(f"{'file':<34} {'stops':>7} {'clipped%':>9}  note")
    for p in paths:
        name = os.path.basename(p)
        key, st = stops_for(name)
        if st is None:
            print(f"{name:<34} {'--':>7} {'--':>9}  no M100 stop for this stack, skipped")
            continue

        a = tifffile.imread(p)
        if a.dtype != np.uint16:
            print(f"{name:<34} {'--':>7} {'--':>9}  not uint16, skipped")
            continue

        lin = srgb_decode(a.astype(np.float32) / 65535.0)
        lin *= (2.0 ** st)
        clipped = 100.0 * float((lin > 1.0).mean())
        out = np.rint(srgb_encode(lin) * 65535.0).astype(np.uint16)

        dst = p.replace(".tif", "-EXPOSED.tif")
        tifffile.imwrite(dst, out, photometric="rgb")
        note = "preview pessimistic (highlights already clipped)" if st < 0 else ""
        print(f"{name:<34} {st:>+7.2f} {clipped:>9.4f}  {note}")

    print("\nWrote -EXPOSED.tif alongside each source. Sources untouched.")
    print("For the DARKENED stacks, judge from the real render, not this.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else r"C:\dev\strehl-out\ORCH-gallery\*-srgb.tif"))

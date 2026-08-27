"""Is the tweezers rim a stacking artifact, or specular rim light the optics delivered?

The corpus-wide halo metric certifies exactly one master, `tweezers-cpl`, at 0.945 step
units. That master is polished metal -- the most specular subject in the corpus -- which is
a competing explanation the metric cannot distinguish on its own: a genuine specular edge
highlight and an overshoot artifact have the same shape in a normalised profile.

The discriminating control: measure the same profile geometry on a *single decoded source
frame*. A rim the optics delivered is present in the individual exposures. A rim the merge
manufactured is not. Nothing about the merge can be blamed for structure already in the
inputs, and nothing about the optics can explain structure that only exists after merging.

Frames are decoded with rawpy at fixed settings (no auto-bright, no user WB) so the tonal
scale is stated rather than fitted; the profile is normalised per-edge exactly as
orch_halo.py does, so the two numbers are directly comparable.
"""
import pathlib
import sys

import numpy as np
import rawpy
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_halo import (BAND, DS, HALF, PLATEAU_FRAC, bilinear, downsample,  # noqa: E402
                       edge_points, robust_step)

SRC = pathlib.Path(r"D:\personal\macro\tweezers-cpl")
MASTER = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2\tweezers-cpl--SHIP-V2.tiff")


def decode(p):
    with rawpy.imread(str(p)) as r:
        return r.postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16,
                             use_camera_wb=True, output_color=rawpy.ColorSpace.sRGB)


def lum_of(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2]).astype(np.float32)


def halo_of(img, rng, tag):
    """Median normalised overshoot, same gates and band as orch_halo.py."""
    ms = robust_step(img)
    pts, gy, gx, _ = edge_points(img, rng)
    t = np.arange(-HALF, HALF + 1, dtype=np.float32)
    a, b = BAND
    prof, rej = [], 0
    for (py, px) in pts:
        g = np.hypot(gy[py, px], gx[py, px])
        if g <= 0:
            continue
        ny, nx = gy[py, px] / g, gx[py, px] / g
        v = bilinear(img, py + t * ny, px + t * nx)
        lo, hi = float(v[:15].mean()), float(v[-15:].mean())
        if abs(hi - lo) < ms:
            rej += 1
            continue
        step = abs(hi - lo)
        lf = abs(float(v[:20].mean()) - float(v[20:40].mean()))
        rf = abs(float(v[-20:].mean()) - float(v[-40:-20].mean()))
        if max(lf, rf) > PLATEAU_FRAC * step:
            rej += 1
            continue
        prof.append((v - lo) / (hi - lo))
    if len(prof) < 60:
        print(f"  {tag:28s} only {len(prof)} profiles -- no reading")
        return None, len(prof)
    p = np.median(np.stack(prof), axis=0)
    oh = float(np.max(p[HALF + a:HALF + b]) - 1.0)
    ol = float(0.0 - np.min(p[HALF - b:HALF - a]))
    h = max(max(oh, ol), 0.0)
    print(f"  {tag:28s} halo {h:7.4f}   profiles {len(prof):5d}  rejected {rej:5d}  "
          f"peak {float(np.max(p[HALF + a:HALF + b])):.3f}")
    return h, len(prof)


def main():
    rng = np.random.default_rng(99)
    raws = sorted([p for p in SRC.iterdir() if p.suffix.lower() == ".arw"])
    print(f"source {SRC}: {len(raws)} raw frames")
    if not raws:
        return 1

    print("\nARM MASTER  the shipped stack")
    a = tifffile.imread(str(MASTER))
    hm, _ = halo_of(downsample(lum_of(a[:, :, :3]), DS), rng, "tweezers-cpl SHIP-V2")
    del a

    print("\nARM SINGLE  individual decoded source frames (the control)")
    idx = sorted(set(int(round(x)) for x in np.linspace(0, len(raws) - 1, 12)))
    vals = []
    for i in idx:
        rgb = decode(raws[i])
        h, n = halo_of(downsample(lum_of(rgb), DS), rng, f"frame {i:3d} {raws[i].name}")
        del rgb
        if h is not None:
            vals.append(h)

    print("\n" + "=" * 74)
    if hm is None or not vals:
        print("inconclusive: one arm produced no reading")
        return 1
    med = float(np.median(vals))
    mx = float(np.max(vals))
    print(f"shipped master        {hm:.4f}")
    print(f"single frames  median {med:.4f}   range {min(vals):.4f}..{mx:.4f}")
    print()
    if hm <= mx:
        print(f"VERDICT  the master's {hm:.4f} is BELOW the strongest single frame's "
              f"{mx:.4f}.")
        print( "         A focus stacker selects the sharpest frame at each edge, and at")
        print( "         a specular boundary the sharpest frame is also the one with the")
        print( "         strongest rim. The merge therefore inherits a rim the optics")
        print( "         delivered; it is not manufacturing one. Comparing against the")
        print(f"         median ({med:.4f}) would have wrongly indicted the merge at")
        print(f"         {hm / med:.2f}x, because the median averages in frames whose")
        print( "         edges are defocused and which the merge never selects there.")
        print()
        print( "         NOT ESTABLISHED as a stacking artifact. Do not hand this number")
        print( "         to a lane as a defect target.")
    elif med <= 0.0:
        print("VERDICT  the rim is ABSENT from every single frame -> merge-manufactured.")
    else:
        print(f"VERDICT  the master {hm:.4f} EXCEEDS every single frame (max {mx:.4f}) by "
              f"{hm / mx:.2f}x.")
        print( "         No frame the merge could have selected contains a rim this")
        print( "         strong, so the excess is manufactured and is the merge's to")
        print( "         answer for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

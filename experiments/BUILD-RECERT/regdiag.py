"""Why did three subjects read UNREGISTERED, when both arms share one alignment solve?

flatexp.registration_shift() tests ONE site (sites[0]) and refuses the whole
subject if its SSD argmin is not (0, 0).  Both arms of this experiment were
rendered by one binary from one input set, and their own logs report the SAME
sidecar, the SAME reference frame and the SAME placed/refused counts -- so a
genuine shift would be a serious defect and a spurious one would be a defect in
my guard.  Those are different claims and this script separates them by reading
the SSD surface instead of only its argmin.

The discriminator: if the arms really sit on different grids, SSD(0,0) is far
above the minimum at EVERY site and the argmin agrees between sites.  If the
guard is misfiring, SSD(0,0) sits a hair above a minimum that is essentially
flat, and the argmin disagrees from site to site because noise, not geometry,
is choosing it.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flatexp import DEF_DIR, FLAT_DIR, CROP, content_sites  # noqa: E402

RADIUS = 4


def surface(a, b, y, x, radius=RADIUS):
    pa = a[y:y + CROP, x:x + CROP, 1].astype(np.float32)
    out = {}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            pb = b[y + dy:y + dy + CROP, x + dx:x + dx + CROP, 1].astype(np.float32)
            if pb.shape != pa.shape:
                continue
            out[(dy, dx)] = float(np.mean((pa - pb) ** 2))
    return out


def main(names):
    for name in names:
        dp = DEF_DIR / f"{name}--DEF-2f858c62.tiff"
        fp = FLAT_DIR / f"{name}--FLAT1-2f858c62.tiff"
        if not (dp.exists() and fp.exists()):
            print(f"{name}: MISSING")
            continue
        a = tifffile.imread(dp)
        b = tifffile.imread(fp)
        sites = content_sites(a)
        print(f"\n== {name}   shape={a.shape}  sites={len(sites)}")
        print("  site        argmin     SSD(0,0)      SSD(min)   excess%   "
              "SSD(+-1 ring min)")
        argmins = []
        for i, (y, x) in enumerate(sites):
            s = surface(a, b, y, x)
            zero = s[(0, 0)]
            mn = min(s.values())
            am = min(s, key=s.get)
            argmins.append(am)
            ring = min(v for k, v in s.items()
                       if max(abs(k[0]), abs(k[1])) == 1)
            excess = (zero / mn - 1.0) * 100.0 if mn > 0 else 0.0
            print(f"  {i} ({y:5d},{x:5d}) {str(am):>8}  {zero:11.4f}  "
                  f"{mn:11.4f}  {excess:7.3f}   {ring:11.4f}")
        agree = len(set(argmins)) == 1
        print(f"  argmins agree across sites: {agree}   distinct={set(argmins)}")


if __name__ == "__main__":
    main(sys.argv[1:])

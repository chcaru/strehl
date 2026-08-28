"""Commission the MEASURED_ZERO / CANNOT_MEASURE distinction in carefit.

The defect being closed: `fit_mag_and_offset` recovers each tile's unit radial
vector FROM the displacement vector, so an exactly-zero displacement has no
recoverable direction and the tile was dropped. A perfectly corrected channel
dropped every tile and printed "too few tiles" -- the no-data message. Measured
zero and could not measure were the same string.

Lowering the tile threshold would NOT fix that; it would only move it. The fix
has to distinguish the two states, so this commissions the distinction rather
than the threshold:

  arm ZERO   : strong structure, R = G = B exactly  -> tiles EXIST, displacement
               is zero            -> must say MEASURED ZERO
  arm NODATA : uniform flat field, no gradient      -> tiles do not exist
               at all             -> must say UNSCORED / cannot measure

REQUIREMENT: the two arms must print DIFFERENT strings. If they print the same
string the defect is still present, whatever the string says.

Run through carefit.py's real command line, not by importing it.
"""
import os
import subprocess
import sys

import numpy as np
import tifffile

H, W = 3072, 4096


def structured(rng):
    """Broad structure with real gradients everywhere, so tiles qualify."""
    base = rng.normal(0.0, 1.0, (H // 16, W // 16)).astype(np.float32)
    big = np.kron(base, np.ones((16, 16), np.float32))[:H, :W]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    edges = 3000.0 * ((np.sin(xx / 37.0) > 0).astype(np.float32))
    edges += 3000.0 * ((np.sin(yy / 41.0) > 0).astype(np.float32))
    img = 8000.0 + 2500.0 * big + edges
    return np.clip(img, 0, 65535)


def write(outdir, name, r, g, b):
    a = np.stack([r, g, b], -1).astype(np.uint16)
    p = os.path.join(outdir, name + ".tiff")
    tifffile.imwrite(p, a)
    return p


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:\strehl-out\BUILD-CROP\live"
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(11)

    g = structured(rng)
    p_zero = write(outdir, "arm-ZERO", g.copy(), g, g.copy())

    flat = np.full((H, W), 12000.0, np.float32)
    p_nodata = write(outdir, "arm-NODATA", flat.copy(), flat, flat.copy())

    here = os.path.dirname(os.path.abspath(__file__))
    out = {}
    for tag, p in (("ZERO", p_zero), ("NODATA", p_nodata)):
        res = subprocess.run(
            [sys.executable, os.path.join(here, "carefit.py"), p],
            capture_output=True, text=True, cwd=here,
        )
        line = ""
        for ln in res.stdout.splitlines():
            if "arm-" in ln:
                line = ln.strip()
        out[tag] = line
        print(f"  arm {tag:7s} -> {line or '(no line emitted)'}")

    print()
    z, n = out.get("ZERO", ""), out.get("NODATA", "")
    # Compare the VERDICT, not the whole line: the lines always differ by
    # subject name, so comparing them would pass even when the verdicts are
    # identical -- the exact conflation this script exists to detect.
    zv = z.split("arm-ZERO", 1)[-1].strip()
    nv = n.split("arm-NODATA", 1)[-1].strip()
    zero_ok = "MEASURED ZERO" in zv
    nodata_ok = ("UNSCORED" in nv) or ("cannot measure" in nv)
    distinct = bool(zv) and bool(nv) and (zv != nv)
    print(f"  arm ZERO verdict   : {zv or '(none)'}")
    print(f"  arm NODATA verdict : {nv or '(none)'}")
    print(f"  arm ZERO says MEASURED ZERO      : {'OK' if zero_ok else 'FAIL'}")
    print(f"  arm NODATA says UNSCORED         : {'OK' if nodata_ok else 'FAIL'}")
    print(f"  the two VERDICTS differ          : {'OK' if distinct else 'FAIL'}")
    ok = zero_ok and nodata_ok and distinct
    print("\nCOMMISSION:", "GREEN -- the two states are distinguishable"
          if ok else "RED -- states still conflated")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

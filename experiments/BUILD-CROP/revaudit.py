"""revaudit.py -- conclusion-reversal audit of carefit.py's verdict channels.

carefit.py set a SHIPPED COEFFICIENT this turn. Its two verdict channels were
never commissioned:

  1. the SIGN and MAGNITUDE of `native` -- the number that goes into optics.rs
  2. the GATE (r2 >= R2_MIN -> scored, else "FAILS GATE, UNSCORED")

ORCH's three earned lessons, applied here rather than assumed:

  * AN INERT PLANT AND A DEAD INSTRUMENT GIVE THE IDENTICAL GREEN. So there is a
    LIVENESS arm (R = G exactly, must read 0.0) beside every signal arm. A tool
    that returned 0 unconditionally would pass the liveness arm and fail the
    signal arms; a tool that echoed its expectation would pass the signal arms
    and fail REVERSED. No single arm can catch both.
  * COMMISSIONING SENSITIVITY IS NOT COMMISSIONING SPECIFICITY. So there is a
    NOISE arm carrying no radial signal at all, which must NOT produce a
    confident coefficient.
  * COMMISSION DELETION AS WELL AS REVERSAL. So there is a DELETED arm where the
    radial organisation is destroyed by shuffling tile positions, which must fall
    to the gate rather than report a plausible number.

This writes synthetic masters and prints the ground truth. It deliberately does
NOT import carefit: the measurement must be made by running carefit.py's real
command line, so the audit exercises the shipped entry point end to end
(tifffile.imread -> field -> fit_mag_and_offset -> gate -> native -> median).

Usage:  python revaudit.py <outdir>
"""
from __future__ import annotations

import os
import sys

import numpy as np
import tifffile

from magdose import magnify

H, W = 3072, 4096
APPLIED_R = 704.5          # what carefit will subtract
SEED = 424242


def base_planes():
    """Textured green with gradient everywhere, so tiles gate in across the field."""
    rng = np.random.default_rng(SEED)
    g = rng.normal(0.0, 1.0, (H, W)).astype(np.float32)
    # a few octaves of smoothed noise -> broadband structure at tile scale
    from scipy.ndimage import gaussian_filter
    acc = np.zeros_like(g)
    for s, amp in ((1.0, 1.0), (3.0, 2.0), (9.0, 4.0), (27.0, 8.0)):
        acc += amp * gaussian_filter(g, s)
    acc -= acc.min()
    acc /= acc.max()
    return (acc * 20000.0 + 4000.0).astype(np.float32)


def write(outdir, name, r, g, b):
    img = np.stack([r, g, b], axis=2)
    img = np.clip(img, 0, 65535).astype(np.uint16)
    p = os.path.join(outdir, name + ".tiff")
    tifffile.imwrite(p, img)
    return p


def main() -> int:
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    g = base_planes()
    rng = np.random.default_rng(SEED + 1)
    # per-channel content difference at a realistic scale, so regression
    # dilution is PRESENT rather than deleted by making R a copy of G
    noise = lambda: rng.normal(0.0, 300.0, (H, W)).astype(np.float32)

    print(f"synthetic masters {W}x{H}, applied push carefit will remove: "
          f"{APPLIED_R:+.1f} ppm\n")
    rows = []

    # ---- ARM 1: NORMAL. residual +192 ppm outward (the real observation).
    r = magnify(g, +192.0) + noise()
    write(outdir, "arm1-normal", r, g, g + noise())
    rows.append(("arm1-normal", "+192 resid", 192.0 - APPLIED_R,
                 "native must be ~-512"))

    # ---- ARM 2: REVERSED. residual -192 ppm INWARD. A harness that echoes its
    # expectation, or that reports |magnitude| only, reports -512 here too.
    r = magnify(g, -192.0) + noise()
    write(outdir, "arm2-reversed", r, g, g + noise())
    rows.append(("arm2-reversed", "-192 resid", -192.0 - APPLIED_R,
                 "native must be ~-896, NOT -512"))

    # ---- ARM 3: LIVENESS. R = G exactly. Must read native = -704.5 (mag 0).
    write(outdir, "arm3-liveness", g.copy(), g, g.copy())
    rows.append(("arm3-liveness", "0 resid, no noise", -APPLIED_R,
                 "mag must be ~0 exactly"))

    # ---- ARM 4: NOISE ONLY. No radial signal, realistic content difference.
    write(outdir, "arm4-noiseonly", g + noise(), g, g + noise())
    rows.append(("arm4-noiseonly", "no radial signal", -APPLIED_R,
                 "must NOT report a confident coefficient"))

    # ---- ARM 5: DELETED. Strong radial signal, then the radial organisation is
    # destroyed by scrambling in blocks. Detection must FALL, not persist.
    r = magnify(g, +600.0) + noise()
    blk = 512
    scr = r.copy()
    idx = rng.permutation((H // blk) * (W // blk))
    cells = [(y, x) for y in range(0, H - blk + 1, blk)
             for x in range(0, W - blk + 1, blk)]
    for k, (y, x) in enumerate(cells):
        sy, sx = cells[idx[k] % len(cells)]
        scr[y:y + blk, x:x + blk] = r[sy:sy + blk, sx:sx + blk]
    write(outdir, "arm5-deleted", scr, g, g + noise())
    rows.append(("arm5-deleted", "+600 then scrambled", None,
                 "must FALL to the gate, not report ~-104"))

    print(f"{'arm':>16} {'planted':>22} {'expected native':>16}  requirement")
    print("-" * 96)
    for name, planted, exp, req in rows:
        e = f"{exp:+.1f} ppm" if exp is not None else "n/a"
        print(f"{name:>16} {planted:>22} {e:>16}  {req}")
    print(f"\nwrote 5 masters to {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Diagnose why the planted seam produces no response.

Two rounds of reasoning about the detector have both been wrong, so this stops arguing
and instruments it: a synthetic image whose answer is known by construction, then the
real master with the intermediate quantities printed. If the synthetic case fires, the
detector works and the fault is in how the plant meets the data; if it does not, the
fault is in line_ratio and the real-image readings carry no information at all.
"""
import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_seams2 import PLANT_PERIOD, line_ratio, load_luma, projections  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def synth(h=4000, w=8000, seed=1):
    rng = np.random.default_rng(seed)
    y = rng.normal(8000, 400, size=(h, w)).astype(np.float32)
    return y


def report(tag, y, amp):
    gx, gy = projections(y)
    r_before_x = line_ratio(gx, PLANT_PERIOD)
    r_before_y = line_ratio(gy, PLANT_PERIOD)
    z = y.copy()
    z[:, ::PLANT_PERIOD] += amp
    z[::PLANT_PERIOD, :] += amp
    pgx, pgy = projections(z)
    r_after_x = line_ratio(pgx, PLANT_PERIOD)
    r_after_y = line_ratio(pgy, PLANT_PERIOD)
    print(f"--- {tag} ---")
    print(f"  shape {y.shape} dtype {y.dtype}  luma mean {y.mean():.1f}")
    print(f"  median(gx) {np.median(gx):.3f}   amp planted {amp:.3f}")
    print(f"  gx[125:132] before {np.round(gx[125:132], 2)}")
    print(f"  gx[125:132] after  {np.round(pgx[125:132], 2)}")
    print(f"  delta at the planted column: {pgx[127] - gx[127]:+.3f} "
          f"/ {pgx[128] - gx[128]:+.3f}")
    print(f"  ratio@128  x {r_before_x:8.2f} -> {r_after_x:8.2f}")
    print(f"  ratio@128  y {r_before_y:8.2f} -> {r_after_y:8.2f}")
    print()


def main():
    y = synth()
    gx, _ = projections(y)
    report("SYNTHETIC noise, amp = 0.25 x median|dx|", y, float(np.median(gx)) * 0.25)
    report("SYNTHETIC noise, amp = 4 x median|dx|", y, float(np.median(gx)) * 4.0)

    p = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2\112MSDCF--SHIP-V2.tiff")
    im = Image.open(p)
    print(f"PIL reports mode={im.mode!r} size={im.size}")
    a = np.asarray(im)
    print(f"numpy dtype={a.dtype} shape={a.shape} "
          f"min={a.min()} max={a.max()}")
    del a
    ry, _ = load_luma(p)
    gx, _ = projections(ry)
    report("REAL 112MSDCF, amp = 0.25 x median|dx|", ry, float(np.median(gx)) * 0.25)
    report("REAL 112MSDCF, amp = 4 x median|dx|", ry, float(np.median(gx)) * 4.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())

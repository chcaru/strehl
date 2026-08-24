"""M109 B7-B9: an EXPOSURE-MATCHED LibRaw control for the magenta bar.

ORCH's `single_frame_control.py` develops with `no_auto_bright=True`, i.e. at
exposure gain 1.0, and compares it against a strehl render made at
`--exposure=-0.24` (gain 0.8467). Exposure is not a free variable for this
defect: green is pinned at the container ceiling and physically cannot follow
red and blue down when the gain is reduced, so lowering exposure OPENS the gap
that the magenta predicate measures. I measured 0.0349% -> 0.3378% from
exposure alone on one code path with one frame set -- 9.7x.

So this script re-develops the same middle frame LINEARLY through LibRaw, then
applies the exposure gain and strehl's own sRGB curve, so the control can be
produced at any gain and the comparison can hold exposure fixed.

It also removes a second, smaller confound: ORCH's control encodes with
`gamma=(2.222, 4.5)`, which is BT.709, not the sRGB curve strehl uses. Near
white the two are close, but the predicate is a DIFFERENCE of encoded channels,
so it is worth removing rather than assuming negligible.

D1 and D8 are IMPORTED from ORCH's `defect_audit.py` rather than reimplemented,
so the two batteries cannot silently diverge.

Usage:  python control_exposure.py <stackdir> <outdir> [gain ...]
"""

import sys
from pathlib import Path

import numpy as np
import rawpy
import tifffile

_ORCH = Path(__file__).resolve().parents[2] / "ORCH-drift-check"
if not (_ORCH / "defect_audit.py").is_file():
    raise SystemExit(f"cannot find ORCH's defect_audit.py at {_ORCH}")
sys.path.insert(0, str(_ORCH))
from defect_audit import d1_magenta, d8_partial_clip  # noqa: E402


def srgb_encode(x):
    """strehl's `color::srgb_encode`, not BT.709."""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    stack, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    gains = [float(g) for g in sys.argv[3:]] or [1.0]
    outdir.mkdir(parents=True, exist_ok=True)

    raws = sorted(stack.glob("*.ARW"))
    if not raws:
        print(f"no .ARW in {stack}")
        return 1
    mid = raws[len(raws) // 2]
    print(f"{len(raws)} frames; middle frame = {mid.name}")

    with rawpy.imread(str(mid)) as r:
        lin = (
            r.postprocess(
                output_bps=16,
                use_camera_wb=True,
                no_auto_bright=True,
                output_color=rawpy.ColorSpace.sRGB,
                gamma=(1, 1),
            ).astype(np.float32)
            / 65535.0
        )
    print(f"linear LibRaw develop: {lin.shape[1]}x{lin.shape[0]}, max {lin.max():.4f}")

    for g in gains:
        u = (srgb_encode(lin * g) * 65535.0 + 0.5).astype(np.uint16)
        p = outdir / f"control-eg{g:.4f}.tif"
        tifffile.imwrite(str(p), u)
        f = u.astype(np.float32) / 65535.0
        _, m1 = d1_magenta(f)
        _, m8 = d8_partial_clip(f)
        print(f"\ngain {g:.4f} -> {p}")
        print(f"   D1 {m1}")
        print(f"   D8 {m8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

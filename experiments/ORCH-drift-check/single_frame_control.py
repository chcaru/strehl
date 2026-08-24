"""Develop a single unstacked frame with LibRaw, as the negative control for
`defect_audit.py`.

The audit as first run had NO control, which is discipline 706's exact failure:
several of its checks are constructed from percentiles of the image itself and
therefore fire on ANY image by construction. Without a control there is no way
to tell "strehl produced this artefact" from "this is what the scene looks
like". D2 (chroma on edges) is the clearest case -- a single frame has its own
lateral chromatic aberration, so a ratio above 1.0 is expected and says nothing
about the merge until compared.

This develops the MIDDLE frame of a stack through LibRaw with settings chosen to
match strehl's output space as closely as the control can:
  - sRGB output, 16-bit
  - camera white balance (what strehl uses)
  - no auto-brightness (strehl's exposure is applied separately and auto-bright
    would introduce a difference that is not the thing under test)

The middle frame is chosen because it is the one most likely to be near focus
on the subject, so its edge and detail statistics are comparable to a merged
render rather than to a wholly defocused frame.

Usage:  python single_frame_control.py <stackdir> <out.tif>
"""
import sys
from pathlib import Path

import numpy as np
import rawpy
import tifffile


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    stack = Path(sys.argv[1])
    out = Path(sys.argv[2])
    raws = sorted(stack.glob("*.ARW"))
    if not raws:
        print(f"no .ARW found in {stack}")
        return 1
    mid = raws[len(raws) // 2]
    print(f"{len(raws)} frames; developing middle frame {mid.name}")
    with rawpy.imread(str(mid)) as r:
        rgb = r.postprocess(
            output_bps=16,
            use_camera_wb=True,
            no_auto_bright=True,
            output_color=rawpy.ColorSpace.sRGB,
            gamma=(2.222, 4.5),
        )
    tifffile.imwrite(str(out), rgb)
    y = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 65535.0
    print(f"wrote {out}  {rgb.shape[1]}x{rgb.shape[0]}  luma mean {y.mean():.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

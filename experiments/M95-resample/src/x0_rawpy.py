"""A = rawpy/LibRaw decode of DSC00150.ARW, matched to strehl's linear camera-native
output as closely as LibRaw allows: raw colour primaries, gamma 1.0, unity WB, no auto
brightness, 16-bit. This is the orchestrator's FULL term, and A -> B0 is the demosaic
algorithm difference they could not price from outside the codebase.

NOTE the rawpy use-after-free trap: `raw.raw_image_visible` is a VIEW into LibRaw-owned
memory and slicing it after the `with` block exits kills the interpreter with
0xC0000005 and no traceback. `postprocess()` returns an owned array, so it is safe.
"""

import os

import numpy as np
import rawpy

SRC = r"C:\dev\strehl-out\M95-resample\one-frame\DSC00150.ARW"
DST = r"C:\dev\strehl-out\M95-resample\rawpy-A.npy"

with rawpy.imread(SRC) as raw:
    rgb = raw.postprocess(
        output_color=rawpy.ColorSpace.raw,
        gamma=(1, 1),
        no_auto_bright=True,
        output_bps=16,
        user_wb=[1.0, 1.0, 1.0, 1.0],
        use_camera_wb=False,
        use_auto_wb=False,
        half_size=False,
    )
    rgb = np.ascontiguousarray(rgb)  # owned copy taken INSIDE the with block

print("rawpy decode:", rgb.shape, rgb.dtype, "mean", float(rgb.mean()))
np.save(DST, rgb)
print("wrote", DST)

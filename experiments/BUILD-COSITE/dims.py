"""Report shape/dtype/colour-space description of 16-bit TIFFs.

tifffile only; never PIL. Asserts uint16 before reporting any DN.
"""

import sys

import numpy as np
import tifffile

for p in sys.argv[1:]:
    with tifffile.TiffFile(p) as tf:
        page = tf.pages[0]
        desc = page.tags.get("ImageDescription")
        desc = desc.value if desc is not None else "<none>"
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{p}: dtype {arr.dtype}, expected uint16"
    print(p)
    print(f"  shape={arr.shape} dtype={arr.dtype} ptp={np.ptp(arr)}")
    print(f"  ImageDescription: {str(desc)[:240]}")

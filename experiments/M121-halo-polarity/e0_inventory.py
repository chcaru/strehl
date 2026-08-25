"""E0 -- inventory.  What is in each file, and does it match its log?

Run:  python experiments/M121-halo-polarity/e0_inventory.py
"""

from __future__ import annotations

import json
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from m121_io import ARMS, FRAMES, M93, OUT, arm_path, load_u16, luma, sha256  # noqa: E402

ORCH = __import__("pathlib").Path(r"C:\dev\strehl-out\ORCH-morning")
M96 = __import__("pathlib").Path(r"C:\dev\strehl-out\M96-election-margin")


def describe(path):
    with tifffile.TiffFile(str(path)) as tf:
        p = tf.pages[0]
        shape, dtype = p.shape, p.dtype
    a = load_u16(path)
    l = luma(a) if a.ndim == 3 else a.astype(np.float32)
    return {
        "path": str(path),
        "page_shape": list(shape),
        "page_dtype": str(dtype),
        "array_shape": list(a.shape),
        "array_dtype": str(a.dtype),
        "min": int(a.min()),
        "max": int(a.max()),
        "luma_mean": float(l.mean()),
        "sha256_16": sha256(path)[:16],
    }


def main():
    rows = []
    for name in ARMS:
        rows.append(describe(arm_path(name)) | {"what": ARMS[name]})
    for name in FRAMES:
        rows.append(describe(M93 / f"{name}.tif") | {"what": "single input frame, 1 frame, gate 0, alignment OFF"})
    rows.append(describe(ORCH / "bee-3-strehl.tif") | {"what": "shipped full render, demosaiced"})

    # M96 maps: check the dtype before believing anything about them.
    for f in ("elected-index", "margin-q8", "confusion-radius"):
        p = M96 / "bee-3-cpl" / f"{f}.tif"
        with tifffile.TiffFile(str(p)) as tf:
            pg = tf.pages[0]
            rows.append({
                "path": str(p),
                "page_shape": list(pg.shape),
                "page_dtype": str(pg.dtype),
                "what": "M96 map",
            })

    for r in rows:
        print(json.dumps(r))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e0-inventory.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()

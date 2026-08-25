"""Shared loading for M121.

Discipline 828 / SYNTHESIS fact 1615: `PIL.Image.open()` silently returns uint8
for a 16-bit RGB TIFF.  Every load in this milestone goes through `load_u16`,
which reads with `tifffile` and asserts the dtype on the line after the read.
Nothing in this milestone ever opens a `.tif` through PIL.

Discipline 830: an arm's name is not its semantics.  `ARMS` records what each
input file actually is, checked against the render log that sits beside it.
"""

from __future__ import annotations

import hashlib
import pathlib

import numpy as np
import tifffile

M93 = pathlib.Path(r"C:\dev\strehl-out\M93-out")
OUT = pathlib.Path(r"C:\dev\strehl-out\M121")

# What each arm IS, taken from the `strehl stack` log written beside it
# (discipline 830).  `binlin` = 16-bit RGB, 3516x2344, binned from one 2x2 CFA
# quad per pixel, so ONE OUTPUT PIXEL IS ONE PLANE PIXEL -- the same unit
# `focus.rs::WINDOW_RADIUS` is denominated in.
ARMS = {
    "armM4-gate4-binlin": (
        "SHIPPED GATE.  gate 4.00 == merge.rs:298 DEFAULT_GATE.  299 frames of "
        "bee-3-cpl, alignment OFF, mean n_eff 60.86, 35.02% singleton."
    ),
    "armM-gate0-binlin": (
        "NEGATIVE CONTROL.  gate 0.00, pure selector.  merge.rs:3299 and "
        "merge.rs:3341 label gate 0 a negative control and establish that it "
        "admits exactly the winner.  Same 299 frames, alignment OFF."
    ),
}
FRAMES = ["armF-f143", "armF-f158", "armF-f173", "armF-f193", "armF-f208"]


def load_u16(path: pathlib.Path) -> np.ndarray:
    """Read a TIFF and assert it came back 16-bit."""
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return a


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def luma(rgb: np.ndarray) -> np.ndarray:
    """Green-weighted luma in float32, in native raw DN.

    The merge accumulates in native raw DN with no white balance, so the panes
    are camera-native linear RGB.  A plain unweighted mean would let the two
    green samples of the quad be outvoted; this is the same 1/4,1/2,1/4 the
    crate's `green_luma` uses.
    """
    assert rgb.ndim == 3 and rgb.shape[2] == 3, rgb.shape
    f = rgb.astype(np.float32)
    return 0.25 * f[:, :, 0] + 0.5 * f[:, :, 1] + 0.25 * f[:, :, 2]


def arm_path(name: str) -> pathlib.Path:
    return M93 / f"{name}.tif"

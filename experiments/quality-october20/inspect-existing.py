"""Read existing full renders; write bounded photographic review artifacts.

This does not render, alter source files, or rank photographs by a statistic.
The receipt records exact historical arguments, byte hashes, and display steps.
"""

from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parents[2]
OUT = HERE / "existing-review"
RUNS = {
    "slide-default": "strehl-1792309957142-43564-3",
    "slide-clamped": "strehl-1792310382762-43564-5",
    "slide-strong": "strehl-1792310732553-43564-7",
    "garnet-default": "strehl-1792368598430-22840-1",
    "garnet-auto-exposure": "strehl-1792368986586-22840-2",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    receipt = {
        "method": "Complete RGB16 TIFF -> rounded RGB8/257; overview BOX "
        "resampling, native crops unresampled; embedded ICC preserved. "
        "Historical files only, not new controlled A/B renders.",
        "renders": [],
    }
    for label, run in RUNS.items():
        folder = ORIGINAL / run
        path = folder / "result.tiff"
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            pixels = page.asarray()
            assert pixels.dtype == np.uint16 and pixels.ndim == 3
            assert pixels.shape[2] == 3
            icc = page.tags.get(34675)
            icc = icc.value if icc else None
            software = page.tags.get(305)
            software = software.value if software else None
        rgb = ((pixels.astype(np.uint32) + 128) // 257).astype(np.uint8)
        image = Image.fromarray(rgb)
        image.thumbnail((1500, 1100), Image.Resampling.BOX)
        preview = OUT / f"{label}-whole.png"
        image.save(preview, icc_profile=icc)
        with (folder / "render.log").open(encoding="utf-8", errors="replace") as f:
            header = [next(f).rstrip("\n") for _ in range(8)]
        receipt["renders"].append({
            "label": label, "path": str(path), "bytes": path.stat().st_size,
            "sha256": digest(path), "shape": pixels.shape,
            "software": software, "log_header": header,
            "overview": str(preview), "overview_sha256": digest(preview),
        })
        print(label, pixels.shape)
        del pixels, rgb, image
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()

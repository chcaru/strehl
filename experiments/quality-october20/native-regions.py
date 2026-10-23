"""Frozen native output regions and sequential camera source witnesses."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import rawpy
import tifffile

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parents[2]
OUT = HERE / "native-review"
REGIONS = {
    # Frozen from the full default image before inspecting comparison crops.
    "qr-edge": [4650, 400, 640, 640],
    "centre-text": [3300, 1800, 640, 640],
    "grey-ramp": [2200, 650, 640, 640],
}
RUNS = {
    "default": "strehl-1792309957142-43564-3",
    "clamped": "strehl-1792310382762-43564-5",
    "strong": "strehl-1792310732553-43564-7",
}


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as s:
        for b in iter(lambda: s.read(4 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Read-only 197-frame calibration-slide bracket")
    source = parser.parse_args().source
    OUT.mkdir(exist_ok=True)
    result = {"regions": REGIONS, "crops": [], "sources": [],
              "scope": "Historical output comparison; original-source witness "
              "grayscale is unwarped, unregistered, fixed black/container and "
              "sRGB transfer. Source overview cannot measure edge widths."}
    for label, run in RUNS.items():
        with tifffile.TiffFile(ORIGINAL / run / "result.tiff") as t:
            p = t.pages[0]
            a = p.asarray()
            icc = p.tags.get(34675)
            icc = icc.value if icc else None
        for name, (x, y, w, h) in REGIONS.items():
            rgb = ((a[y:y+h, x:x+w].astype(np.uint32)+128)//257).astype(np.uint8)
            path = OUT / f"{label}-{name}.png"
            Image.fromarray(rgb).save(path, icc_profile=icc)
            result["crops"].append({"label": label, "region": name, "file": str(path),
                                    "sha256": digest(path)})
        del a
    files = sorted(source.glob("*.ARW"))
    assert len(files) == 197
    for index in [49, 98, 147]:
        path = files[index]
        before = digest(path)
        with rawpy.imread(str(path)) as raw:
            active = raw.raw_image_visible.copy()
            colors = raw.raw_colors_visible.copy()
            metadata = {"black": raw.black_level_per_channel,
                        "white": raw.white_level, "shape": active.shape}
        # Own both buffers before closing RawPy. No full-buffer synthetic padding.
        green = .5 * (active[0::2, 1::2].astype(np.float32)
                      + active[1::2, 0::2].astype(np.float32))
        assert set(np.unique(colors[0::2, 1::2])) == {1}
        assert set(np.unique(colors[1::2, 0::2])) == {3}
        lin = np.clip((green-512)/15871, 0, 1)
        enc = np.where(lin <= .0031308, 12.92*lin, 1.055*np.power(lin, 1/2.4)-.055)
        pic = Image.fromarray(np.rint(enc*255).astype(np.uint8))
        pic.thumbnail((1500, 1100), Image.Resampling.BOX)
        preview = OUT / f"source-{index:03}-whole.png"
        pic.save(preview)
        assert digest(path) == before
        result["sources"].append({"path": str(path), "index_zero": index,
            "sha256": before, "active_sha256": hashlib.sha256(active.tobytes()).hexdigest(),
            "metadata": metadata, "nominal_white_count": int((active >=15360).sum()),
            "container_count": int((active >=16383).sum()), "maximum": int(active.max()),
            "preview": str(preview)})
        print("source", index, metadata, "max", active.max())
        del active, colors, green, lin, enc, pic
    (OUT/"receipt.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()

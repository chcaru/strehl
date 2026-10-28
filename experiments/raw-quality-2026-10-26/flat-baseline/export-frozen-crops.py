"""Export only the pre-frozen native crops from the saved complete flat baseline."""
from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "outputs/raw-quality-2026-10-26/flat-1s-baseline"
FROZEN = HERE / "frozen-witnesses.json"
OUT = HERE / "baseline-native"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ref(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 << 20):
            digest.update(block)
    stat = path.stat()
    return {"path": str(path), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "sha256": digest.hexdigest()}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    started = time.monotonic()
    require(not OUT.exists(), "fresh crop directory required")
    config = read(FROZEN)
    require(config["candidate_seen"] is False and config["complete_baseline_viewed"] is True,
            "baseline-first nomination required")
    receipt = read(SOURCE / "completion.json")
    master_path = SOURCE / "stack-master.tiff"
    paths = [FROZEN, SOURCE / "completion.json", SOURCE / "input-order.json",
             SOURCE / "alignment.txt", master_path, SOURCE / "linear-master.tiff", Path(__file__).resolve()]
    before = [ref(p) for p in paths]
    require(receipt["status"] == "RENDERED_AWAITING_INDEPENDENT_VISUAL_REVIEW"
            and receipt["frames"] == 60 and receipt["original_bytes_and_metadata_unchanged"] is True
            and receipt["native_dimensions"] == config["dimensions"]
            and receipt["crop_quad_xywh"] == config["crop_quad_xywh"], "baseline receipt differs")
    require(before[4]["sha256"] == receipt["master"]["sha256"] == config["master_sha256"], "master changed")
    require(before[3]["sha256"] == receipt["warp_map"]["sha256"] == config["map_sha256"], "map changed")
    require(before[2]["sha256"] == config["input_order_sha256"]
            and receipt["executable"]["sha256"] == config["executable_sha256"], "order/executable differs")
    order = read(SOURCE / "input-order.json")
    require(len(order) == 60 and [r["index"] for r in order] == list(range(60))
            and [Path(r["path"]).name for r in order] == [f"DSC{i:05}.ARW" for i in range(16, 76)],
            "complete source order differs")
    lines = (SOURCE / "alignment.txt").read_text().splitlines()
    rows = [line.split() for line in lines if line and line.split()[0].isdigit()]
    require("reference 30" in lines and "resampler catmull-rom" in lines
            and len(rows) == 60 and all(row[1] == "placed" for row in rows), "map placement differs")
    width, height = config["dimensions"]
    with tifffile.TiffFile(master_path) as source:
        require(len(source.pages) == 1 and source.pages[0].shape == (height, width, 3)
                and source.pages[0].dtype == np.uint16, "complete RGB16 master required")
        icc = bytes(source.pages[0].tags[34675].value)
    # Read only the linear master's metadata, not its pixel array.
    with tifffile.TiffFile(SOURCE / "linear-master.tiff") as source:
        require(len(source.pages) == 1 and source.pages[0].shape == (height, width, 3)
                and source.pages[0].dtype == np.float32, "complete single-page RGB32 linear master required")
        description = source.pages[0].description
    baseline_lines = [line[len("DisplayBaseline: "):] for line in description.splitlines()
                      if line.startswith("DisplayBaseline: ")]
    require(len(baseline_lines) == 1, "exact baseline tone metadata required")
    display_baseline = json.loads(baseline_lines[0])
    image = tifffile.memmap(master_path, mode="r")
    require(len(config["witnesses"]) == 8, "eight frozen regions required")
    OUT.mkdir()
    records = []
    for witness in config["witnesses"]:
        name = witness["name"]
        require(name.replace("-", "").isalnum(), "plain crop name required")
        x, y, w, h = witness["native_xywh"]
        require(0 < w <= 384 and 0 < h <= 384 and 0 <= x <= width-w and 0 <= y <= height-h,
                "invalid native rectangle")
        crop = image[y:y+h, x:x+w].copy()
        png8 = ((crop.astype(np.uint32)+128)//257).astype(np.uint8)
        png, tiff = OUT / f"{name}.png", OUT / f"{name}.tiff"
        Image.fromarray(png8).save(png, icc_profile=icc)
        tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None,
                         extratags=[(34675, "B", len(icc), icc, False)])
        with Image.open(png) as check:
            require(check.size == (w, h) and check.info.get("icc_profile") == icc
                    and np.array_equal(np.asarray(check), png8), "PNG roundtrip differs")
        with tifffile.TiffFile(tiff) as check:
            require(bytes(check.pages[0].tags[34675].value) == icc
                    and np.array_equal(check.asarray(), image[y:y+h, x:x+w]), "lossless crop differs")
        records.append({**witness, "resized": False, "png": ref(png), "rgb16": ref(tiff)})
    del image
    require([ref(p) for p in paths] == before, "bound input changed during crop export")
    result = {"status": "EIGHT_EXACT_NATIVE_BASELINE_CROPS_READY_NO_VERDICT", "quality_claim": False,
              "command": [sys.executable, *sys.orig_argv[1:]], "inputs": before,
              "input_files_unchanged": True, "original_raw_reads": 0, "display": config["display"],
              "linear_master": {**before[5], "pages": 1, "shape": [height, width, 3], "dtype": "float32", "pixel_analysis": False},
              "exact_product_display_baseline": display_baseline,
              "icc_sha256": hashlib.sha256(icc).hexdigest(), "witnesses": records,
              "operational_seconds": time.monotonic()-started}
    with (HERE / "crop-export-receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2)+"\n")
    print(f"Eight exact native crops ready, original RGB16 display retained; {result['operational_seconds']:.3f}s.")


if __name__ == "__main__":
    main()

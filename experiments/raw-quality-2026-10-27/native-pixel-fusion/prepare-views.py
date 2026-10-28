"""Complete fixed-tone RGB16 photographs and exact, previously frozen flat witnesses."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / "experiments/raw-quality-2026-10-26/flat-baseline/frozen-witnesses.json"
FROZEN_SHA = "fde6bb02b6ca12793176b3e30ef8d60bba5aed3ed86dd1d4e3ea080c736a297e"


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 << 20):
            h.update(block)
    st = path.stat()
    return dict(path=str(path), sha256=h.hexdigest(), bytes=st.st_size, mtime_ns=st.st_mtime_ns)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(ROOT / "outputs") and not out.exists()
    frozen = json.loads(FROZEN.read_text())
    assert ref(FROZEN)["sha256"] == FROZEN_SHA
    assert frozen["dimensions"] == [6932, 4620] and len(frozen["witnesses"]) == 8
    paths = [args.baseline.resolve(), args.candidate.resolve(), args.receipt.resolve(), FROZEN, Path(__file__).resolve()]
    before = [ref(path) for path in paths]
    receipt = json.loads(paths[2].read_text())
    assert receipt["status"] == "COMPLETE60_OBSERVATION_READY" and receipt["source_count"] == 60
    assert receipt["baseline_pixel_golden_exact"] and receipt["original_bytes_and_metadata_unchanged"]
    assert receipt["native_dimensions"] == frozen["dimensions"] and receipt["crop_quad_xywh"] == frozen["crop_quad_xywh"]
    for index, name in enumerate(("baseline", "candidate")):
        bound = receipt[name]["rgb16"]
        assert Path(bound["path"]).samefile(paths[index])
        assert bound["sha256"] == before[index]["sha256"] and bound["bytes"] == before[index]["bytes"]
    out.mkdir(parents=True)
    rows = []
    common_icc = None
    for name, path in zip(("baseline", "candidate"), paths[:2]):
        dest = out / name
        dest.mkdir()
        with tifffile.TiffFile(path) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.uint16 and tif.pages[0].shape == (4620, 6932, 3)
            icc = bytes(tif.pages[0].tags[34675].value)
            rgb = tif.asarray()
        assert icc
        if common_icc is None:
            common_icc = icc
        else:
            assert icc == common_icc, "arms must have identical ICC"
        # Exactly the already fixed writer output: no display fit or spatial filter.
        rgb8 = ((rgb.astype(np.uint32) + 128) // 257).astype(np.uint8)
        full = dest / "complete-stack.jpg"
        whole = Image.fromarray(rgb8)
        whole.save(full, quality=98, subsampling=0, icc_profile=icc)
        with Image.open(full) as check:
            assert check.size == (6932, 4620) and check.info.get("icc_profile") == icc
        whole.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        whole.save(dest / "overview.jpg", quality=98, icc_profile=icc)
        crops = []
        for witness in frozen["witnesses"]:
            x, y, w, h = witness["native_xywh"]
            assert w == h == 384 and 0 <= x <= 6932-w and 0 <= y <= 4620-h
            crop = rgb[y:y+h, x:x+w].copy()
            png8 = rgb8[y:y+h, x:x+w].copy()
            png = dest / (witness["name"] + ".png")
            tiff = dest / (witness["name"] + ".tiff")
            Image.fromarray(png8).save(png, icc_profile=icc)
            tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None,
                             extratags=[(34675, "B", len(icc), icc, False)])
            with tifffile.TiffFile(tiff) as check:
                assert np.array_equal(check.asarray(), crop) and bytes(check.pages[0].tags[34675].value) == icc
            with Image.open(png) as check:
                assert np.array_equal(np.asarray(check), png8) and check.info.get("icc_profile") == icc
            crops.append(dict(name=witness["name"], native_xywh=[x,y,w,h], png=ref(png), tiff=ref(tiff), exact=True))
        rows.append(dict(arm=name, master=ref(path), full_jpeg=ref(full), overview=ref(dest / "overview.jpg"),
                         rgb16_pixel_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(), crops=crops))
        del rgb, rgb8, whole
    assert [ref(path) for path in paths] == before, "input changed during display export"
    result = dict(command=sys.argv, status="COMPLETE_IMAGES_READY_FOR_REVIEW", seconds=time.monotonic()-started,
                  inputs=before, arms=rows, inputs_unchanged=True,
                  display="Existing fixed-tone RGB16, conversion (value+128)//257, identical ICC; no per-arm retone or sharpening.",
                  scope="Full JPEGs retain entire output; overview resampling is orientation only. Crops are exact unresampled384 subarrays.")
    with (out / "display-receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(status=result["status"], seconds=result["seconds"], receipt=ref(out / "display-receipt.json"))))


if __name__ == "__main__":
    main()

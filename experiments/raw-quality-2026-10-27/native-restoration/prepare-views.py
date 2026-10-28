"""Complete unchanged-tone native-restoration displays and all frozen witnesses."""
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
DATASETS = {
    "weevil": dict(dimensions=[6896,4596], crop=[34,23,3448,2298], origin=[68,46], count=10,
        manifest="experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json",
        manifest_sha="826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888", rect_key="rect_xywh"),
    "flat": dict(dimensions=[6932,4620], crop=[25,17,3466,2310], origin=[50,34], count=8,
        manifest="experiments/raw-quality-2026-10-26/flat-baseline/frozen-witnesses.json",
        manifest_sha="fde6bb02b6ca12793176b3e30ef8d60bba5aed3ed86dd1d4e3ea080c736a297e", rect_key="native_xywh"),
}


def ref(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 << 20):
            digest.update(block)
    st = path.stat()
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=st.st_size, mtime_ns=st.st_mtime_ns)


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=tuple(DATASETS), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    assert source.is_dir() and source.is_relative_to(ROOT / "outputs")
    assert out.is_relative_to(ROOT / "outputs") and not out.exists() and not out.is_relative_to(source)
    config = DATASETS[args.dataset]
    width, height = config["dimensions"]
    manifest_path = ROOT / config["manifest"]
    assert ref(manifest_path)["sha256"] == config["manifest_sha"]
    frozen = json.loads(manifest_path.read_text())
    assert len(frozen["witnesses"]) == config["count"]
    receipt_path = source / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "COMPLETE_NATIVE_RESTORATION_DIAGNOSTIC"
    assert receipt["dataset"] == args.dataset
    assert receipt["native_dimensions"] == config["dimensions"] and receipt["crop_quad_xywh"] == config["crop"]
    assert receipt["admission"] is False and receipt["quality_claim"] is False
    assert receipt["RAW_reads"] == 0 and receipt["original_RAW_read_or_written"] is False
    for key in ("noop_rgb16_pixel_exact", "noop_linear_pixel_exact", "pair_material_metadata_exact",
                "baseline_pixel_golden_exact", "baseline_material_metadata_golden_exact", "sensor_off_bit_exact",
                "retained_input_bytes_and_metadata_unchanged"):
        assert receipt[key] is True, key
    paths = [Path(__file__).resolve(), manifest_path, receipt_path]
    files = {}
    for arm in ("baseline", "candidate"):
        assert receipt[arm]["entire_output"] is True
        files[arm] = {}
        for kind in ("rgb16", "linear", "sensor"):
            bound = receipt[arm][kind]
            path = Path(bound["path"]).resolve()
            assert path.parent == source
            actual = ref(path)
            assert actual["sha256"] == bound["sha256"] and actual["bytes"] == bound["bytes"]
            files[arm][kind] = path
            paths.append(path)
        sidecar = source / (arm + "-sensor.json")
        sensor = json.loads(sidecar.read_text())
        assert [sensor["width"], sensor["height"]] == config["dimensions"]
        assert sensor["active_native_origin"] == config["origin"]
        assert files[arm]["sensor"].stat().st_size == width * height * 4
        assert sensor["payload"]["sha256"] == receipt[arm]["sensor"]["sha256"]
        paths.append(sidecar)
    before = [ref(path) for path in paths]
    out.mkdir()
    rows = []
    common_icc = None
    for arm in ("baseline", "candidate"):
        dest = out / arm
        dest.mkdir()
        with tifffile.TiffFile(files[arm]["rgb16"]) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.uint16
            assert tif.pages[0].shape == (height, width, 3)
            icc = bytes(tif.pages[0].tags[34675].value)
            rgb = tif.asarray()
        assert icc and rgb.flags.c_contiguous
        if common_icc is None:
            common_icc = icc
        else:
            assert common_icc == icc, "common held ICC required"
        with tifffile.TiffFile(files[arm]["linear"]) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.float32
            assert tif.pages[0].shape == (height, width, 3)
        pixel_sha = hashlib.sha256(memoryview(rgb).cast("B")).hexdigest()
        assert pixel_sha == receipt[arm]["rgb16_pixels_sha256"]
        rgb8 = ((rgb.astype(np.uint32) + 128) // 257).astype(np.uint8)
        full = dest / "complete-stack.jpg"
        whole = Image.fromarray(rgb8)
        whole.save(full, quality=98, subsampling=0, icc_profile=icc)
        with Image.open(full) as check:
            assert check.size == (width, height) and check.info.get("icc_profile") == icc
        whole.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        whole.save(dest / "overview.jpg", quality=98, icc_profile=icc)
        crops = []
        for witness in frozen["witnesses"]:
            x, y, w, h = witness[config["rect_key"]]
            assert w == h == 384 and 0 <= x <= width-w and 0 <= y <= height-h
            crop, png8 = rgb[y:y+h, x:x+w].copy(), rgb8[y:y+h, x:x+w].copy()
            png, tiff = dest / (witness["name"] + ".png"), dest / (witness["name"] + ".tiff")
            Image.fromarray(png8).save(png, icc_profile=icc)
            tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None,
                             extratags=[(34675, "B", len(icc), icc, False)])
            with tifffile.TiffFile(tiff) as check:
                assert np.array_equal(check.asarray(), crop) and bytes(check.pages[0].tags[34675].value) == icc
            with Image.open(png) as check:
                assert np.array_equal(np.asarray(check), png8) and check.info.get("icc_profile") == icc
            crops.append(dict(name=witness["name"], native_xywh=[x,y,w,h], exact=True, png=ref(png), tiff=ref(tiff)))
        rows.append(dict(arm=arm, role="exact no-op replay" if arm == "baseline" else "bounded sensor-space restoration diagnostic",
                         master=ref(files[arm]["rgb16"]), linear_master=ref(files[arm]["linear"]), sensor_master=ref(files[arm]["sensor"]),
                         full_jpeg=ref(full), overview=ref(dest / "overview.jpg"), rgb16_pixel_sha256=pixel_sha, crops=crops))
        del rgb, rgb8, whole
    assert [ref(path) for path in paths] == before, "retained output changed during view export"
    result = dict(status="COMPLETE_RESTORATION_DISPLAYS_READY_NO_VERDICT", dataset=args.dataset, command=sys.argv,
                  seconds=time.monotonic()-started, inputs=before, inputs_unchanged=True, arms=rows, observation_receipt=receipt,
                  admission=False, photographic_improvement_claimed=False,
                  display="Held writer RGB16 only; (value+128)//257; identical original ICC; no retone or sharpening.",
                  scope="Full JPEG and bound master retain complete image; overview is orientation only; every frozen384 crop is unresampled.")
    save(out / "display-receipt.json", result)
    print(json.dumps(dict(status=result["status"], dataset=args.dataset, seconds=result["seconds"], receipt=ref(out / "display-receipt.json"))))


if __name__ == "__main__":
    main()

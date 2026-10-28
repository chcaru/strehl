"""Read-only cached-output locator; freeze origins before exact native exports."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import time

import cv2
import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
HELPER = ROOT / "experiments/raw-quality-2026-10-26/comparator/photo-review/export-corresponding.py"
HELPER_SHA = "4a7df974014431fcefff4803f1ad8dcc394644856d8927dcab7015c26fba7244"
ARMS = {
    "native-ca-off": ROOT / "outputs/raw-quality-2026-10-26/weevil-107-ca-off",
    "b8": ROOT / "outputs/raw-quality-2026-10-26/weevil-107-comparator/b",
    "b4": ROOT / "outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2",
}
MASTER_SHA = {
    "native-ca-off": "5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655",
    "b8": "56e6f5be1c98f7670b81dfe458d734d0bd782e0bc2a801bb7cd1dcf30a89165a",
    "b4": "d24e944825fe5e8405dbf26a7339e7d69af4f70dea6607db1af81ea809a274ff",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path):
    s = path.stat()
    return {"path": str(path), "sha256": sha(path), "bytes": s.st_size, "mtime_ns": s.st_mtime_ns}


def save(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def read(path):
    with tifffile.TiffFile(path) as t:
        assert len(t.pages) == 1 and t.pages[0].dtype == np.uint16
        icc = bytes(t.pages[0].tags[34675].value)
    a = tifffile.memmap(path, mode="r")
    assert a.ndim == 3 and a.shape[2] == 3
    return a, icc


def rgb8(a):
    # Row blocks avoid a full RGB32 scratch volume; no spatial filtering.
    b = np.empty(a.shape, dtype=np.uint8)
    for y in range(0, a.shape[0], 128):
        b[y:y+128] = ((a[y:y+128].astype(np.uint32) + 128) // 257).astype(np.uint8)
    return b


def main():
    start = time.monotonic()
    assert sys.argv[1:] == ["--whole-images-reviewed"], "Three complete views precede any crop"
    assert not (HERE / "mapped-witnesses.json").exists()
    assert sha(HELPER) == HELPER_SHA
    spec = importlib.util.spec_from_file_location("retained_weevil_locator", HELPER)
    locator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locator)
    cv2.setNumThreads(2)
    frozen = json.loads(FROZEN.read_text())
    assert len(frozen["witnesses"]) == 10
    watched = [Path(__file__), FROZEN, HELPER]
    completions = {}
    for arm, directory in ARMS.items():
        cp = directory / "completion.json"
        c = json.loads(cp.read_text())
        assert c["master"]["sha256"] == MASTER_SHA[arm]
        master = directory / "stack-master.tiff"
        assert sha(master) == MASTER_SHA[arm]
        if arm == "native-ca-off":
            assert c["frames"] == 299 and c["original_bytes_and_metadata_unchanged"]
            assert c["crop_quad_xywh"] == frozen["source_crop_quad_xywh"]
            assert c["warp_map"]["sha256"] == frozen["map"]["sha256"]
        else:
            assert c["inputs_unchanged"] and c["shape"] == [4676, 7020, 3]
        if arm == "b4":
            assert c["status"] == "COMPLETE299_B4_READY_FOR_INDEPENDENT_REVIEW"
            assert (c["source_count"], c["method"], c["radius"], c["smoothing"]) == (299, "B", 4, 4)
        completions[arm] = c
        watched.extend([cp, master, directory / "stack-full.jpg"])
    before = [ref(p) for p in watched]
    native, icc = read(ARMS["native-ca-off"] / "stack-master.tiff")
    assert [native.shape[1], native.shape[0]] == frozen["complete_rgb16_dimensions"]
    assert hashlib.sha256(icc).hexdigest() == frozen["icc_sha256"]
    a8 = rgb8(native)
    mappings = {}
    for arm, directory in ARMS.items():
        pixels, other_icc = read(directory / "stack-master.tiff")
        assert other_icc == icc
        if arm == "native-ca-off":
            matrix = np.array([[1., 0., 0.], [0., 1., 0.]])
            ap = bp = np.empty((0, 2))
            details = {"purpose": "Held native gauge, exact frozen coordinates; no registration"}
        else:
            b8 = rgb8(pixels)
            matrix, ap, bp, details = locator.locate(a8, b8)
            del b8
        witnesses = []
        for w in frozen["witnesses"]:
            x, y, width, height = w["rect_xywh"]
            assert width == height == 384
            center = np.array([x+width/2, y+height/2])
            target = matrix[:, :2] @ center + matrix[:, 2]
            near = np.linalg.norm(ap-center, axis=1) < 300
            delta = np.zeros(2)
            if near.sum() >= 3:
                delta = np.median(bp[near] - (ap[near] @ matrix[:, :2].T + matrix[:, 2]), axis=0)
                assert np.linalg.norm(delta) < 10
                target += delta
            bx, by = np.rint(target-[width/2, height/2]).astype(int)
            assert bx >= 0 and by >= 0 and bx+width <= pixels.shape[1] and by+height <= pixels.shape[0]
            witnesses.append({"name": w["name"], "native_ca_off_xywh": w["rect_xywh"],
                              "arm_xywh": [int(bx), int(by), width, height],
                              "nearby_feature_inliers": int(near.sum()), "local_native_translation": delta.tolist()})
        mappings[arm] = {"master": ref(directory / "stack-master.tiff"),
                         "complete_jpeg": ref(directory / "stack-full.jpg"),
                         "dimensions": [pixels.shape[1], pixels.shape[0]],
                         "mapping": details, "witnesses": witnesses}
        print(arm, json.dumps(details), flush=True)
        del pixels
    del native, a8
    manifest = {"status": "MAPPINGS_FROZEN_AFTER_THREE_COMPLETE_VIEWS_BEFORE_CROP_EXPORT",
                "inputs": before, "arms": mappings, "whole_view_order": ["native-ca-off", "b8", "b4"],
                "native_condition": "CA-off native reconstruction, original automatic tone; same held reference149 crop active68,46 as frozen coordinates",
                "display": "Original RGB16/ICC, PNG(value+128)//257; no common-display gain variant or retone",
                "comparison_limit": "B8/B4 use identical predeveloped299 TIFFs and tone; native is developed after RAW fusion. Pre/postdevelopment and original native tone remain workflow differences.",
                "locator_limit": "SIFT similarity/local translation locates crop centers only. Native384 pixels retained; physical footprints vary by fitted scale and local depth. No placement-accuracy, equal-footprint resolution or image-quality metric."}
    save(HERE / "mapped-witnesses.json", manifest)
    frozen_mapping = ref(HERE / "mapped-witnesses.json")
    outputs = []
    for arm, directory in ARMS.items():
        pixels, arm_icc = read(directory / "stack-master.tiff")
        dest = HERE / arm
        dest.mkdir(exist_ok=False)
        for w in mappings[arm]["witnesses"]:
            x, y, width, height = w["arm_xywh"]
            patch = pixels[y:y+height, x:x+width]
            png = dest / f"{w['name']}.png"
            tiff = dest / f"{w['name']}.tiff"
            expected8 = rgb8(patch)
            Image.fromarray(expected8).save(png, icc_profile=arm_icc)
            tifffile.imwrite(tiff, patch, photometric="rgb", metadata=None,
                             extratags=[(34675, "B", len(arm_icc), arm_icc, False)])
            with Image.open(png) as check:
                assert np.array_equal(np.asarray(check), expected8) and check.info["icc_profile"] == arm_icc
            with tifffile.TiffFile(tiff) as check:
                assert np.array_equal(check.asarray(), patch) and bytes(check.pages[0].tags[34675].value) == arm_icc
            outputs.append({"arm": arm, "name": w["name"], "xywh": w["arm_xywh"],
                            "png": ref(png), "tiff": ref(tiff), "pixels_exact": True, "icc_exact": True})
        del pixels
    assert [ref(p) for p in watched] == before
    assert ref(HERE / "mapped-witnesses.json") == frozen_mapping
    save(HERE / "crop-export-receipt.json", {"status": "ALL30_NATIVE_CROPS_READY_NO_VERDICT",
         "command": [sys.executable, "-B", "-X", "faulthandler", str(Path(__file__)), *sys.argv[1:]],
         "inputs": before, "mapped_manifest": frozen_mapping, "inputs_unchanged": True,
         "outputs": outputs, "seconds": time.monotonic()-start, "raw_reads": 0,
         "resized_crops": False, "icc_sha256": hashlib.sha256(icc).hexdigest()})
    print(json.dumps({"status": "ALL30_NATIVE_CROPS_READY_NO_VERDICT", "seconds": time.monotonic()-start}))


if __name__ == "__main__":
    main()

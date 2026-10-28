"""Root-run exporter of three complete, identically displayed photographs.

Source preparation only until root releases a completed photographic run.
Reads generated outputs and receipts, never the original capture corpus.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image, __version__ as PILLOW_VERSION
import tifffile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAMES = ("baseline", "matched-mean", "phase-energy")
WIDTH, HEIGHT = 6896, 4596
MAP_SHA = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
ORDER_SHA = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f"
BASE_CFA_SHA = "1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0"
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"
WITNESSES = (
    ("background-black", 3800, 500), ("dark-elytron", 2750, 2120),
    ("turquoise-scales", 2120, 1340), ("elytron-seam", 2950, 1960),
    ("bright-wing-rim", 4050, 1810), ("thorax-texture", 4520, 2560),
    ("upper-leg-hairs", 1820, 640), ("blue-joint", 2680, 850),
    ("upper-occlusion", 3850, 1300), ("eye-and-antenna", 5350, 2920),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 << 20):
            digest.update(block)
    return digest.hexdigest()


def reference(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2) + "\n")


def check_record(record, input_dir):
    path = Path(record["path"]).resolve(strict=True)
    require(path.is_file() and path.is_relative_to(input_dir), "arm file outside input directory")
    require(path.stat().st_size == record["bytes"] and sha(path) == record["sha256"],
            f"bound file differs: {path}")
    return path


def inspect_rgb(path, dtype, require_icc):
    with tifffile.TiffFile(path) as image:
        require(len(image.pages) == 1, f"not one complete image: {path}")
        page = image.pages[0]
        require(page.shape == (HEIGHT, WIDTH, 3) and page.dtype == np.dtype(dtype),
                f"wrong image dimensions/type: {path}")
        require(int(page.photometric) == 2, f"not RGB: {path}")
        if require_icc:
            require(34675 in page.tags, f"ICC absent: {path}")
            icc = bytes(page.tags[34675].value)
            require(hashlib.sha256(icc).hexdigest() == ICC_SHA, f"ICC differs: {path}")
        else:
            icc = None
    # The native writer emits uncompressed TIFFs. Refuse a changed format here.
    data = tifffile.memmap(path, mode="r")
    digest = hashlib.sha256()
    le_dtype = np.dtype(dtype).newbyteorder("<")
    for y in range(0, HEIGHT, 128):
        block = data[y:y + 128]
        require(np.isfinite(block).all(), f"nonfinite RGB: {path}")
        digest.update(np.ascontiguousarray(block, dtype=le_dtype).tobytes())
    del data
    return digest.hexdigest(), icc


def common16(linear):
    value = np.clip(linear * np.float32(3.434), np.float32(0), np.float32(1))
    encoded = np.where(value <= np.float32(.0031308), value * np.float32(12.92),
                       np.float32(1.055) * np.maximum(value, np.float32(0)) **
                       np.float32(1 / 2.4) - np.float32(.055))
    return np.rint(encoded * np.float32(65535)).astype(np.uint16)


def rgb8(values):
    return ((values.astype(np.uint32) + 128) // 257).astype(np.uint8)


def export_arm(name, paths, output_dir, icc):
    target = output_dir / name
    target.mkdir()
    linear = tifffile.memmap(paths["linear_rgb32"], mode="r")
    master_path = target / "common-display-master.tiff"
    tags = [(34675, "B", len(icc), icc, False)]
    master = tifffile.memmap(master_path, shape=(HEIGHT, WIDTH, 3), dtype=np.uint16,
                            photometric="rgb", metadata=None,
                            software="Strehl green-phase review: fixed gain3.434 and sRGB transfer",
                            extratags=tags)
    preview = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(0, HEIGHT, 128):
        master[y:y + 128] = common16(linear[y:y + 128])
        preview[y:y + 128] = rgb8(master[y:y + 128])
    master.flush()
    image = Image.fromarray(preview)
    complete = target / "complete-stack.jpg"
    image.save(complete, quality=98, subsampling=0, icc_profile=icc)
    overview = image.copy()
    overview.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
    overview_path = target / "overview.jpg"
    overview.save(overview_path, quality=98, icc_profile=icc)
    rows = []
    for label, x, y in WITNESSES:
        crop = master[y:y + 384, x:x + 384].copy()
        require(np.array_equal(crop, common16(linear[y:y + 384, x:x + 384])),
                f"crop differs from complete display: {name}/{label}")
        png, tiff = target / f"{label}.png", target / f"{label}.tiff"
        Image.fromarray(rgb8(crop)).save(png, icc_profile=icc)
        tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None, extratags=tags)
        with Image.open(png) as check:
            require(check.size == (384, 384) and check.info.get("icc_profile") == icc,
                    f"native PNG contract failed: {png}")
            require(np.array_equal(np.asarray(check), rgb8(crop)), f"PNG pixels differ: {png}")
        with tifffile.TiffFile(tiff) as check:
            require(bytes(check.pages[0].tags[34675].value) == icc, f"crop ICC differs: {tiff}")
            require(np.array_equal(check.asarray(), crop), f"TIFF crop pixels differ: {tiff}")
        rows.append({"name": label, "native_xywh": [x, y, 384, 384], "resized": False,
                     "png": reference(png), "rgb16": reference(tiff)})
    del master, linear, preview, image, overview
    # Verify the saved complete TIFF, including every output pixel, after closing its writer.
    master_hash, saved_icc = inspect_rgb(master_path, np.uint16, True)
    require(saved_icc == icc, "saved master ICC differs")
    saved = tifffile.memmap(master_path, mode="r")
    linear = tifffile.memmap(paths["linear_rgb32"], mode="r")
    for y in range(0, HEIGHT, 128):
        require(np.array_equal(saved[y:y + 128], common16(linear[y:y + 128])),
                f"complete saved master differs: {name}")
    del saved, linear
    with Image.open(complete) as check:
        require(check.size == (WIDTH, HEIGHT) and check.info.get("icc_profile") == icc,
                f"complete JPEG contract failed: {name}")
    return {"source_files": {key: reference(path) for key, path in paths.items()},
            "common_master": reference(master_path), "common_master_pixel_sha256": master_hash,
            "complete_jpeg": reference(complete), "overview": reference(overview_path),
            "witnesses": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="completed full299 adapter directory")
    parser.add_argument("--out", required=True, type=Path, help="fresh workspace review directory")
    args = parser.parse_args()
    start = time.monotonic()
    input_dir = args.input.resolve(strict=True)
    output_dir = args.out.resolve()
    require(input_dir.is_dir() and input_dir.is_relative_to(ROOT / "outputs"),
            "input must be a generated workspace output directory")
    require(output_dir.is_relative_to(ROOT) and not output_dir.exists()
            and output_dir.parent.is_dir() and not output_dir.is_relative_to(input_dir),
            "fresh separate workspace output with existing parent required")
    meta_paths = [input_dir / n for n in ("completion.json", "started.json", "baseline-identity.json")]
    done, started, identity = (read_json(path) for path in meta_paths)
    require(done["status"] == "COMPLETE299_OBSERVATION_READY" and done["frames"] == 299
            and done["native_dimensions"] == [WIDTH, HEIGHT], "complete299 receipt required")
    require(done["quality_claim"] is False and done["terminal_mean_exact"] is True,
            "observational/terminal-mean contract differs")
    for key in ("all299_source_metadata_unchanged", "processed_source_contents_unchanged",
                "all299_contents_reread"):
        require(done[key] is True, f"missing producer unchanged-source assertion: {key}")
    require(sorted(row["index"] for row in done["frame_receipts"]) == list(range(299)),
            "receipt must cover every source exactly once")
    require(started["phase"] == "complete299" and started["source_count"] == 299
            and started["held_stack_count"] == 299 and started["arms"] == list(NAMES)
            and started["native_dimensions"] == [WIDTH, HEIGHT]
            and started["crop_quad"] == [34, 23, 3448, 2298]
            and started["map_sha256"] == MAP_SHA and started["order_sha256"] == ORDER_SHA
            and started["fine_changed"] == [0, 1]
            and started["environment"]["STREHL_FIX_CA"] == "off", "held full-run contract differs")
    require(identity == done["baseline_identity"] and identity["exact"] is True
            and identity["scope"] == "complete old CPU CA-off vs new canonical route"
            and identity["held"]["cfa"] == BASE_CFA_SHA, "full baseline identity is not verified")
    require(len(done["arms"]) == len(done["pixel_hashes"]) == 3, "three complete arms required")
    manifest_path = HERE.parent / "photo-review/baseline-witnesses.json"
    manifest = read_json(manifest_path)
    require([(r["name"], *r["rect_xywh"]) for r in manifest["witnesses"]]
            == [(name, x, y, 384, 384) for name, x, y in WITNESSES], "frozen witnesses differ")
    bindings = {str(p): reference(p) for p in [*meta_paths, manifest_path, Path(__file__).resolve()]}
    arm_paths = {}
    icc = None
    for index, name in enumerate(NAMES):
        record = done["arms"][index]
        require(record["entire_output"] is True, f"partial arm: {name}")
        paths = {key: check_record(record[key], input_dir) for key in ("cfa", "rgb16", "linear_rgb32")}
        require(paths["cfa"].name == f"{name}-cfa-dn.f32le"
                and paths["rgb16"].name == f"{name}-master.tiff"
                and paths["linear_rgb32"].name == f"{name}-linear.tiff"
                and paths["cfa"].stat().st_size == WIDTH * HEIGHT * 4, "arm order/extent differs")
        pixel_hash, arm_icc = inspect_rgb(paths["rgb16"], np.uint16, True)
        linear_hash, _ = inspect_rgb(paths["linear_rgb32"], np.float32, False)
        actual = {"rgb16": pixel_hash, "linear_rgb32": linear_hash}
        require(actual == done["pixel_hashes"][index], f"actual RGB pixels differ from receipt: {name}")
        if index == 0:
            require(actual == identity["canonical"]
                    and all(actual[k] == identity["held"][k] for k in actual)
                    and record["cfa"]["sha256"] == BASE_CFA_SHA, "baseline pixel identity differs")
            icc = arm_icc
        require(arm_icc == icc, "arm ICC differs")
        arm_paths[name] = paths
        bindings.update({str(p): {"path": str(p), "bytes": record[key]["bytes"],
                                 "sha256": record[key]["sha256"]} for key, p in paths.items()})
    output_dir.mkdir()
    write_json(output_dir / "started.json", {"status": "EXPORTING_NOT_READY", "input": str(input_dir),
               "bindings": bindings, "baseline_identity": identity, "command": sys.argv})
    arms = {name: export_arm(name, arm_paths[name], output_dir, icc) for name in NAMES}
    for path, bound in bindings.items():
        require(reference(Path(path)) == bound, f"review input changed during export: {path}")
    result = {"schema": 1, "status": "THREE_COMPLETE_COMMON_DISPLAYS_READY_NO_VERDICT",
              "quality_claim": False, "frames": 299, "dimensions": [WIDTH, HEIGHT],
              "display": "Linear RGB32 -> f32 gain3.434 -> clamp0..1 -> standard sRGB -> roundRGB16; PNG/JPEG (RGB16+128)//257. No fitting or sharpening. Only labeled overviews resize.",
              "gauge": "Delivered native RGB; reference149 active origin(68,46); same map/order, CA-off.",
              "baseline_pixel_identity_verified": True, "baseline_identity": identity,
              "input_files_unchanged": True, "original_source_preservation": "Producer full299 before/after hashes asserted by bound completion receipt; reviewer does not reopen RAW files.",
              "bindings": bindings, "icc_sha256": ICC_SHA, "arms": arms,
              "script": reference(Path(__file__).resolve()), "command": sys.argv,
              "versions": {"numpy": np.__version__, "tifffile": tifffile.__version__, "pillow": PILLOW_VERSION},
              "operational_seconds": time.monotonic() - start}
    write_json(output_dir / "common-display-receipt.json", result)
    print(f"Three complete masters/JPEGs and30 frozen native witnesses ready; no quality verdict. {result['operational_seconds']:.3f}s.")


if __name__ == "__main__":
    main()

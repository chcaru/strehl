from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from common import (
    DECODER,
    EXPECTED,
    ROOT,
    SRGB_TO_REC2020,
    SUBJECT,
    WARP_MAP,
    atomic_json,
    bounded_environment,
    image_census,
    linear_rec2020_icc,
    parse_warp_map,
    pixel_sha256,
    read_rgb16,
    sha256,
    tiff_tags,
    write_rgb16,
)


INVENTORY_PATH = ROOT / "source-inventory-preregistered.json"
PREPARED = ROOT / "prepared"
WORK = ROOT / "work"


def fnv_stack_digest(entries: list[dict]) -> str:
    value = 0xCBF29CE484222325
    prime = 0x00000100000001B3
    for entry in entries:
        for byte in entry["name"].encode("utf-8") + b"\0":
            value ^= byte
            value = (value * prime) & 0xFFFFFFFFFFFFFFFF
        for byte in int(entry["bytes"]).to_bytes(8, "little") + b"\0":
            value ^= byte
            value = (value * prime) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def inventory() -> dict:
    paths = sorted(SUBJECT.glob("*.ARW"), key=lambda p: p.name)
    entries = [
        {"ordinal": index, "name": path.name, "bytes": path.stat().st_size}
        for index, path in enumerate(paths)
    ]
    payload = {
        "selection_rule": (
            "Every *.ARW directly inside the registrar-granted tilted-sw10-cpl "
            "directory, sorted by case-sensitive filename; no sibling directory."
        ),
        "read_only_source": str(SUBJECT),
        "frames": len(entries),
        "entries": entries,
        "fnv1a_name_size_digest": fnv_stack_digest(entries),
        "expected_external_inventory_sha256": EXPECTED["source_inventory_sha256"],
    }
    if len(entries) != EXPECTED["frames"]:
        raise RuntimeError(f"found {len(entries)} ARWs, expected {EXPECTED['frames']}")
    if payload["fnv1a_name_size_digest"] != EXPECTED["stack_digest"]:
        raise RuntimeError(
            f"source digest {payload['fnv1a_name_size_digest']}, "
            f"expected {EXPECTED['stack_digest']}"
        )
    if entries[EXPECTED["reference"]]["name"] != EXPECTED["reference_file"]:
        raise RuntimeError("registered reference file changed")
    atomic_json(INVENTORY_PATH, payload)
    return payload


def require_controls() -> dict:
    path = ROOT / "controls" / "PASS.json"
    if not path.is_file():
        raise RuntimeError("controls/PASS.json is absent; subject preparation is forbidden")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError("controls did not pass")
    return payload


def decode_one(source: Path, destination: Path, ordinal: int) -> dict:
    one = WORK / "decode-one"
    if one.exists():
        shutil.rmtree(one)
    one.mkdir(parents=True)
    copied = one / source.name
    shutil.copy2(source, copied)
    source_hash = sha256(source)
    if sha256(copied) != source_hash:
        raise RuntimeError(f"copy hash mismatch for {source.name}")
    command = [
        str(DECODER),
        "stack",
        "--limit",
        "1",
        "--merge",
        "estimator",
        "--photometric",
        "off",
        "--linear-srgb",
        "--out",
        str(destination),
        str(one),
    ]
    env = bounded_environment()
    env["STREHL_ALIGN"] = "0"
    run = subprocess.run(
        command,
        cwd=WORK,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log = ROOT / "decode-logs"
    log.mkdir(exist_ok=True)
    (log / f"{ordinal:03d}.stdout.txt").write_text(run.stdout, encoding="utf-8")
    (log / f"{ordinal:03d}.stderr.txt").write_text(run.stderr, encoding="utf-8")
    shutil.rmtree(one)
    if run.returncode != 0 or not destination.is_file():
        raise RuntimeError(
            f"decoder failed for {source.name} with return code {run.returncode}"
        )
    return {
        "command": command,
        "returncode": run.returncode,
        "raw_sha256": source_hash,
        "stdout_sha256": sha256(log / f"{ordinal:03d}.stdout.txt"),
        "stderr_sha256": sha256(log / f"{ordinal:03d}.stderr.txt"),
    }


def warp_and_convert(
    decoded: np.ndarray, placement: dict, icc: bytes, destination: Path
) -> dict:
    height, width, _ = decoded.shape
    if (width, height) != (EXPECTED["width"], EXPECTED["height"]):
        raise RuntimeError(
            f"decoded geometry {width}x{height}, expected "
            f"{EXPECTED['width']}x{EXPECTED['height']}"
        )
    crop = EXPECTED["crop"]
    cx, cy = width * 0.5, height * 0.5
    xr = (
        crop["x"] + np.arange(crop["width"], dtype=np.float64) - cx
    )[None, :]
    yr = (
        crop["y"] + np.arange(crop["height"], dtype=np.float64) - cy
    )[:, None]
    map_x = (
        placement["a_re"] * xr
        - placement["a_im"] * yr
        + placement["b_re"]
        + cx
    ).astype(np.float32)
    map_y = (
        placement["a_re"] * yr
        + placement["a_im"] * xr
        + placement["b_im"]
        + cy
    ).astype(np.float32)
    if (
        float(map_x.min()) < 0.0
        or float(map_y.min()) < 0.0
        or float(map_x.max()) >= width - 1
        or float(map_y.max()) >= height - 1
    ):
        raise RuntimeError("registered crop is not valid for bilinear prepared warp")
    linear_srgb = decoded.astype(np.float32) / np.float32(65535.0)
    linear_rec2020 = cv2.transform(
        linear_srgb, SRGB_TO_REC2020.astype(np.float32)
    )
    warped = cv2.remap(
        linear_rec2020,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(np.nan, np.nan, np.nan),
    )
    if not np.isfinite(warped).all():
        raise RuntimeError("non-finite sample in prepared warp")
    below = int(np.count_nonzero(warped < 0.0))
    above = int(np.count_nonzero(warped > 1.0))
    if below or above:
        raise RuntimeError(
            f"linear sRGB to Rec.2020/bilinear preparation needed clipping: "
            f"{below} below, {above} above"
        )
    encoded = np.rint(warped.astype(np.float64) * 65535.0).astype(np.uint16)
    write_rgb16(
        destination,
        encoded,
        icc,
        "M8 prepared identity-boundary input; linear Rec.2020 D65",
    )
    return {
        "pixel_sha256": pixel_sha256(encoded),
        "file_sha256": sha256(destination),
        "tags": tiff_tags(destination),
        "census": image_census(encoded),
        "pre_quantization_below_zero": below,
        "pre_quantization_above_one": above,
        "map_extrema": {
            "x_min": float(map_x.min()),
            "x_max": float(map_x.max()),
            "y_min": float(map_y.min()),
            "y_max": float(map_y.max()),
        },
    }


def prepare() -> dict:
    cv2.setNumThreads(6)
    controls = require_controls()
    if sha256(DECODER) != EXPECTED["decoder_sha256"]:
        raise RuntimeError("decoder binary changed after preregistration")
    source_inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    current = inventory()
    if current["entries"] != source_inventory["entries"]:
        raise RuntimeError("source inventory changed after preregistration")
    warp_map = parse_warp_map()
    icc = linear_rec2020_icc()
    expected_icc_hash = controls["icc"]["sha256"]
    if sha256(ROOT / "controls" / "linear-rec2020-v2.icc") != expected_icc_hash:
        raise RuntimeError("commissioned ICC changed")
    PREPARED.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    decoded_path = WORK / "decoded-linear-srgb.tif"
    partial_path = ROOT / "prepared-manifest.partial.json"
    partial = (
        json.loads(partial_path.read_text(encoding="utf-8"))
        if partial_path.is_file()
        else {"frames": []}
    )
    completed = {row["ordinal"]: row for row in partial["frames"]}
    rows = []
    for entry, placement in zip(current["entries"], warp_map["placements"], strict=True):
        ordinal = entry["ordinal"]
        source = SUBJECT / entry["name"]
        destination = PREPARED / f"{ordinal:03d}-{source.stem}.tif"
        previous = completed.get(ordinal)
        if previous and destination.is_file():
            image = read_rgb16(destination)
            if (
                sha256(destination) == previous["prepared"]["file_sha256"]
                and pixel_sha256(image) == previous["prepared"]["pixel_sha256"]
                and tiff_tags(destination)["icc_sha256"] == expected_icc_hash
            ):
                rows.append(previous)
                continue
        decoded_path.unlink(missing_ok=True)
        decode = decode_one(source, decoded_path, ordinal)
        decoded = read_rgb16(decoded_path)
        decoded_record = {
            "shape": list(decoded.shape),
            "dtype": str(decoded.dtype),
            "pixel_sha256": pixel_sha256(decoded),
            "file_sha256": sha256(decoded_path),
            "tags": tiff_tags(decoded_path),
            "census": image_census(decoded),
        }
        prepared = warp_and_convert(decoded, placement, icc, destination)
        row = {
            "ordinal": ordinal,
            "source": str(source),
            "source_name": source.name,
            "source_bytes": source.stat().st_size,
            "raw_sha256": decode["raw_sha256"],
            "placement_bits": placement["bits"],
            "decode": decode,
            "decoded": decoded_record,
            "prepared_path": str(destination.resolve()),
            "prepared": prepared,
        }
        rows.append(row)
        atomic_json(partial_path, {"frames": rows})
        print(f"prepared {ordinal + 1}/{EXPECTED['frames']}: {source.name}", flush=True)
    decoded_path.unlink(missing_ok=True)
    payload = {
        "status": "PREPARED",
        "subject": EXPECTED["subject"],
        "score_status": "commissioning/development only; never scoreable",
        "source_root_read_only": str(SUBJECT),
        "source_selection": current,
        "warp_map": str(WARP_MAP.resolve()),
        "warp_map_sha256": EXPECTED["warp_map_sha256"],
        "reference": EXPECTED["reference"],
        "reference_file": EXPECTED["reference_file"],
        "preparation": {
            "decoder": str(DECODER),
            "decoder_sha256": EXPECTED["decoder_sha256"],
            "decode_command_template": (
                "strehl.exe stack --limit 1 --merge estimator --photometric off "
                "--linear-srgb --out <decoded> <single-file-copy-directory>; "
                "STREHL_ALIGN=0"
            ),
            "input_decode_domain": "linear sRGB/BT.709 primaries, D65, no transfer curve",
            "matrix_srgb_to_rec2020": SRGB_TO_REC2020.tolist(),
            "warp": (
                "OpenCV remap INTER_LINEAR, placement pulls reference to source, "
                "float32 maps, crop applied directly during gather"
            ),
            "crop": EXPECTED["crop"],
            "quantization": "round-to-nearest via numpy.rint, then uint16; clipping forbidden",
            "output_domain": "linear ITU-R BT.2020 primaries, D65, identity TRCs",
            "icc_sha256": expected_icc_hash,
        },
        "frames": rows,
    }
    atomic_json(ROOT / "prepared-manifest.json", payload)
    partial_path.unlink(missing_ok=True)
    print(json.dumps({"status": "PREPARED", "frames": len(rows)}, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["inventory", "prepare"])
    args = parser.parse_args()
    if args.operation == "inventory":
        print(json.dumps(inventory(), indent=2))
    else:
        prepare()


if __name__ == "__main__":
    main()

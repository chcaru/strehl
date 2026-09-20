"""Native fixed-window paired views; exact crop-origin translation, no scoring.

Reads completed TIFFs only. Importing this helper performs no work.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

import numpy as np
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROZEN = ROOT / "experiments/quality-september19/vitamin-c-review-1/regions.json"
FULL_HELPER = ROOT / "experiments/quality-september19/full-output-views.py"


def binding(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=HERE / "full-1")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    out = args.out.resolve() if args.out else run / "photo-comparison-1"
    assert run.is_relative_to(HERE) and out.is_relative_to(HERE)
    source = run / "output"
    started_path = source / "started.json"
    receipt_path = source / "receipt.json"
    started = json.loads(started_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    frozen = json.loads(FROZEN.read_text())
    initial = started["original_crop"]
    effective = started["effective_crop"]
    assert initial == [28, 19, 3460, 2306]
    assert effective == receipt["effective_crop"]
    assert len(effective) == 4 and all(type(v) is int and v >= 0 for v in effective)
    assert receipt["frames"] == 70
    width, height = 2 * effective[2], 2 * effective[3]
    assert receipt["native_dimensions"] == [width, height]
    assert effective[0] >= initial[0] and effective[1] >= initial[1]
    assert effective[0] + effective[2] <= initial[0] + initial[2]
    assert effective[1] + effective[3] <= initial[1] + initial[3]
    offset = [2 * (initial[0] - effective[0]), 2 * (initial[1] - effective[1])]
    regions = []
    for row in frozen["regions"]:
        x, y, w, h = row["xywh"]
        assert w == h == 384
        mapped = [x + offset[0], y + offset[1], w, h]
        assert 0 <= mapped[0] <= width - w and 0 <= mapped[1] <= height - h
        regions.append(dict(name=row["name"], frozen_xywh=row["xywh"], pair_xywh=mapped,
                            reference_sensor_xywh=[x + 2 * initial[0], y + 2 * initial[1], w, h]))
    assert len(regions) == 5
    input_bindings = {}
    for arm in ("baseline", "candidate", "late"):
        path = source / (arm + ".tiff")
        input_bindings[arm] = binding(path)
        assert input_bindings[arm]["sha256"] == receipt[arm + "_sha256"]
        with tifffile.TiffFile(path) as tf:
            assert tf.pages[0].shape == (height, width, 3)
            assert str(tf.pages[0].dtype) == "uint16"
    # Create output only after all three images and completion receipt have been validated.
    out.mkdir()
    outputs = []
    for arm in ("baseline", "candidate", "late"):
        path = source / (arm + ".tiff")
        with tifffile.TiffFile(path) as tf:
            pixels = tf.asarray()
            icc_tag = tf.pages[0].tags.get(34675)
            icc = icc_tag.value if icc_tag else None
        image_options = {"icc_profile": icc} if icc else {}
        for region in regions:
            x, y, w, h = region["pair_xywh"]
            patch = ((pixels[y:y+h, x:x+w].astype(np.uint32) + 128) // 257).astype(np.uint8)
            assert patch.shape == (384, 384, 3)
            output = out / f"{region['name']}-{arm}.png"
            Image.fromarray(patch).save(output, **image_options)
            with Image.open(output) as check:
                assert np.array_equal(np.asarray(check), patch)
            outputs.append(binding(output))
        del pixels
        # Existing full-output helper preserves original extent and ICC, and
        # independently checks the RGB8 PNG against its rounded RGB16 source.
        command = [sys.executable, "-I", "-B", str(FULL_HELPER), str(path), str(out / (arm + ".png"))]
        child = subprocess.run(command, capture_output=True, text=True, timeout=90)
        (out / (arm + "-full-conversion.log")).write_text(child.stdout + child.stderr, encoding="utf-8")
        assert child.returncode == 0, child.stderr
        full_receipt = json.loads((out / (arm + ".json")).read_text())
        assert full_receipt["shape"] == [height, width, 3]
        assert full_receipt["source_sha256"] == input_bindings[arm]["sha256"]
        with Image.open(out / (arm + ".png")) as full:
            assert full.size == (width, height)
            overview = full.copy()
        overview.thumbnail((1560, 1100), Image.Resampling.LANCZOS)
        overview.save(out / (arm + "-overview.jpg"), quality=95, **image_options)
        outputs.extend([binding(out / (arm + ".png")), binding(out / (arm + "-overview.jpg"))])
    save(out / "coordinate-receipt.json", dict(
        schema=1, input_images=input_bindings, started=binding(started_path), completion=binding(receipt_path),
        frozen_regions=binding(FROZEN), helper=binding(Path(__file__)), full_output_helper=binding(FULL_HELPER),
        initial_crop_quads=initial, effective_crop_quads=effective, native_translation=offset,
        coordinate_rule="pair_xy = frozen_xy + 2 * (initial_crop_origin - effective_crop_origin)",
        native_dimensions=[width, height], regions=regions, outputs=outputs,
        crop_display="384 x 384 native samples; rounded division by 257; no resampling or other adjustment",
        whole_png="complete triplet extent, same dimensions; rounded division by 257; ICC retained",
        overview="resized for whole-field orientation only; not evidence of native detail",
        scope="image preparation only; no RAW decode, render, score or quality verdict"))
    print(json.dumps(dict(status="COMPLETE_TRIPLET_VIEWS_READY", out=str(out), native_translation=offset,
                          native_dimensions=[width, height], regions=regions)), flush=True)


if __name__ == "__main__":
    main()

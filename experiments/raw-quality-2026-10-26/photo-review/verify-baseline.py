"""Independent readback of frozen photographic witnesses; no RAW decoding."""
from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import PIL
from PIL import Image
import tifffile


HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = HERE / "baseline-witnesses.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    master_path = Path(manifest["master"]["path"])
    assert sha(master_path) == manifest["master"]["sha256"]
    with tifffile.TiffFile(master_path) as f:
        master = f.asarray()
        icc = bytes(f.pages[0].tags[34675].value)
    assert master.shape == (4596, 6896, 3) and master.dtype == np.uint16
    assert hashlib.sha256(icc).hexdigest() == manifest["icc_sha256"]
    rows = []
    for witness in manifest["witnesses"]:
        x, y, w, h = witness["rect_xywh"]
        expected = master[y:y+h, x:x+w]
        tiff_path, png_path = (Path(witness[k]["path"]) for k in ("rgb16", "png8"))
        assert sha(tiff_path) == witness["rgb16"]["sha256"]
        assert sha(png_path) == witness["png8"]["sha256"]
        with tifffile.TiffFile(tiff_path) as f:
            actual = f.asarray()
            assert np.array_equal(actual, expected)
            assert bytes(f.pages[0].tags[34675].value) == icc
        with Image.open(png_path) as image:
            assert image.size == (384, 384)
            assert image.info["icc_profile"] == icc
            expected8 = ((expected.astype(np.uint32) + 128) // 257).astype(np.uint8)
            assert np.array_equal(np.asarray(image), expected8)
        changed = actual.copy()
        changed[0, 0, 0] ^= np.uint16(1)
        assert not np.array_equal(changed, expected), "one-bit wrong-pixel negative control escaped"
        rows.append({"name": witness["name"], "rect_xywh": witness["rect_xywh"],
                     "rgb16_exact": True, "png8_exact": True, "icc_exact": True,
                     "one_bit_mutation_rejected": True,
                     "visually_inspected_individually_detail_original": True})
    receipt = {
        "schema": 1,
        "status": "BASELINE_ONLY_NO_GAIN_CLAIM",
        "command": "python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/verify-baseline.py",
        "cwd": str(HERE.parents[2]),
        "source_master_sha256": sha(master_path),
        "manifest_sha256": sha(manifest_path),
        "verifier_sha256": sha(Path(__file__).resolve()),
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "pillow": PIL.__version__, "tifffile": tifffile.__version__},
        "visual_observations": "Human-readable model review in baseline-review.md; flags record actual prior view_image calls, not an automated quality metric.",
        "full_output_viewed_first": True,
        "full_output_tool_display_dimensions": [1920, 1280],
        "complete_output_dimensions": [6896, 4596],
        "full_view_is_orientation_only": True,
        "commission": {"path": str(HERE / "viewer-commission-384.png"),
                       "sha256": sha(HERE / "viewer-commission-384.png"),
                       "native_dimensions": [384, 384],
                       "observed": "Vertical/horizontal one-pixel stripe directions, diagonal pattern and checker pattern distinguishable; no screen color calibration claimed."},
        "candidate_seen": False,
        "raw_decodes": 0,
        "witnesses": rows,
    }
    (HERE / "inspection-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(rows)} frozen crop pixel/ICC bindings and wrong-pixel rejection; baseline only.")


if __name__ == "__main__":
    main()

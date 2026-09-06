"""Independent, synthetic-only M193 challenge; never edits frozen M193 files.

Before execution, rejection expectations are:
* stale hash after shrinking an overlap denominator must be rejected;
* unknown overlap schema and inconsistent rectangle counts must be rejected;
* an output descriptor without a real adapter may validate syntax only, never
  establish product geometry closure;
* identity-geometry inputs with complementary defocus can defeat a single
  reference, despite the same registration succeeding when focus is shared.

These are counterexamples to closure, not product-quality measurements.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "M193-cover-overlap" / "reference.py"
spec = importlib.util.spec_from_file_location("m193_frozen", SOURCE)
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


def capture(operation):
    try:
        return {"accepted": True, "value": operation()}
    except M.ContractError as exc:
        return {"accepted": False, "code": exc.code, "detail": str(exc)}


def main():
    frozen = M.load_json(SOURCE.parent / "fixtures.json")
    overlap = frozen["synthetic_overlap"]
    grid = M.make_output_grid(
        overlap, arm_id="cropped-grid",
        expected_width=overlap["native_width"] - 12,
        expected_height=overlap["native_height"] - 10,
        derivation_kind="predeclared_program_grid",
    )
    result = {
        "scope": "Independent development-only counterexamples; no RAW/candidate/holdout access",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "baseline_cropped": M.output_retention(overlap, grid),
    }
    identity = M.make_output_grid(
        overlap, arm_id="identity-control",
        expected_width=overlap["native_width"],
        expected_height=overlap["native_height"],
    )
    result["identity_control"] = M.output_retention(overlap, identity)
    stale = copy.deepcopy(overlap)
    stale["common_overlap"] = {"x": 20, "y": 20, "width": 20, "height": 20, "area_pixels": 400}
    result["denominator_tamper"] = {
        "hash_is_stale": M.manifest_digest(stale) != stale["manifest_sha256"],
        "outcome": capture(lambda: M.output_retention(stale, grid)),
    }
    unknown = copy.deepcopy(overlap)
    unknown["schema"] = "UNRECOGNIZED-OVERLAP-SCHEMA"
    result["unknown_schema"] = capture(lambda: M.output_retention(unknown, identity))
    inconsistent = copy.deepcopy(overlap)
    inconsistent["common_overlap"]["area_pixels"] = 1
    result["inconsistent_area"] = capture(lambda: M.output_retention(inconsistent, identity))
    unknown_adapter = copy.deepcopy(identity)
    unknown_adapter["adapter_sha256"] = "0" * 64
    unknown_adapter["settings_sha256"] = "0" * 64
    result["unbacked_adapter_syntax"] = capture(lambda: M.output_retention(overlap, unknown_adapter))
    if "--focus" in sys.argv:
        import cv2
        import numpy as np
        rng = np.random.default_rng(731943)
        texture = cv2.GaussianBlur(rng.uniform(3000, 62000, (288, 384)).astype(np.float32), (0, 0), 0.7)
        far = cv2.GaussianBlur(texture, (0, 0), 12.0)
        left = far.copy()
        right = far.copy()
        left[:, :184] = texture[:, :184]
        right[:, 200:] = texture[:, 200:]
        rgb = lambda a: np.repeat(np.clip(np.rint(a), 0, 65535).astype(np.uint16)[..., None], 3, axis=2)
        a, b = rgb(left), rgb(right)
        fa, fb = M.extract_features(a), M.extract_features(b)
        result["focus_identity_control"] = capture(lambda: M.register_to_reference(fa, fa)[1])
        result["complementary_focus"] = {
            "native_width": 384, "native_height": 288,
            "planted_geometry": "exact identity; only local PSF changes",
            "features": [len(fa.keys), len(fb.keys)],
            "direct_matches": len(M.match_features(fa, fb)),
            "outcome": capture(lambda: M.construct_overlap([M.encode_tiff(a), M.encode_tiff(b)])),
        }
    result["native_input_payload_lower_bound"] = {
        "one_rgb16_frame_bytes": 7032 * 4688 * 3 * 2,
        "n299_blob_and_decoded_bytes": 2 * 299 * 7032 * 4688 * 3 * 2,
        "n299_blob_and_decoded_gib": 2 * 299 * 7032 * 4688 * 3 * 2 / 2**30,
        "scope": "derived payload only: construct_overlap retains input TIFF byte strings and a decoded list; excludes overhead",
    }
    target = ROOT / "challenge-results.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert result["baseline_cropped"]["field_of_view_verdict"] == "FAIL_GEOMETRY_FIELD_OF_VIEW"
    assert result["identity_control"]["field_of_view_verdict"] == "PASS"
    assert result["denominator_tamper"]["hash_is_stale"]
    assert result["denominator_tamper"]["outcome"]["accepted"]
    assert result["denominator_tamper"]["outcome"]["value"]["field_of_view_verdict"] == "PASS"
    print("REPRODUCED: stale-denominator defect changes FAIL to PASS")


if __name__ == "__main__":
    main()

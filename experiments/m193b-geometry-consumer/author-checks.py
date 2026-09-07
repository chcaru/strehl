"""Bounded author regressions; independent evidence is independent-verify.py."""
from __future__ import annotations

import copy
import hashlib
import json
import uuid
from pathlib import Path
from unittest.mock import patch

import consumer as c


def main() -> None:
    records = []
    frozen = c.HERE.parent / "M193-cover-overlap"
    protected = [frozen / name for name in ("reference.py", "fixtures.json", "contract-v1.json")]
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    workspace = c.HERE / ("author-inputs-" + uuid.uuid4().hex)
    workspace.mkdir()
    try:
        base = c.v1.synthetic_rgb()
        images = [base, c.v1.warp_synthetic(base, scale=0.985, rotation_degrees=0.35, tx=3.25, ty=-2.5),
                  c.v1.warp_synthetic(base, scale=1.018, rotation_degrees=-0.25, tx=-4.0, ty=3.0)]
        paths = []
        for index, image in enumerate(images):
            path = workspace / f"fixture-{index}.tif"
            path.write_bytes(c.v1.encode_tiff(image))
            paths.append(path)
        del images, image, base
        manifest, binding = c.construct_overlap_paths(paths)
        fixtures = json.loads((frozen / "fixtures.json").read_text())
        assert manifest == fixtures["synthetic_overlap"]
        records.append({"case": "frozen-manifest-exact", "pass": True,
                        "manifest_sha256": manifest["manifest_sha256"]})
        for label, dw, dh in (("identity", 0, 0), ("cropped", 12, 10)):
            grid = c.v1.make_output_grid(manifest, arm_id=label + "-grid",
                    expected_width=manifest["native_width"] - dw,
                    expected_height=manifest["native_height"] - dh,
                    derivation_kind="predeclared_program_grid" if dw else "identity_reference_grid")
            result = c.output_retention(manifest, grid, binding)
            assert result == fixtures["output_retention"][label]
            records.append({"case": "frozen-" + label, "pass": True, "result": result})
        crop = grid
        for rehash in (False, True):
            changed = copy.deepcopy(manifest)
            changed["common_overlap"] = {"x": 20, "y": 20, "width": 20, "height": 20, "area_pixels": 400}
            changed_grid = copy.deepcopy(crop)
            if rehash:
                changed["manifest_sha256"] = c.v1.manifest_digest(changed)
                changed_grid["overlap_manifest_sha256"] = changed["manifest_sha256"]
            legacy = c.v1.output_retention(changed, changed_grid)
            assert legacy["field_of_view_verdict"] == "PASS"
            with patch.object(c.v1, "output_retention", side_effect=AssertionError("counting occurred")):
                try:
                    c.output_retention(changed, changed_grid, binding)
                except c.ContractError as exc:
                    records.append({"case": "rehash-small-denominator" if rehash else "stale-small-denominator",
                                    "pass": True, "legacy_result": legacy, "refusal": str(exc)})
                else:
                    raise AssertionError("malicious denominator was accepted")
        # Prove structural replay catches a nonmaximal rectangle independently of
        # the external-binding check; this private call cannot mint authority.
        changed["manifest_sha256"] = c.v1.manifest_digest(changed)
        try:
            c._validate_manifest_structure(changed)
        except c.ContractError as exc:
            assert "maximal" in str(exc)
            records.append({"case": "private-geometry-replay-negative", "pass": True, "refusal": str(exc)})
        else:
            raise AssertionError("geometry replay accepted smaller rectangle")
        snapshot = c.validate_overlap(manifest, binding)
        snapshot["common_overlap"]["area_pixels"] = 1
        assert c.validate_overlap(manifest, binding)["common_overlap"]["area_pixels"] == 99918
        records.append({"case": "validated-snapshot-detached", "pass": True})
        # Equal digest and length must still sort/deduplicate by exact bytes.
        a, b = workspace / "collision-a", workspace / "collision-b"
        a.write_bytes(b"abc")
        b.write_bytes(b"abd")
        ia = c._InputFile(a, b"x" * 32, 3)
        ib = c._InputFile(b, b"x" * 32, 3)
        assert c._compare_files(ia, ib) == -1 and c._compare_files(ib, ia) == 1
        assert c._compare_files(ia, ia) == 0
        records.append({"case": "forced-collision-byte-tiebreak", "pass": True})
        # A changed source between hash registration and snapshot decode refuses.
        expected = c._scan(paths[0])
        paths[0].write_bytes(paths[0].read_bytes() + b"changed")
        try:
            c.decode_input_path(paths[0], expected.digest.hex(), expected.length)
        except c.ContractError as exc:
            assert "input changed" in str(exc)
            records.append({"case": "changed-source-refused", "pass": True, "refusal": str(exc)})
        else:
            raise AssertionError("changed source decoded under old hash")
        assert hashes == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        result = {"status": "AUTHOR_REGRESSION_PASS", "records": records,
                  "frozen_files_before_after_sha256": hashes}
        (c.HERE / "author-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        assert workspace.resolve().parent == c.HERE.resolve()
        for child in workspace.iterdir():
            assert child.is_file()
            child.unlink()
        workspace.rmdir()


if __name__ == "__main__":
    main()

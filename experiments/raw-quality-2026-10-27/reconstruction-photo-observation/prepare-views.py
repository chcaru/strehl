"""Fixed display of the complete finite reconstruction diagnostic; no quality admission."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import time

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / "experiments/raw-quality-2026-10-26/flat-baseline/frozen-witnesses.json"
FROZEN_SHA = "fde6bb02b6ca12793176b3e30ef8d60bba5aed3ed86dd1d4e3ea080c736a297e"
ARMS = ("baseline", "candidate")


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 << 20):
            h.update(block)
    st = path.stat()
    return dict(path=str(path), sha256=h.hexdigest(), bytes=st.st_size, mtime_ns=st.st_mtime_ns)


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Complete60 output directory containing receipt.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    assert source.is_relative_to(ROOT / "outputs") and source.is_dir()
    assert out.is_relative_to(ROOT / "outputs") and not out.exists()
    assert not out.is_relative_to(source), "review output must be outside immutable observation"
    receipt_path = source / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    frozen = json.loads(FROZEN.read_text())
    assert ref(FROZEN)["sha256"] == FROZEN_SHA
    assert frozen["dimensions"] == [6932, 4620] and len(frozen["witnesses"]) == 8
    assert receipt["status"] == "COMPLETE60_FINITE_RECONSTRUCTION_DIAGNOSTIC"
    assert receipt["source_count"] == 60
    assert receipt["baseline_pixel_golden_exact"] is True
    assert receipt["original_bytes_and_metadata_unchanged"] is True
    assert receipt["held_map_order_baseline_unchanged"] is True
    assert receipt["admission"] is False and receipt["quality_claim"] is False
    assert receipt["native_dimensions"] == frozen["dimensions"]
    assert receipt["crop_quad_xywh"] == frozen["crop_quad_xywh"]
    for key in ("observer_nonperturbation_exact", "baseline_material_metadata_golden_exact",
                "pair_material_metadata_exact", "actual_input_hull_applied", "hard_solver_gate_passed"):
        assert receipt[key] is True, key
    assert receipt["rendered_cfa_planes"] == 4
    assert receipt["candidate_role"] == "finite reconstruction diagnostic; solver refusal preserved"
    paths = [receipt_path, FROZEN, Path(__file__).resolve()]
    observer_path, solver_path = source / "observer-placebo.json", source / "solver-results.json"
    observer = json.loads(observer_path.read_text())
    solver = json.loads(solver_path.read_text())
    assert observer == receipt["observer"]
    for key in ("finish_before_after_extraction_exact", "finish_before_after_solve_exact",
                "canonical_target_collapse_hull_exact", "state_weights_hull_targets_exact",
                "actual_input_hull_applied", "observer_nonperturbation_exact"):
        assert observer[key] is True, key
    for kind in ("accumulator", "hull"):
        assert observer[kind + "_before_sha256"] == observer[kind + "_after_sha256"]
    assert solver["planes"] == receipt["solver_results"]
    assert [row["plane"] for row in solver["planes"]] == [0, 1, 2, 3]
    assert solver["iterations_cap"] == 32 and solver["restart_iteration"] == 8
    assert solver["error_rms_limit"] == 0.02
    assert solver["operator_sha256"] == receipt["operator_sha256"]
    assert solver["admission"] is False and solver["quality_claim"] is False
    assert solver["rendered_even_if_iteration_cap_refused"] is True
    assert solver["all_solver_converged"] == receipt["all_solver_converged"] == all(row["converged"] for row in solver["planes"])
    paths.extend((observer_path, solver_path))
    for row in solver["planes"]:
        per_plane = source / ("solver-plane-" + str(row["plane"]) + ".json")
        assert json.loads(per_plane.read_text()) == row
        assert row["admission"] is False and 0 <= row["iterations"] <= 32
        assert ((row["converged"] is True and row["refusal"] is None)
                or (row["converged"] is False and row["refusal"] == "iteration-cap"))
        assert all(math.isfinite(row[key]) for key in ("relative_residual", "error_bound_rms", "correction_rhs_norm",
                   "correction_residual_norm", "correction_objective", "final_rounding_bound", "initial_objective", "objective"))
        assert row["objective"] <= row["initial_objective"]
        paths.append(per_plane)
    # The actual consumer performed its hard checks before writing any image.
    # Retain every numerical flag and trace verbatim; convergence is not required.
    files = {}
    for arm in ARMS:
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
        assert [sensor["width"], sensor["height"]] == frozen["dimensions"]
        assert sensor["active_native_origin"] == frozen["reference_active_offset_xy"]
        assert files[arm]["sensor"].stat().st_size == 6932 * 4620 * 4
        assert sensor["payload"]["sha256"] == receipt[arm]["sensor"]["sha256"]
        paths.append(sidecar)
    before = [ref(path) for path in paths]
    out.mkdir(parents=True)
    rows = []
    common_icc = None
    for arm in ARMS:
        dest = out / arm
        dest.mkdir()
        path = files[arm]["rgb16"]
        with tifffile.TiffFile(path) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.uint16
            assert tif.pages[0].shape == (4620, 6932, 3)
            icc = bytes(tif.pages[0].tags[34675].value)
            rgb = tif.asarray()
        assert icc
        if common_icc is None:
            common_icc = icc
        else:
            assert icc == common_icc, "arms must have identical ICC"
        with tifffile.TiffFile(files[arm]["linear"]) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.float32
            assert tif.pages[0].shape == (4620, 6932, 3)
        pixel_sha = hashlib.sha256(memoryview(rgb).cast("B")).hexdigest()
        assert pixel_sha == receipt[arm]["rgb16_pixels_sha256"]
        # Reuse the already fixed writer pixels; no new display fitting/filter.
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
            crop, png8 = rgb[y:y+h, x:x+w].copy(), rgb8[y:y+h, x:x+w].copy()
            png, tiff = dest / (witness["name"] + ".png"), dest / (witness["name"] + ".tiff")
            Image.fromarray(png8).save(png, icc_profile=icc)
            tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None,
                             extratags=[(34675, "B", len(icc), icc, False)])
            with tifffile.TiffFile(tiff) as check:
                assert np.array_equal(check.asarray(), crop)
                assert bytes(check.pages[0].tags[34675].value) == icc
            with Image.open(png) as check:
                assert np.array_equal(np.asarray(check), png8) and check.info.get("icc_profile") == icc
            crops.append(dict(name=witness["name"], native_xywh=[x,y,w,h], png=ref(png), tiff=ref(tiff), exact=True))
        rows.append(dict(arm=arm, role="canonical baseline" if arm == "baseline" else "finite reconstruction diagnostic; solver refusal preserved",
                         master=ref(path), linear_master=ref(files[arm]["linear"]), sensor_master=ref(files[arm]["sensor"]),
                         full_jpeg=ref(full), overview=ref(dest / "overview.jpg"), rgb16_pixel_sha256=pixel_sha, crops=crops))
        del rgb, rgb8, whole
    assert [ref(path) for path in paths] == before, "input changed during display export"
    result = dict(command=sys.argv, status="COMPLETE_DIAGNOSTIC_IMAGES_READY_NO_VERDICT", seconds=time.monotonic()-started,
                  inputs=before, arms=rows, inputs_unchanged=True, observation_receipt=receipt,
                  admission=False, photographic_improvement_claimed=False,
                  display="Existing fixed-tone RGB16; (value+128)//257; common original ICC; no per-arm retone or sharpening.",
                  scope="Both full JPEGs retain entire output. Overview resampling is orientation only. All eight crops are exact384 subarrays.")
    save(out / "display-receipt.json", result)
    print(json.dumps(dict(status=result["status"], seconds=result["seconds"], receipt=ref(out / "display-receipt.json"))))


if __name__ == "__main__":
    main()

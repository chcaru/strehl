"""Root-run saved final-CFA completion and genuine normalized-camera delivery.

Importing this module performs no tensor import, GPU work, decode or export.
The helper develop_camera is also the native delivery path for independent controls.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OPERATOR = HERE / "spectral-completion.py"
STATUS = "COMPLETE_NORMALIZED_CAMERA_NATIVE_DEVELOPMENT"
HELD_CAMERA = "42429be10904e1c81a95e83fc0d1fed22a1ced1eb211c9d449a20cb0cef2a7cf"
HELD_CFA = "1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0"
HELD_DEVELOPMENT = "26a441851ee4344c78d86ef1f8eeb39002acea01ba93b34319c60992e2a9c7c0"
HELD_RGB = "f98cb4d9bc281eb9f28f4e618878607d7e7317eeb7ac20b349f35dfee81c280c"
HELD_LINEAR = "ee2b711bc36e48b9913531e1c615bd265ad06fd395a74f6224ca94392e32be09"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return dict(path=str(path), sha256=h.hexdigest(), bytes=path.stat().st_size)


def snapshot(path):
    value = ref(path)
    return dict(value, mtime_ns=Path(path).stat().st_mtime_ns)


def bind(value):
    path = Path(value["path"]).resolve()
    actual = ref(path)
    require(actual["sha256"] == value["sha256"] and actual["bytes"] == value["bytes"],
            "bound file changed: " + str(path))
    return path


def read(path):
    path = Path(path)
    require(path.stat().st_size <= 4 << 20, "JSON input exceeds 4MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    require(len(text.encode("utf-8")) <= 4 << 20, "JSON output exceeds 4MiB")
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        f.write(text)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def renderer_executable(binding_path):
    value = read(binding_path)
    require(set(value) == {"path", "sha256", "bytes"}, "renderer binding must be exact file binding")
    return bind(value), value


def verify_native(record, width, height, origin):
    require(record["status"] == STATUS and record["schema"] == 1 and record["complete"] is True,
            "normalized-camera writer incomplete")
    require(record["native_dimensions"] == [width, height] and record["active_origin_xy"] == list(origin),
            "native output geometry changed")
    require(record["writer_completion_stages"] == record["writer_demosaic_calls"] == 0
            and record["source_demosaic_calls"] == record["remosaic_calls"] == record["RAW_reads"] == 0,
            "writer added a completion/RAW stage")
    require(record["normalization_applied"] is False and record["input_clamp_applied"] is False
            and record["tone_measured_from_output"] is False,
            "writer changed normalization or tone")
    require(record["signed_camera_copy_bit_exact"] is True and record["pixel_readback_exact"] is True
            and record["retained_input_bytes_and_metadata_unchanged"] is True and record["entire_output"] is True
            and record["quality_claim"] is False and record["photographic_admission"] is False,
            "writer preservation/readback/scope differs")
    require(record["camera_rgb"]["bytes"] == width * height * 12
            and record["camera_rgb"]["sha256"] == record["input_camera_rgb"]["sha256"],
            "native camera extent/copy changed")
    for key in ("input_camera_rgb", "source_receipt", "camera_rgb", "rgb16", "linear_rgb32",
                "development_receipt", "executable", "configuration"):
        bind(record[key])
    return record


def verify_mhc(path):
    value = read(path)
    require(value["schema"] == 1 and value["status"] == "COMPLETE_NATIVE_CFA_DEVELOPMENT"
            and value["complete"] is True and value["physical_pattern"] == "RGGB",
            "existing actual MHC final-CFA receipt required")
    w, h = value["native_dimensions"]
    require(4 <= w <= 8192 and 4 <= h <= 8192 and w * h <= 40_000_000,
            "MHC field exceeds bounded native extent")
    require(value["demosaic_stages"] == 1 and value["demosaic_row_calls"] == h
            and value["demosaic_implementation"] == "strehl_core::demosaic::demosaic_malvar_row"
            and value["source_demosaic_calls"] == value["remosaic_calls"] == value["RAW_reads"] == 0,
            "actual one-stage MHC reference required")
    require(value["signed_cfa_copy_bit_exact"] is True and value["pixel_readback_exact"] is True
            and value["retained_input_bytes_and_metadata_unchanged"] is True
            and value["quality_claim"] is False and value["photographic_admission"] is False,
            "MHC reference preservation/scope differs")
    require(value["cfa"]["sha256"] == value["input_cfa"]["sha256"] and value["cfa"]["bytes"] == w * h * 4,
            "signed MHC input field differs")
    for key in ("cfa", "input_cfa", "camera_rgb", "rgb16", "linear_rgb32", "development_receipt",
                "configuration", "executable"):
        bind(value[key])
    return value


def verify_null(path, renderer_binding):
    value = verify_native(read(path), 6896, 4596, (68, 46))
    parity = value["parity"]
    require(parity["requested"] is True and all(parity[k] is True for k in (
        "rgb16_pixel_exact", "linear_pixel_exact", "rgb16_material_exact", "linear_material_exact")),
        "held normalized-camera native null must be exact")
    require(value["input_camera_rgb"]["sha256"] == HELD_CAMERA
            and value["pixel_hashes"]["rgb16"] == HELD_RGB
            and value["pixel_hashes"]["linear_rgb32"] == HELD_LINEAR
            and value["development_receipt"]["sha256"] == HELD_DEVELOPMENT,
            "held null camera/development/pixels differ")
    if renderer_binding is not None:
        _, exe = renderer_executable(renderer_binding)
        require(value["executable"]["sha256"] == exe["sha256"], "writer differs from commissioned null")
    source = verify_mhc(bind(value["source_receipt"]))
    require(source["camera_rgb"]["sha256"] == HELD_CAMERA and source["cfa"]["sha256"] == HELD_CFA,
            "null is not the actual held MHC camera field")
    for key in ("rgb16", "linear_rgb32"):
        bind(parity["references"][key])
    return value


def develop_camera(*, camera_path, width, height, active_origin_xy, source_receipt,
                   development_receipt, renderer_binding, out_dir, parity_reference=None):
    """Invoke only the new normalized-camera writer; root owns process/job bounds."""
    out_dir = Path(out_dir).resolve()
    require(not out_dir.exists() and out_dir.parent.is_dir(), "native output must be fresh")
    exe, executable = renderer_executable(renderer_binding)
    config_path = out_dir.with_name(out_dir.name + "-config.json")
    config = dict(schema=1, camera_rgb=ref(camera_path), source_receipt=ref(source_receipt),
                  width=int(width), height=int(height), active_origin_xy=list(active_origin_xy),
                  units="normalized-camera-RGB", development_receipt=ref(development_receipt),
                  out_dir=str(out_dir), expected_executable_sha256=executable["sha256"],
                  parity_reference=parity_reference)
    save(config_path, config)
    command = [str(exe), str(config_path)]
    before = [snapshot(p) for p in (camera_path, source_receipt, development_receipt, renderer_binding, exe, config_path)]
    stdout = out_dir.with_name(out_dir.name + "-stdout.txt")
    stderr = out_dir.with_name(out_dir.name + "-stderr.txt")
    start = time.perf_counter()
    with stdout.open("xb") as so, stderr.open("xb") as se:
        result = subprocess.run(command, stdout=so, stderr=se, check=False)
    process = dict(command=command, exit_code=result.returncode, wall_seconds=time.perf_counter() - start,
                   stdout=ref(stdout), stderr=ref(stderr), process_tree_bounds="inherited root-owned job")
    save(out_dir.with_name(out_dir.name + "-process.json"), process)
    require(result.returncode == 0, "native normalized-camera writer failed; outputs/logs retained")
    native = verify_native(read(out_dir / "receipt.json"), width, height, active_origin_xy)
    require(native["input_camera_rgb"]["sha256"] == config["camera_rgb"]["sha256"]
            and native["development_receipt"]["sha256"] == config["development_receipt"]["sha256"]
            and native["source_receipt"]["sha256"] == config["source_receipt"]["sha256"]
            and native["executable"]["sha256"] == executable["sha256"], "native input binding differs")
    for old in before:
        require(snapshot(old["path"]) == old, "native delivery changed retained inputs")
    return ref(out_dir / "receipt.json")


def pre_restore_guard(torch, normalized, evidence, origin):
    """Fixed independent-review mechanics bar, before the exact-site overwrite."""
    ox, oy = origin
    rows = {}
    for name, phases in (("R", ((0, 0),)), ("G", ((1, 0), (0, 1))), ("B", ((1, 1),))):
        parts = [normalized[(py - oy) % 2::2, (px - ox) % 2::2].reshape(-1) for px, py in phases]
        values = torch.cat(parts) if len(parts) > 1 else parts[0]
        peak = float(values.abs().max().item())
        rms = float((values / peak).square().mean().sqrt().item()) * peak if peak else 0.0
        observed = evidence["pre_restore"][name]
        require(observed["count"] == values.numel() and observed["units"] == "normalized-camera",
                "pre-restoration population/units differ")
        max_limit, rms_limit = 3e-6 * max(1.0, peak), 6e-7 * max(1.0, rms)
        passed = observed["max_abs"] <= max_limit and observed["rms"] <= rms_limit
        rows[name] = dict(reference_known_max_abs=peak, reference_known_rms=rms, count=values.numel(),
                          observed=observed, max_limit=max_limit, rms_limit=rms_limit, passed=passed)
        del parts, values
    return dict(status="FULL_FIELD_PRE_RESTORATION_NULL", per_color=rows,
                mechanical_pass=all(v["passed"] for v in rows.values()),
                bar="max<=3e-6*max(1,known-color maxabs); RMS<=6e-7*max(1,known-color RMS)",
                scope="same fixed small-control mechanical bar, not inferred-color fidelity", quality_claim=False)


def write_tensor(path, tensor):
    """Exact little-endian float32 rows; no display conversion or resampling."""
    import numpy as np
    with Path(path).open("xb") as f:
        for y in range(0, tensor.shape[0], 128):
            array = tensor[y:y + 128].detach().cpu().contiguous().numpy()
            require(array.dtype == np.float32 and np.isfinite(array).all(), "finite f32 output required")
            f.write(np.ascontiguousarray(array, dtype="<f4").tobytes())
    return ref(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-receipt", type=Path, required=True, help="actual ordinary final-CFA MHC native receipt")
    p.add_argument("--renderer-binding", type=Path, required=True)
    p.add_argument("--null-receipt", type=Path, required=True, help="commissioned normalized-camera writer held MHC null")
    p.add_argument("--expected-completion-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists() and out.parent.is_dir(),
            "fresh workspace output directory required")
    require(ref(OPERATOR)["sha256"] == args.expected_completion_sha, "completion source differs")
    operator = load(OPERATOR, "fixed_final_cfa_completion")
    mhc = verify_mhc(args.input_receipt)
    null = verify_null(args.null_receipt, args.renderer_binding)
    require(mhc["native_dimensions"] == [6896, 4596] and mhc["active_origin_xy"] == [68, 46],
            "saved full weevil field/gauge required; use independent controls for small fields")
    require(mhc["development"] == null["development"]
            and mhc["development_receipt"]["sha256"] == null["development_receipt"]["sha256"],
            "same actual held development required")
    paths = [Path(__file__), OPERATOR, HERE / "normalized-camera-develop.rs", args.input_receipt,
             args.null_receipt, args.renderer_binding]
    paths.extend(operator.source_dependencies())
    paths.extend(bind(mhc[k]) for k in ("cfa", "input_cfa", "camera_rgb", "rgb16", "linear_rgb32",
                                       "development_receipt", "configuration", "executable"))
    paths.extend(bind(v) for v in mhc["development"]["source_bindings"])
    paths.extend(bind(null[k]) for k in ("source_receipt", "input_camera_rgb", "camera_rgb", "rgb16", "linear_rgb32",
                                       "executable", "configuration", "development_receipt"))
    paths.extend(bind(v) for v in null["parity"]["references"].values())
    null_source = read(bind(null["source_receipt"]))
    paths.extend(bind(null_source[k]) for k in ("cfa", "input_cfa", "camera_rgb", "rgb16", "linear_rgb32",
                                              "configuration", "executable", "development_receipt"))
    before = [snapshot(v) for v in dict.fromkeys(paths)]
    out.mkdir()
    save(out / "input-bindings.json", before)
    started = time.perf_counter()
    try:
        import numpy as np
        import torch
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        width, height = mhc["native_dimensions"]
        signed = np.fromfile(bind(mhc["cfa"]), dtype="<f4").reshape(height, width)
        require(np.isfinite(signed).all(), "nonfinite saved final CFA")
        cfa_path = out / "final-cfa-dn.f32le"
        shutil.copyfile(bind(mhc["cfa"]), cfa_path)
        require(ref(cfa_path)["sha256"] == mhc["cfa"]["sha256"], "signed final CFA copy differs")
        engine = operator.SpectralCompletion(torch, device_limit_bytes=8 << 30)
        tensor = torch.from_numpy(signed).to(device="cuda:0", dtype=torch.float32).contiguous()
        torch.cuda.synchronize()
        compute_start = time.perf_counter()
        completed = engine.complete(tensor, mhc["development"], physical_origin_xy=tuple(mhc["active_origin_xy"]))
        torch.cuda.synchronize()
        completion_seconds = time.perf_counter() - compute_start
        require(tuple(completed.camera_rgb.shape) == (height, width, 3)
                and tuple(completed.normalized_cfa.shape) == (height, width), "completion output shape differs")
        require(torch.equal(tensor.view(torch.int32), torch.from_numpy(signed).to(device="cuda:0").view(torch.int32)),
                "completion modified signed input bits")
        evidence = completed.evidence
        require(evidence["status"] == "COMPLETE_FINAL_CFA_SPECTRAL_COMPLETION" and evidence["complete"] is True
                and evidence["height"] == height and evidence["width"] == width
                and evidence["physical_origin_xy"] == mhc["active_origin_xy"]
                and evidence["camera_units"] == "normalized-camera-RGB" and evidence["camera_layout"] == "HWC"
                and evidence["final_color_completion_calls"] == 1
                and evidence["source_demosaic_calls"] == evidence["MHC_calls"] == evidence["remosaic_calls"] == evidence["RAW_reads"] == 0
                and evidence["diagnostic_foil"] is None and evidence["known_sites_restored_bit_exact"] is True
                and evidence["quality_claim"] is False and evidence["photographic_admission"] is False,
                "actual completion path/units/claims differ")
        camera = write_tensor(out / "camera-rgb-normalized.f32le", completed.camera_rgb)
        normalized = write_tensor(out / "normalized-cfa.f32le", completed.normalized_cfa)
        engine_record = engine.metadata(strict=True)
        require(engine_record["source_sha256"] == args.expected_completion_sha
                and engine_record["bindings_unchanged"] is True and engine_record["completed_fields"] == 1,
                "actual completion runtime/source count differs")
        completion = dict(schema=1, status="COMPLETE_FINAL_CFA_COLOR_OPERATOR_FIELD", complete=True,
            source_mhc_receipt=ref(args.input_receipt), cfa=ref(cfa_path), normalized_cfa=normalized, camera_rgb=camera,
            native_dimensions=[width, height], active_origin_xy=mhc["active_origin_xy"],
            development_receipt=mhc["development_receipt"], operator_source=ref(OPERATOR),
            evidence=evidence, engine=engine_record,
            final_completion_stages=1, source_demosaic_calls=0, remosaic_calls=0,
            completion_seconds=completion_seconds, signed_input_unchanged=True,
            quality_claim=False, photographic_admission=False, RAW_reads=0)
        save(out / "completion.json", completion)
        null_guard = pre_restore_guard(torch, completed.normalized_cfa, evidence, tuple(mhc["active_origin_xy"]))
        save(out / "pre-restore-null.json", null_guard)
        require(null_guard["mechanical_pass"], "full-field pre-restoration null failed; finite fields retained")
        del completed, tensor, signed
        torch.cuda.empty_cache()
        native = develop_camera(camera_path=camera["path"], width=width, height=height,
            active_origin_xy=mhc["active_origin_xy"], source_receipt=out / "completion.json",
            development_receipt=bind(mhc["development_receipt"]), renderer_binding=args.renderer_binding,
            out_dir=out / "native")
        developed = read(native["path"])
        require(developed["material_metadata"] == mhc["material_metadata"]
                and developed["linear_material_metadata"] == mhc["linear_material_metadata"],
                "paired final development material differs")
        for old in before:
            require(snapshot(old["path"]) == old, "saved source bytes/metadata changed")
        receipt = dict(schema=1, status="COMPLETE_SAVED_FINAL_CFA_COLOR", complete=True,
            mhc_reference=ref(args.input_receipt), null_reference=ref(args.null_receipt), completion=ref(out / "completion.json"),
            native=native, cfa=ref(cfa_path), normalized_cfa=normalized, camera_rgb=camera,
            pre_restore_null=ref(out / "pre-restore-null.json"), pre_restore_null_pass=True,
            native_dimensions=[width, height], active_origin_xy=mhc["active_origin_xy"],
            input_bindings=ref(out / "input-bindings.json"), inputs_unchanged=True, entire_output=True,
            final_completion_stages=1, writer_completion_stages=0, RAW_reads=0,
            development_unchanged=True, quality_claim=False, photographic_admission=False,
            elapsed_seconds=time.perf_counter() - started,
            scope="saved final-CFA comparison only; root owns full299 source/job qualification; no new fusion or RAW reads")
        save(out / "receipt.json", receipt)
        print(json.dumps(dict(status=receipt["status"], native=native), allow_nan=False), flush=True)
    except BaseException as error:
        save(out / "failure.json", dict(status="SAVED_FINAL_CFA_COLOR_FAILED", error=repr(error),
            traceback=traceback.format_exc(), partial_outputs_preserved=True, quality_claim=False, photographic_admission=False))
        raise


if __name__ == "__main__":
    main()

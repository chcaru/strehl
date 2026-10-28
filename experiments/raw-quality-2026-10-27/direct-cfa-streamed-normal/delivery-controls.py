"""Independent small final-RGB integration/native-development controls; root runs."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DELIVERY = HERE / "delivery.py"
CPU = HERE.parent / "joint-cfa-local-fit/band-residual/sensor-operator.py"
GPU = HERE.parent / "direct-cfa-forward-gpu/measurement-gpu.py"
EXAMPLE = ROOT / "crates/strehl-cli/examples/direct-rgb-develop.rs"
EXPORT = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-tiff-export/receipt.json"
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-ca-off"
RGB = BASE / "stack-master.tiff"
LINEAR = BASE / "linear-master.tiff"
LIMIT = 8 << 30
BARS = dict(normalized_max=1e-5, normalized_rms=2e-6, neutral_max_channel_spread_codes=2)
PINNED = {
    DELIVERY: "c59c7f6a5f218f8809de43e4315ff88f5c5cd7a124826d016da3b75563b83b3b",
    CPU: "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac",
    GPU: "8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84",
    EXPORT: "461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0",
    RGB: "5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655",
    LINEAR: "8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1 << 20), b""):
            h.update(data)
    return dict(path=str(path), sha256=h.hexdigest(), bytes=path.stat().st_size)


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    return module


def bind(value):
    require(set(value) == {"path", "sha256", "bytes"}, "strict executable/file binding required")
    actual = ref(value["path"])
    require(actual["sha256"] == value["sha256"] and actual["bytes"] == value["bytes"],
            "bound file differs: " + value["path"])
    return Path(actual["path"])


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def differences(t, actual, expected):
    a = actual.detach().cpu().contiguous()
    e = expected.detach().cpu().contiguous()
    require(a.dtype == e.dtype == t.float32 and a.shape == e.shape, "same-shape f32 comparisons required")
    require(bool(t.isfinite(a).all() & t.isfinite(e).all()), "nonfinite delivery")
    delta = a - e
    maximum = float(delta.abs().max())
    rms = float(t.sqrt(t.mean(delta * delta)))
    scale_max = max(1., float(e.abs().max()))
    scale_rms = max(1., float(t.sqrt(t.mean(e * e))))
    nm, nr = maximum / scale_max, rms / scale_rms
    return dict(max_abs_dn=maximum, rms_dn=rms, reference_max_scale=scale_max,
                reference_rms_scale=scale_rms, normalized_max=nm, normalized_rms=nr,
                pass_=nm <= BARS["normalized_max"] and nr <= BARS["normalized_rms"])


def write_array(np, path, array):
    value = np.ascontiguousarray(array, dtype="<f4")
    require(bool(np.isfinite(value).all()), "finite f32 camera master required")
    with Path(path).open("xb") as f:
        value.tofile(f)
    return ref(path)


def native_render(np, tifffile, Image, out, label, camera, development, executable, icc_expected):
    folder = out / label
    folder.mkdir()
    camera = np.ascontiguousarray(camera, dtype="<f4")
    camera_ref = write_array(np, folder / "camera-rgb-dn.f32le", camera)
    camera_stat = (Path(camera_ref["path"]).stat().st_size, Path(camera_ref["path"]).stat().st_mtime_ns)
    delivery = dict(schema=1, status="COMPLETE_REFERENCE_CELL_CAMERA_RGB", complete=True,
        camera_rgb=camera_ref, shape=list(camera.shape), dtype="<f4", channels=["R", "G", "B"],
        units="black-subtracted-camera-DN", demosaic_calls=0, remosaic_calls=0,
        entire_output=True, commissioning_panel=True, quality_claim=False, photographic_admission=False)
    save(folder / "delivery-receipt.json", delivery)
    save(folder / "development.json", development)
    config = dict(schema=1, camera_rgb=camera_ref, delivery_receipt=ref(folder / "delivery-receipt.json"),
        development_receipt=ref(folder / "development.json"), out_dir=str(folder / "native"),
        expected_executable_sha256=executable["sha256"])
    save(folder / "config.json", config)
    command = [str(bind(executable)), str(folder / "config.json")]
    env = os.environ.copy()
    removed = sorted(k for k in env if k.startswith("STREHL_"))
    for key in removed:
        env.pop(key)
    env["RAYON_NUM_THREADS"] = "4"
    start = time.perf_counter()
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=45, check=False)
    (folder / "stdout.log").write_bytes(completed.stdout)
    (folder / "stderr.log").write_bytes(completed.stderr)
    save(folder / "invocation.json", dict(command=command, expected_exit=0, actual_exit=completed.returncode,
        seconds=time.perf_counter()-start, removed_environment=removed, workers=4))
    require(completed.returncode == 0, "native renderer failed: " + label)
    receipt_path = folder / "native/receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt["status"] == "COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT" and receipt["complete"]
        and receipt["pixel_readback_exact"] and receipt["retained_input_bytes_and_metadata_unchanged"]
        and receipt["demosaic_calls"] == receipt["remosaic_calls"] == receipt["RAW_reads"] == 0
        and receipt["tone_measured_from_output"] is False and receipt["quality_claim"] is False
        and receipt["photographic_admission"] is False and receipt["development"] == development,
        "native producing contract changed")
    require(receipt["negative_camera_samples_preserved_until_developer"] == int((camera < 0).sum()),
            "native negative input census differs")
    master = bind(receipt["rgb16"])
    with tifffile.TiffFile(master) as tf:
        require(len(tf.pages) == 1, "single complete native page required")
        page = tf.pages[0]
        pixels = page.asarray()
        icc = bytes(page.tags[34675].value)
        description = page.description
    require(pixels.dtype == np.uint16 and pixels.shape == camera.shape, "native full RGB16 extent/type differs")
    pixel_sha = hashlib.sha256(pixels.astype("<u2", copy=False).tobytes()).hexdigest()
    icc_sha = hashlib.sha256(icc).hexdigest()
    require(pixel_sha == receipt["rgb16_pixels_sha256"], "independent full pixel readback differs")
    require(icc == icc_expected and icc_sha == receipt["icc_sha256"], "native ICC differs from held baseline")
    require(description == receipt["image_description"], "native description readback differs")
    require(receipt["native_dimensions"] == [camera.shape[1], camera.shape[0]], "receipt dimensions differ")
    require(ref(camera_ref["path"]) == camera_ref and camera_stat ==
            (Path(camera_ref["path"]).stat().st_size, Path(camera_ref["path"]).stat().st_mtime_ns),
            "signed camera input was altered")
    readback = np.fromfile(camera_ref["path"], dtype="<f4").reshape(camera.shape)
    require(np.array_equal(readback.view(np.uint32), camera.view(np.uint32)), "signed camera bits changed")
    preview = ((pixels.astype(np.uint32) + 128) // 257).astype(np.uint8)
    Image.fromarray(preview, "RGB").save(folder / "complete.png", icc_profile=icc)
    interior = pixels[4:-4, 4:-4].astype(np.int32)
    spread = int((interior.max(axis=2) - interior.min(axis=2)).max())
    neutral = spread <= BARS["neutral_max_channel_spread_codes"]
    result = dict(label=label, renderer_receipt=ref(receipt_path), camera_rgb=camera_ref,
        complete_master=ref(master), complete_png=ref(folder / "complete.png"),
        pixel_readback_exact=True, signed_input_bit_exact=True,
        negative_samples=int((camera < 0).sum()), icc_sha256=icc_sha,
        interior_xywh=[4, 4, camera.shape[1]-8, camera.shape[0]-8],
        maximum_channel_spread_codes=spread, neutral_pass=neutral)
    save(folder / "independent-readback.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--renderer-binding", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(), "fresh workspace outputs required")
    out.mkdir(parents=True)
    started = time.perf_counter()
    state = dict(status="STARTED", all_cases_completed=False, mechanical_pass=False,
                 quality_claim=False, photographic_admission=False, RAW_reads=0, bars=BARS)
    try:
        binding_path = args.renderer_binding.resolve()
        executable = json.loads(binding_path.read_text(encoding="utf-8"))
        executable_path = bind(executable)
        paths = list(PINNED) + [Path(__file__), HERE / "delivery-controls-plan.md", EXAMPLE,
            binding_path, executable_path, ROOT / "crates/strehl-cli/src/image_out.rs",
            ROOT / "crates/strehl-core/src/color.rs", HERE.parent / "dual-tree-cfa-gpu/ordered-fir.py"]
        before = [ref(p) for p in paths]
        stats = [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths]
        for item in before:
            expected = PINNED.get(Path(item["path"]))
            require(expected is None or expected == item["sha256"], "pinned delivery/development source changed")
        save(out / "bindings.json", before)
        import numpy as np
        import torch as t
        import tifffile
        from PIL import Image
        t.set_num_threads(4)
        t.set_num_interop_threads(1)
        t.backends.cuda.matmul.allow_tf32 = False
        t.backends.cudnn.allow_tf32 = False
        require(t.cuda.is_available(), "CUDA required")
        t.cuda.set_device(0)
        total = t.cuda.get_device_properties(0).total_memory
        require(total >= LIMIT, "fixed device budget unavailable")
        t.cuda.set_per_process_memory_fraction(LIMIT / total, 0)
        t.cuda.reset_peak_memory_stats(0)
        save(out / "environment.json", dict(torch=t.__version__, cuda=t.version.cuda, python=sys.version,
            numpy=np.__version__, tifffile=tifffile.__version__, device=t.cuda.get_device_name(0),
            workers=4, matmul_tf32=False, cudnn_tf32=False, autocast=False, allocation_limit_bytes=LIMIT))
        export = json.loads(EXPORT.read_text(encoding="utf-8"))
        require(export["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED"
                and export["levels"] == [512., 15360.], "held sensor metadata changed")
        with tifffile.TiffFile(LINEAR) as tf:
            require(len(tf.pages) == 1 and tf.pages[0].shape == (4596, 6896, 3)
                    and tf.pages[0].dtype == np.float32, "held linear master metadata differs")
            description = tf.pages[0].description
        lines = [line[len("DisplayBaseline: "):] for line in description.splitlines()
                 if line.startswith("DisplayBaseline: ")]
        require(len(lines) == 1, "exact held DisplayBaseline required")
        display = json.loads(lines[0])
        require(set(display) == {"black", "white", "contrast", "exposure_gain"}
                and bits(display["exposure_gain"]) == bits(1.), "held display contract changed")
        with tifffile.TiffFile(RGB) as tf:
            require(len(tf.pages) == 1 and tf.pages[0].shape == (4596, 6896, 3)
                    and tf.pages[0].dtype == np.uint16, "held viewing master header differs")
            baseline_icc = bytes(tf.pages[0].tags[34675].value)
        require(bool(baseline_icc), "held baseline ICC absent")
        development = dict(schema=1, levels_bits=[bits(v) for v in export["levels"]],
            wb_bits=export["wb_bits"], xyz_to_cam_bits=export["xyz_to_cam_bits"],
            tone_bits=[bits(display[k]) for k in ("black", "white", "contrast")], exposure_bits=bits(1.),
            source_bindings=[ref(EXPORT), ref(LINEAR), ref(RGB)])
        save(out / "held-development.json", development)
        cpu = load(CPU, "delivery_controls_frozen_cpu")
        delivery = load(DELIVERY, "delivery_controls_producer")
        runtime = []
        def integrate_bound(label, latent, origin, rectangle):
            # Same constructor and integrate call as the frozen integrate_rgb
            # wrapper, retaining its actual engine for runtime provenance only.
            engine = delivery.ReferenceDelivery(t, tuple(latent.shape[:2]), origin, LIMIT)
            initial = copy.deepcopy(engine.metadata())
            result = engine.integrate(latent, rectangle)
            final = engine.metadata()
            record = dict(label=label, initial=initial, final=final)
            save(out / ("runtime-" + label + ".json"), record)
            runtime.append(record)
            return result
        wb = np.asarray([f32(v) for v in development["wb_bits"]], dtype=np.float32)
        sensor_range = np.float32(15360 - 512)
        cases = []
        arrays = {}
        with t.inference_mode(), t.autocast(device_type="cuda", enabled=False):
            for name, h, w in (("constants", 24, 32), ("signed-structure", 31, 47), ("neutral", 23, 37)):
                latent = np.empty((h+16, w+16, 3), dtype=np.float32)
                if name == "constants":
                    latent[:] = np.asarray([-192., 1200., 3700.], dtype=np.float32)
                elif name == "neutral":
                    latent[:] = np.float32(.12) * sensor_range / wb
                else:
                    y, x = np.mgrid[-8:h+8, -8:w+8].astype(np.float32)
                    for c in range(3):
                        latent[..., c] = (np.float32(300 + 190*c)
                            + np.float32(1800 + 200*c)*np.sin(np.float32(.19+.07*c)*x + np.float32(.13-.03*c)*y)
                            + np.float32(700)*np.cos(np.float32(.61-.05*c)*x - np.float32(.31+.09*c)*y))
                folder = out / (name + "-integration")
                folder.mkdir()
                latent_ref = write_array(np, folder / "latent.f32le", latent)
                config = cpu.Config((h, w), (.2,)*4, (1.,)*4, (512.,)*4, 15360)
                expected = cpu.integrate_reference(t.from_numpy(latent), config)
                actual = integrate_bound(name, t.from_numpy(latent).to("cuda:0"), (-8, -8), (0, 0, w, h))
                comparison = differences(t, actual, expected)
                camera = actual.detach().cpu().numpy().astype("<f4", copy=False)
                arrays[name] = camera.copy()
                entry = dict(name=name, output_shape=[h, w, 3], latent_shape=list(latent.shape),
                    reference_origin_xy=[-8, -8], output_xywh=[0, 0, w, h], latent=latent_ref,
                    cpu=write_array(np, folder / "cpu-camera-rgb-dn.f32le", expected.numpy()),
                    gpu=write_array(np, folder / "gpu-camera-rgb-dn.f32le", camera), comparison=comparison)
                if name == "constants":
                    target = t.from_numpy(np.broadcast_to(latent[0, 0], (h, w, 3)).copy())
                    entry["known_constant"] = differences(t, actual, target)
                if name == "signed-structure":
                    gpu_latent = t.from_numpy(latent).to("cuda:0")
                    wrong_origin = integrate_bound("wrong-origin", gpu_latent, (-7, -8), (0, 0, w, h))
                    wrong_channel = integrate_bound("wrong-channel", gpu_latent[..., [2, 1, 0]].contiguous(),
                                                    (-8, -8), (0, 0, w, h))
                    entry["wrong_origin"] = differences(t, wrong_origin, expected)
                    entry["wrong_channel"] = differences(t, wrong_channel, expected)
                    entry["wrong_origin_output"] = write_array(np, folder / "wrong-origin.f32le", wrong_origin.cpu().numpy())
                    entry["wrong_channel_output"] = write_array(np, folder / "wrong-channel.f32le", wrong_channel.cpu().numpy())
                save(folder / "receipt.json", entry)
                cases.append(entry)
        save(out / "integration.json", cases)
        integration_pass = all(v["comparison"]["pass_"] for v in cases)
        integration_pass &= cases[0]["known_constant"]["pass_"]
        integration_pass &= not cases[1]["wrong_origin"]["pass_"] and not cases[1]["wrong_channel"]["pass_"]
        require(integration_pass, "fixed integration fidelity or active foil failed")
        native = [native_render(np, tifffile, Image, out, name, arrays[name], development,
                                executable, baseline_icc) for name in ("constants", "signed-structure", "neutral")]
        bad_wb = copy.deepcopy(development)
        bad_wb["wb_bits"] = [bits(1.)]*3
        native.append(native_render(np, tifffile, Image, out, "wrong-wb", arrays["neutral"], bad_wb,
                                    executable, baseline_icc))
        native.append(native_render(np, tifffile, Image, out, "black-pedestal-unit-error",
                                    arrays["neutral"] + np.float32(512), development, executable, baseline_icc))
        save(out / "native.json", native)
        require(native[2]["neutral_pass"], "positive native neutral failed fixed2-code guard")
        require(not native[3]["neutral_pass"] and not native[4]["neutral_pass"], "native WB/unit foils did not fail neutral guard")
        require(native[1]["negative_samples"] > 0 and native[1]["signed_input_bit_exact"], "signed structured input not preserved")
        after = [ref(p) for p in paths]
        require(before == after and stats == [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths],
                "bound source/metadata/executable changed")
        state.update(status="COMPLETE_DIRECT_CFA_DELIVERY_CONTROLS", all_cases_completed=True,
            mechanical_pass=True, complete=True, integration=cases, native=native, runtime=runtime,
            bound_inputs_unchanged=True, gpu_peak_allocated_bytes=t.cuda.max_memory_allocated(0),
            gpu_peak_reserved_bytes=t.cuda.max_memory_reserved(0),
            elapsed_seconds=time.perf_counter()-started,
            limitations=["Neutral fidelity does not qualify off-neutral camera color characterization.",
                        "Small complete consumer panels do not establish optical/detail/noise quality.",
                        "No baseline photograph was reconstructed or compared here."])
        save(out / "receipt.json", state)
    except BaseException as error:
        state.update(status="REFUSED_DIRECT_CFA_DELIVERY_CONTROLS", error_type=type(error).__name__,
                     error=str(error), traceback=traceback.format_exc(), elapsed_seconds=time.perf_counter()-started)
        save(out / "failure.json", state)
        raise


if __name__ == "__main__":
    main()

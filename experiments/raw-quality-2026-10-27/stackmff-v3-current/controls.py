"""Fixed live V3 mechanics and small image stresses; never a photographic admission."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
MAX_ERROR = 1e-4
RMS_ERROR = 1e-5


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def ref(path):
    path = Path(path).resolve(strict=True)
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def json_default(value):
    import numpy as np
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def save_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False, default=json_default)
        stream.write("\n")


def difference(a, b):
    import numpy as np
    require(a.shape == b.shape, "comparison dimensions")
    d = a.astype(np.float64) - b.astype(np.float64)
    finite = bool(np.isfinite(d).all())
    maximum = float(np.max(np.abs(d))) if finite else None
    rms = float(np.sqrt(np.mean(d * d))) if finite else None
    return dict(finite=finite, max=maximum, rms=rms,
                pass_bound=finite and maximum <= MAX_ERROR and rms <= RMS_ERROR)


def u16(a):
    import numpy as np
    return np.clip(np.rint(a), 0, 65535).astype(np.uint16)


def save_image(out, name, rgb):
    import numpy as np
    import tifffile
    from PIL import Image, ImageCms
    require(rgb.dtype == np.uint16 and rgb.ndim == 3 and rgb.shape[2] == 3, "RGB16 display input")
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    master, preview = out / (name + ".tiff"), out / (name + ".png")
    tifffile.imwrite(master, rgb, photometric="rgb", metadata=None,
                     extratags=[(34675, 7, len(icc), icc, False)])
    display = ((rgb.astype(np.uint32) + 128) // 257).astype(np.uint8)
    Image.fromarray(display).save(preview, icc_profile=icc)
    return dict(master=ref(master), display=ref(preview), shape=list(rgb.shape),
                transform="(RGB16+128)//257", resized=False)


def fixture_images():
    """Deterministic image-selection stresses; not an optical forward model."""
    import cv2
    import numpy as np
    h = w = 192
    y, x = np.mgrid[:h, :w].astype(np.float32)
    truth = np.full((h, w, 3), 18000.0, np.float32)
    top = y < 96
    # Near-region fine bars and bright/dark strands have no fitted template.
    fine = (1200 * np.sin(2 * np.pi * x / 7) + 900 * np.cos(2 * np.pi * (x + y) / 11)) * top
    truth += fine[:, :, None]
    hair_a = (np.abs(y - (.18 * x + 30)) < .7) & top
    hair_b = (np.abs(y - (-.12 * x + 73)) < .8) & top
    truth[hair_a] += 14000
    truth[hair_b] -= 11000
    # Separate far-region broad ridges, with independent color texture.
    coarse = 5500 * np.sin(2 * np.pi * x / 39) * (~top)
    truth += coarse[:, :, None]
    color_area = (x > 96) & (y > 100) & (y < 151)
    truth[:, :, 0] += color_area * (3500 * np.cos(2 * np.pi * x / 6))
    truth[:, :, 1] += color_area * (80 * np.sin(2 * np.pi * y / 13))
    truth[:, :, 2] += color_area * (4000 * np.sin(2 * np.pi * (x - y) / 8))
    glint = (x - 48) ** 2 + (y - 163) ** 2 <= 2.2 ** 2
    truth[glint] = (62000, 63000, 61000)
    truth[(x > 73) & (x < 76) & (y > 104)] = (7000, 10000, 8000)
    truth = u16(truth)
    rng = np.random.default_rng(506272)
    inputs = []
    sigma_near = (2.4, 0.0, 1.2, 2.2, 3.0)
    sigma_far = (3.0, 2.2, 1.2, 0.0, 2.4)
    for near_sigma, far_sigma in zip(sigma_near, sigma_far):
        def blurred(sigma):
            return truth.astype(np.float32) if sigma == 0 else cv2.GaussianBlur(
                truth.astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_REFLECT_101)
        source = np.where(top[:, :, None], blurred(near_sigma), blurred(far_sigma))
        source += rng.normal(0, 32, source.shape).astype(np.float32)
        inputs.append(u16(source))
    flat_truth = np.broadcast_to(np.array([16384, 24576, 32768], np.uint16), (h, w, 3)).copy()
    flat_rng = np.random.default_rng(506271)
    flats = u16(flat_truth[None].astype(np.float32) + flat_rng.normal(0, 128, (5, h, w, 3)))
    regions = {"near-fine-hairs": (8, 8, 176, 80), "far-coarse": (8, 104, 80, 80),
               "independent-color": (104, 104, 80, 40), "glint": (24, 144, 48, 40),
               "depth-boundary": (8, 88, 176, 16)}
    return flat_truth, flats, truth, np.stack(inputs), regions


def large_texture():
    import cv2
    import numpy as np
    y, x = np.mgrid[:756, :760].astype(np.float32)
    texture = np.empty((756, 760, 3), np.float32)
    texture[:, :, 0] = 26000 + 6500 * np.sin((x + y) * .29) + 2400 * np.cos(x * .071)
    texture[:, :, 1] = 28000 + 6000 * np.cos((2 * x - y) * .17) + 2100 * np.sin(y * .103)
    texture[:, :, 2] = 24000 + 7000 * np.sin((x - 2 * y) * .13) + 2900 * np.cos((x + y) * .043)
    blurry = cv2.GaussianBlur(texture, (0, 0), 2.1, borderType=cv2.BORDER_REFLECT_101)
    split = ((x // 96 + y // 96) % 2 == 0)[:, :, None]
    return np.stack([u16(np.where(split, texture, blurry)), u16(np.where(split, blurry, texture))])


def image_quality(candidate, uniform, truth, regions, multiplier):
    import numpy as np
    result = {}
    for name, (x, y, w, h) in regions.items():
        target = truth[y:y+h, x:x+w].astype(np.float64)
        a = candidate[y:y+h, x:x+w].astype(np.float64) - target
        b = uniform[y:y+h, x:x+w].astype(np.float64) - target
        rmse = np.sqrt(np.mean(a * a, axis=(0, 1)))
        reference = np.sqrt(np.mean(b * b, axis=(0, 1)))
        result[name] = dict(xywh=[x, y, w, h], rmse_rgb_codes=rmse,
                            uniform_rmse_rgb_codes=reference, limit_rgb_codes=multiplier * reference + 1,
                            mean_bias_rgb_codes=a.mean(axis=(0, 1)),
                            pass_guard=bool(np.all(rmse <= multiplier * reference + 1)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, upstream = args.out.resolve(), args.upstream.resolve(strict=True)
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(), "fresh workspace output required")
    out.mkdir(parents=True, exist_ok=False)
    import cv2
    import numpy as np
    import torch
    started = time.monotonic()
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    require(torch.cuda.is_available(), "fixed CUDA comparison requires available GPU")
    total_gpu = torch.cuda.get_device_properties(0).total_memory
    allocator_limit = min(24 * 1024**3, total_gpu)
    torch.cuda.set_per_process_memory_fraction(allocator_limit / total_gpu, 0)
    torch.cuda.reset_peak_memory_stats()
    bound_paths = [AREA / "model-adapter.py", AREA / "input-bridge.py", Path(__file__),
                   AREA / "comparison-protocol.md", AREA / "upstream-manifest.json"]
    bound_paths += sorted(p for p in upstream.rglob("*") if p.is_file())
    before = [ref(p) for p in bound_paths]
    adapter = load_module("stackmff_current_model_adapter", AREA / "model-adapter.py")
    bridge = load_module("stackmff_current_input_bridge", AREA / "input-bridge.py")
    coordinate = bridge.coordinate_controls()
    save_json(out / "coordinate-controls.json", coordinate)
    mechanical = {"coordinate-controls": coordinate["status"] == "INPUT_BRIDGE_COORDINATES_VERIFIED"}
    observations, images = {}, {}
    model = adapter.load_model(upstream, device="cuda")
    mechanical["f32-eval-defaults"] = (not model.model.training and
        all(p.dtype == torch.float32 for p in model.model.parameters()) and tuple(model.model.ms_scales) == (1.0, .75)
        and model.model.cur_K == 1 and not model.model.adaptive)
    official = load_module("stackmff_current_official_fuse", upstream / "fuse.py")

    def record_result(name, result, source_core):
        p, floating, fused = result["probabilities"], result["fused_float"], result["fused"]
        require(p.shape == source_core.shape[:3] and fused.shape == source_core.shape[1:]
                and floating.shape == fused.shape, "prediction dimensions")
        valid = bool(np.isfinite(p).all() and np.isfinite(floating).all())
        if not valid:
            np.save(out / (name + "-nonfinite-probabilities.npy"), p, allow_pickle=False)
            np.save(out / (name + "-nonfinite-float.npy"), floating, allow_pickle=False)
            save_json(out / (name + "-nonfinite-refusal.json"), dict(finite=False, quality_claim=False))
            raise RuntimeError("nonfinite prediction retained: " + name)
        sums = float(np.max(np.abs(p.sum(axis=0, dtype=np.float32) - 1))) if valid else None
        bounds = valid and float(p.min()) >= -1e-7 and float(p.max()) <= 1 + 1e-7
        independent = np.sum(p[:, :, :, None] * source_core.astype(np.float32), axis=0, dtype=np.float32)
        float_difference = difference(floating, independent / np.float32(65535))
        writer_error = int(np.max(np.abs(fused.astype(np.int32) - u16(independent).astype(np.int32))))
        minimum, maximum = source_core.min(axis=0).astype(np.int32), source_core.max(axis=0).astype(np.int32)
        hull = bool(np.all(fused.astype(np.int32) >= minimum - 1) and np.all(fused.astype(np.int32) <= maximum + 1))
        value = dict(finite=valid, probability_min=float(p.min()), probability_max=float(p.max()),
                     normalization_max_error=sums, independent_composer=float_difference,
                     writer_max_codes=writer_error, source_hull=hull, metadata=result["metadata"])
        mechanical[name + "-valid-fusion"] = valid and bounds and sums <= 1e-5 and float_difference["pass_bound"] and writer_error <= 1 and hull
        observations[name] = value
        images[name] = save_image(out, name, fused)
        np.save(out / (name + "-probabilities.npy"), p, allow_pickle=False)
        np.save(out / (name + "-float.npy"), floating, allow_pickle=False)
        save_json(out / (name + "-observation.json"), value)
        return result

    flat_truth, flats, truth, structured, regions = fixture_images()
    inputs_before = {name: hashlib.sha256(value.tobytes()).hexdigest() for name, value in
                     (("flat", flats), ("structured", structured))}
    images["flat-truth"] = save_image(out, "flat-truth", flat_truth)
    images["structured-truth"] = save_image(out, "structured-truth", truth)
    for name, stack in (("flat", flats), ("structured", structured)):
        for index, source in enumerate(stack):
            images[f"{name}-source-{index}"] = save_image(out, f"{name}-source-{index}", source)
        np.save(out / (name + "-input-rgb16.npy"), stack, allow_pickle=False)

    # Constant and flat controls precede any sharpness/structure result.
    constant = np.broadcast_to(np.array([16384, 24576, 32768], np.uint16), (299, 64, 64, 3)).copy()
    const_result = record_result("constant299", adapter.predict_full(model, constant, return_probs=True), constant)
    mechanical["constant299-fidelity"] = int(np.max(np.abs(const_result["fused"].astype(np.int32) - constant[0].astype(np.int32)))) <= 1
    del const_result, constant
    flat_result = record_result("flat-candidate", adapter.predict_full(model, flats, return_probs=True), flats)
    flat_uniform = u16(flats.astype(np.float32).mean(axis=0))
    images["flat-uniform"] = save_image(out, "flat-uniform", flat_uniform)
    flat_quality = image_quality(flat_result["fused"], flat_uniform, flat_truth, {"whole-flat": (0, 0, 192, 192)}, 1.10)
    flat_quality["whole-flat"]["bias_pass"] = bool(np.all(np.abs(flat_quality["whole-flat"]["mean_bias_rgb_codes"]) <= 32))

    identical = np.repeat(truth[None], 3, axis=0)
    identical_result = record_result("identical3", adapter.predict_full(model, identical, return_probs=True), identical)
    mechanical["identical3-fidelity"] = int(np.max(np.abs(identical_result["fused"].astype(np.int32) - truth.astype(np.int32)))) <= 1
    del identical_result, identical
    result = record_result("structured-candidate", adapter.predict_full(model, structured, return_probs=True), structured)
    uniform = u16(structured.astype(np.float32).mean(axis=0))
    images["structured-uniform"] = save_image(out, "structured-uniform", uniform)
    structured_quality = image_quality(result["fused"], uniform, truth, regions, 1.05)

    # Independent direct official inference/composer; no altered network path.
    bgr = [np.ascontiguousarray(source[:, :, ::-1]) for source in structured]
    official_p = official.probabilities(model.model, bgr, torch.device("cuda"), .5)
    official_rgb = official.fuse(official_p, bgr, False)[:, :, ::-1].copy()
    official_agreement = difference(result["probabilities"], official_p)
    official_codes = int(np.max(np.abs(result["fused"].astype(np.int32) - official_rgb.astype(np.int32))))
    mechanical["official-small-path"] = official_agreement["pass_bound"] and official_codes <= 1
    observations["official-small-path"] = dict(probabilities=official_agreement, writer_max_codes=official_codes)
    images["official-structured"] = save_image(out, "official-structured", official_rgb)
    reversed_result = record_result("reversed-structured", adapter.predict_full(model, structured[::-1].copy(), return_probs=True), structured[::-1])
    order_p, order_rgb = difference(result["probabilities"], reversed_result["probabilities"][::-1]), difference(result["fused_float"], reversed_result["fused_float"])
    mechanical["source-order-equivariance"] = order_p["pass_bound"] and order_rgb["pass_bound"]
    observations["source-order"] = dict(probabilities=order_p, rgb=order_rgb)

    # Live mapping seam with deliberate nonuniform weights, independent of whether learned weights are uniform.
    tagged = np.broadcast_to(np.array([[5000, 20000, 45000], [25000, 50000, 10000], [60000, 10000, 25000]], np.uint16)[:, None, None], (3, 16, 16, 3)).copy()
    weights = np.broadcast_to(np.array([.7, .2, .1], np.float32)[:, None, None], (3, 16, 16)).copy()
    weights[:, 8:] = np.array([.1, .3, .6], np.float32)[:, None, None]
    correct_float, correct_codes = adapter.fuse_rgb16(weights, tagged)
    wrong_float, wrong_codes = adapter.fuse_rgb16(weights, tagged[[1, 2, 0]])
    expected = np.sum(weights[:, :, :, None] * tagged.astype(np.float32), axis=0, dtype=np.float32) / np.float32(65535)
    mapping_good, mapping_wrong = difference(correct_float, expected), difference(wrong_float, expected)
    mechanical["known-weight-mapping"] = mapping_good["pass_bound"] and int(np.max(np.abs(correct_codes.astype(np.int32) - u16(expected * 65535).astype(np.int32)))) <= 1
    mechanical["wrong-mapping-foil-rejected"] = not mapping_wrong["pass_bound"]
    observations["mapping"] = dict(correct=mapping_good, wrong_source_order=mapping_wrong)
    images["mapping-correct"] = save_image(out, "mapping-correct", correct_codes)
    images["mapping-wrong"] = save_image(out, "mapping-wrong", wrong_codes)

    large = large_texture()
    for index, source in enumerate(large):
        images[f"context-source-{index}"] = save_image(out, f"context-source-{index}", source)
    full = record_result("context-full", adapter.predict_full(model, large, return_probs=True), large)
    comparisons = {}
    for name, rect, bad in (("center", (256, 256, 256, 256), False),
                             ("outer-edge", (512, 512, 248, 244), False),
                             ("wrong-halo", (256, 256, 256, 256), True)):
        spec = adapter.tile_spec(rect, (760, 756), **({"diagnostic_halo": 0} if bad else {}))
        rx, ry, rw, rh = spec["read_rect"]
        context = np.ascontiguousarray(large[:, ry:ry+rh, rx:rx+rw])
        x, y, w, h = rect
        tile = record_result("context-" + name, adapter.predict_tile(model, context, spec, return_probs=True), large[:, y:y+h, x:x+w])
        p_delta = difference(tile["probabilities"], full["probabilities"][:, y:y+h, x:x+w])
        rgb_delta = difference(tile["fused_float"], full["fused_float"][y:y+h, x:x+w])
        comparisons[name] = dict(spec=spec, probabilities=p_delta, rgb=rgb_delta)
        mechanical["context-" + name] = not(p_delta["pass_bound"] and rgb_delta["pass_bound"]) if bad else p_delta["pass_bound"] and rgb_delta["pass_bound"]
    observations["context-comparisons"] = comparisons
    save_json(out / "context-comparisons.json", comparisons)
    after_inputs = {name: hashlib.sha256(value.tobytes()).hexdigest() for name, value in
                    (("flat", flats), ("structured", structured))}
    mechanical["input-arrays-unchanged"] = after_inputs == inputs_before
    after = [ref(p) for p in bound_paths]
    mechanical["source-bindings-unchanged"] = before == after
    torch.cuda.synchronize()
    quality_pass = (all(row["pass_guard"] for row in flat_quality.values())
                    and flat_quality["whole-flat"]["bias_pass"]
                    and all(row["pass_guard"] for row in structured_quality.values()))
    receipt = dict(status="COMPLETE_CURRENT_STACKMFF_V3_CONTROLS", complete=True,
                   mechanical_pass=all(mechanical.values()), mechanical_checks=mechanical,
                   quality_pass=quality_pass, flat_quality=flat_quality, structured_quality=structured_quality,
                   observations=observations, complete_images=images, source_bindings=before,
                   input_array_hashes=inputs_before, source_bindings_unchanged=before == after,
                   fixed_scales=[1, .75], sigma=.5, mode="weighted", torch_version=torch.__version__,
                   cuda_version=torch.version.cuda, opencv_version=cv2.__version__, numpy_version=np.__version__,
                   tf32_matmul=torch.backends.cuda.matmul.allow_tf32, tf32_cudnn=torch.backends.cudnn.allow_tf32,
                   gpu_name=torch.cuda.get_device_name(0), gpu_allocator_cap_bytes=allocator_limit,
                   peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(), peak_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
                   elapsed_seconds=time.monotonic()-started, torch_workers=4, opencv_workers=1,
                   command=getattr(sys, "orig_argv", [sys.executable, *sys.argv]), RAW_reads=0,
                   actual_photo_reads=0, quality_claim=False, photographic_admission=False, admission=False)
    save_json(out / "receipt.json", receipt)
    require(receipt["mechanical_pass"], "mechanical control failure; receipt and complete panels retained")
    print(json.dumps(dict(status=receipt["status"], mechanical_pass=True, quality_pass=quality_pass)))


if __name__ == "__main__":
    main()

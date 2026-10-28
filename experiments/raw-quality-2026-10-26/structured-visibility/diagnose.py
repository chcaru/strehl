"""One saved-alpha counterfactual; no fit, original RAW decode, or quality claim."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"

HERE = Path(__file__).resolve().parent
SOURCE = Path("C:/dev/blog/death-of-software/projects/strehl")
EXP = SOURCE / "experiments"
OLD = EXP / "marigold-constrained-raw"
RUN = OLD / "run-1"
CAP = 4 * 2**30


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), sha256=sha, bytes=path.stat().st_size)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    allowed = HERE.parents[2] / "outputs" / "raw-quality-2026-10-26"
    if out.exists() or out.parent != allowed:
        raise ValueError("Fresh direct child of workspace outputs/raw-quality-2026-10-26 required")
    pins = read(HERE / "input-pins.json")
    for row in pins:
        if ref(row["path"]) != row:
            raise ValueError("Frozen input changed: " + row["path"])
    out.mkdir(parents=True)
    started = time.monotonic()
    result = dict(status="FAILED", original_raw_reads=0, fit_steps=0,
                  full_stack_output=False, photographic_quality_admitted=False,
                  command=[sys.executable, *sys.argv], python=sys.version,
                  environment={k: v for k, v in os.environ.items() if k.startswith(("STREHL_", "OMP_", "MKL_", "OPENBLAS_", "NUMEXPR_"))})
    gpu = False
    try:
        import numpy as np
        from scipy.ndimage import convolve1d
        import torch
        import tifffile
        from PIL import Image

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        if not torch.cuda.is_available():
            raise RuntimeError("Commissioned CUDA route required; no CPU fallback")
        total = torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(CAP / total, 0)
        torch.cuda.reset_peak_memory_stats()
        gpu = True
        result.update(torch=torch.__version__, cuda=torch.version.cuda,
                      device=torch.cuda.get_device_name(0), worker_count=1)
        model = load_module("structured_visibility_frozen_model", OLD / "model.py")
        helper = load_module("structured_visibility_frozen_helpers", OLD / "run.py")
        optics = read(RUN / "optics.json")
        rows = {row["index"]: row for row in optics["rows"]}
        stage = read(EXP / "marigold-foreground-inputs/stage-1/receipt.json")
        raw = {row["index"]: row for row in stage["frames"]}
        fan = read(EXP / "marigold-fan-learned/run-1/output/receipt.json")
        frames = {row["index"]: row for row in fan["frames"]}
        points = model.aperture(optics["pupil_count"])
        if model.SIGMA != optics["common_sigma"] or model.TRAIN != (96, 112, 128, 144, 160) or model.HELD != (104, 120, 136, 152):
            raise ValueError("Frozen source split or blur changed")

        def table(index):
            row = rows[index]
            value = model.pupil.build_table(points, row["near_shift"], row["far_shift"])
            if value.metadata != row["table"]:
                raise ValueError("Pupil table does not replay saved identity")
            return value

        def sample(index):
            value, support = helper.original_sample(model, raw[index], frames[index]["native_pulls"])
            if support["minimum_latent_margin"] < optics["required_apron"]:
                raise ValueError("Saved original sample lacks optical support")
            return value

        def predict(fields, tab, samples):
            with torch.no_grad():
                n, f, a = (torch.as_tensor(fields[k], device="cuda", dtype=torch.float32) for k in ("near", "far", "alpha"))
                rgb = model.predict_rgb(n, f, a, tab)
                answer = model.sample_rgb(rgb, samples["xy"], samples["channels"]) + model.BLACK
                return answer.cpu().numpy().copy()

        def smooth(alpha):
            kernel = np.array([.25, .5, .25], np.float32)
            return convolve1d(convolve1d(alpha, kernel, axis=0, mode="nearest"), kernel, axis=1, mode="nearest")

        def rms(values):
            return float(np.sqrt(np.mean(np.asarray(values, np.float64)**2)))

        def hp(values):
            return (values - smooth(values))[2:-2, 2:-2]

        # Controls precede the saved-field intervention. Every scored sensel has
        # the full pupil/blur apron, avoiding the gauge's zero-padding exception.
        t104, s104 = table(104), sample(104)
        shape = (300, 336)
        yy, xx = np.indices(shape)
        checker = ((xx + yy) % 2).astype(np.float32)
        equal = np.full((*shape, 3), 1000, np.float32)
        flat0 = dict(near=equal, far=equal, alpha=checker)
        flat1 = dict(near=equal, far=equal, alpha=smooth(checker))
        flat_error = float(np.max(np.abs(predict(flat0, t104, s104) - predict(flat1, t104, s104))))
        assert flat_error < .02, "equal-colour null failed"
        lower = dict(near=equal*2, far=equal, alpha=np.full(shape, .25, np.float32))
        upper = dict(near=equal*2, far=equal, alpha=np.full(shape, .75, np.float32))
        positive = predict(upper, t104, s104) - predict(lower, t104, s104)
        positive_error = float(np.max(np.abs(positive - 500)))
        assert positive_error < .02, "known 500DN coverage response failed"
        assert np.array_equal(smooth(np.full(shape, .5, np.float32)), np.full(shape, .5, np.float32))

        with np.load(RUN / "initial.npz", allow_pickle=False) as z:
            seeds = z["seeds"].copy()
        with np.load(RUN / "final-fields.npz", allow_pickle=False) as z:
            final = {k: z[k].copy() for k in ("near", "far", "alpha")}
        if seeds.shape != shape or final["alpha"].shape != shape or any(final[k].shape != (*shape, 3) for k in ("near", "far")):
            raise ValueError("Saved latent dimensions changed")
        assert np.count_nonzero(seeds == 1) == 15 and np.count_nonzero(seeds == 0) == 39
        assert all(v.dtype == np.float32 and np.isfinite(v).all() for v in final.values())
        known = seeds >= 0
        assert np.array_equal(final["alpha"][known], seeds[known].astype(np.float32))
        changed = dict(final)
        changed["alpha"] = smooth(final["alpha"])
        changed["alpha"][known] = seeds[known]
        assert np.array_equal(changed["alpha"][known], final["alpha"][known])
        assert all(np.array_equal(changed[k], final[k]) for k in ("near", "far"))
        np.savez(out / "changed-fields.npz", **changed, seeds=seeds)

        # Exact representation gauge does change the hard background labels;
        # this is a forward symmetry control, not a feasible constrained fit.
        ga = np.float32(1) - np.float32(.5)*(np.float32(1)-final["alpha"])
        gauge = dict(alpha=ga, far=final["far"]/np.float32(.5),
                     near=(final["alpha"][..., None]*final["near"])/ga[..., None])
        base104 = predict(final, t104, s104)
        gauge_prediction_error = float(np.max(np.abs(predict(gauge, t104, s104)-base104)))
        composite, _ = model.compose(final, False)
        gauge_rgb, _ = model.compose(gauge, False)
        gauge_composite_error = float(np.max(np.abs(gauge_rgb-composite)))
        assert gauge_prediction_error < .02 and gauge_composite_error < .02
        save(out / "controls.json", dict(flat_equal_colour_max_delta_DN=flat_error,
             constant_coverage_known500_max_error_DN=positive_error,
             gauge_prediction_max_delta_DN=gauge_prediction_error,
             gauge_composite_max_delta_DN=gauge_composite_error,
             gauge_scope="Supported forward symmetry only; does not preserve fixed zero seeds",
             hard_seeds_exact=True, radiance_sheets_unchanged=True))

        oldheld = {row["index"]: row for row in read(RUN / "held.json")["rows"]}
        measurements = []
        for index in range(96, 161, 8):
            tab = t104 if index == 104 else table(index)
            samples = s104 if index == 104 else sample(index)
            baseline = base104 if index == 104 else predict(final, tab, samples)
            altered = predict(changed, tab, samples)
            replay = None
            if index in model.HELD:
                with np.load(oldheld[index]["arms"]["final"]["prediction"]["path"], allow_pickle=False) as z:
                    for key in ("source_xy", "phase"):
                        assert np.array_equal(samples[key], z[key]), "held support changed"
                    assert np.array_equal(samples["values"], z["observed_u16"])
                    replay = float(np.max(np.abs(baseline-z["predicted_DN"])))
                    assert replay <= .01, "saved held baseline prediction did not replay"
            observed = samples["values"]
            assert not np.any(observed >= model.SATURATION), "original no-clipping support changed"
            sigma = np.sqrt(model.GAIN*np.maximum(baseline-model.BLACK, 0)+model.READ_VARIANCE+1/12)
            with torch.no_grad():
                obs = torch.as_tensor(observed.astype(np.float32), device="cuda")
                losses = [model.nll(torch.as_tensor(v, device="cuda"), obs).cpu().numpy() for v in (baseline, altered)]
            phase_rows = []
            for phase in range(4):
                use = samples["phase"] == phase
                residuals = [v[use]-observed[use].astype(np.float32) for v in (baseline, altered)]
                phase_rows.append(dict(phase=phase, count=int(use.sum()),
                    original_rmse_DN=rms(residuals[0]), changed_rmse_DN=rms(residuals[1]),
                    original_bias_DN=float(np.mean(residuals[0], dtype=np.float64)),
                    changed_bias_DN=float(np.mean(residuals[1], dtype=np.float64)),
                    prediction_delta_rms_DN=rms((altered-baseline)[use]),
                    prediction_delta_rms_in_original_model_sigma=rms(((altered-baseline)/sigma)[use]),
                    original_mean_nll=float(np.mean(losses[0][use], dtype=np.float64)),
                    changed_mean_nll=float(np.mean(losses[1][use], dtype=np.float64))))
            np.savez(out / f"prediction-{index}.npz", original_DN=baseline, changed_DN=altered,
                     observed_u16=observed, phase=samples["phase"], source_xy=samples["source_xy"])
            measurements.append(dict(index=index, split="held" if index in model.HELD else "train",
                                     saved_final_prediction_max_delta_DN=replay, phases=phase_rows))
            print(json.dumps(dict(stage="source", index=index, replay_max_DN=replay)), flush=True)
        save(out / "predictions.json", dict(rows=measurements,
             scope="Conditional fixed-sheet prediction response, not independent noise estimation or photographic quality"))

        changed_rgb, _ = model.compose(changed, False)
        core = np.s_[96:204, 96:240]
        save(out / "composition.json", dict(target_xywh=model.TARGET,
             alpha_change_rms=rms((changed["alpha"]-final["alpha"])[core]),
             alpha_highpass_rms={k: rms(hp(v["alpha"][core])) for k, v in (("original", final), ("changed", changed))},
             composite_highpass_rgb_rms_DN={k: [rms(hp(v[core])[..., c]) for c in range(3)] for k, v in (("original", composite), ("changed", changed_rgb))},
             composite_change_rgb_rms_DN=[rms((changed_rgb-composite)[core][..., c]) for c in range(3)],
             warning="Highpass also measures real detail; reduction cannot establish improvement"))
        # Reuse the exact historical display transform and replay both Current
        # and the entire original failed patch before inspecting altered output.
        cfg = read(RUN / "render-config.json")
        development = read(cfg["receipt"])
        gain = np.asarray([development["exposure_gain_bits"]], np.uint32).view(np.float32)[0]
        wb = np.asarray(development["wb_bits"], np.uint32).view(np.float32)
        cfg["out"] = str(out / "render")
        cfg["candidates"] = []
        for name, rgb in (("original", composite), ("changed", changed_rgb)):
            camera = (np.maximum(rgb[core], np.float32(0))*wb*gain)/np.float32(14848)
            path = out / (name+"-camera-rgb.f32")
            np.ascontiguousarray(camera, dtype="<f4").tofile(path)
            cfg["candidates"].append(dict(name=name, rgb=str(path)))
        save(out / "render-config.json", cfg)
        argv = [str(helper.RENDERER), str(out / "render-config.json")]
        child = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        (out / "render.log").write_text(child.stdout+child.stderr, encoding="utf-8")
        save(out / "render-command.json", dict(argv=argv, exit_code=child.returncode))
        if child.returncode:
            raise RuntimeError("Matched renderer failed")
        receipt = read(out / "render/receipt.json")
        assert receipt["status"] == "BASELINE_PIXELS_EXACT" and receipt["baseline_differing_u16_samples"] == 0 and receipt["baseline_icc_exact"]
        base = read(EXP / "marigold-fan-learned/photo-1/baseline.json")
        context, icc = helper.read_tiff(base["expected_tiff"]["path"])
        historical, historical_icc = helper.read_tiff(RUN / "render/reconstructed.tiff")
        views = []
        for name in ("original", "changed"):
            image, profile = helper.read_tiff(out / "render" / (name+".tiff"))
            assert image.shape == (108, 144, 3) and profile == icc
            if name == "original":
                assert np.array_equal(image, historical) and profile == historical_icc, "original failed patch display did not replay"
            Image.fromarray(((image.astype(np.uint32)+128)//257).astype(np.uint8)).save(out / (name+"-complete-patch.png"), icc_profile=icc)
            inserted = context.copy()
            inserted[252:360, 184:328] = image
            mask = np.ones((384, 384), bool)
            mask[252:360, 184:328] = False
            assert np.array_equal(inserted[mask], context[mask])
            tifffile.imwrite(out / (name+"-local-context384.tiff"), inserted, photometric="rgb", extratags=[(34675, "B", len(icc), icc, False)])
            Image.fromarray(((inserted.astype(np.uint32)+128)//257).astype(np.uint8)).save(out / (name+"-local-context384.png"), icc_profile=icc)
            views.append(dict(name=name, master=ref(out / "render" / (name+".tiff")),
                              patch=ref(out / (name+"-complete-patch.png")), context=ref(out / (name+"-local-context384.png"))))
        for name, fields in (("original", final), ("changed", changed)):
            Image.fromarray(np.rint(fields["alpha"][core]*255).astype(np.uint8)).save(out / (name+"-alpha.png"))
        save(out / "cuda-runtime.json", model.pupil.runtime_metadata())
        result.update(status="FIXED_SAVED_ALPHA_DIAGNOSTIC_COMPLETE", target_xywh=model.TARGET,
                      hard_seeds_exact=True, radiance_sheets_unchanged=True,
                      current_display_replay_exact=True, original_failed_patch_display_replay_exact=True,
                      train=list(model.TRAIN), held=list(model.HELD), views=views)
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if gpu:
            result["gpu"] = dict(allocator_cap_bytes=CAP, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                                 peak_reserved_bytes=torch.cuda.max_memory_reserved(), excludes_driver_and_NVRTC=True)
        result.update(seconds=time.monotonic()-started, inputs_unchanged=all(ref(row["path"]) == row for row in pins))
        save(out / "result.json", result)
        save(out / "bindings.json", pins + [ref(__file__), ref(HERE / "input-pins.json")])
        print(json.dumps(dict(stage="terminal", status=result["status"], seconds=result["seconds"])), flush=True)
        if not result["inputs_unchanged"]:
            raise ValueError("Frozen inputs changed")


if __name__ == "__main__":
    main()

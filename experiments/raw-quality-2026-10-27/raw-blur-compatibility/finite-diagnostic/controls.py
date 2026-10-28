"""One fixed-work image observation; never converts nonconvergence to admission."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import sys
import time

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = HERE.parents[3]
CONTROL_SHA = "fe9428750e557cfd8839c6be2e0a7cbaaea905d8bd3760e3aca21fdc07705b9f"
MODEL_SHA = "659da66d343908564b16262482dc55e3220dd15f8318bf49623a7b2d8d8106cc"
ORDER = ("flat-colour", "compatible")


def load(name, path, expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    args.out.mkdir(parents=True, exist_ok=False)
    c = load("fixed_parent_independent_controls", PARENT/"independent-controls.py", CONTROL_SHA)
    np, torch = c.np, c.torch
    before = [c.file_ref(p) for p in (Path(__file__), PARENT/"independent-controls.py",
        PARENT/"model.py", HERE/"input-identities.json")]
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no changed execution path")
    torch.cuda.set_per_process_memory_fraction(min(1., (4 << 30)/torch.cuda.get_device_properties(0).total_memory))
    model = load("fixed_parent_raw_blur", PARENT/"model.py", MODEL_SHA)
    config = model.Config(field_hw=c.SHAPE, output_xywh=(c.APRON, c.APRON, c.PANEL, c.PANEL),
        shot4=tuple(c.SHOT), read4=tuple(c.READ), black4=tuple(c.BLACK), saturation=16383, anchor_id=0)
    # Generate the entire original CASES sequence, preserving each original seed.
    data = c.generate(args.out)
    originals = json.loads((HERE/"input-identities.json").read_text())
    for row in originals["originals"]:
        old = ROOT/row["path"]
        fresh = args.out/row["case"]/f"source-{row['index']}-original-cfa.npy"
        assert hashlib.sha256(old.read_bytes()).hexdigest() == row["sha256"]
        assert hashlib.sha256(fresh.read_bytes()).hexdigest() == row["sha256"]
    commission = c.commission(model, config, data)
    c.save_json(args.out/"commission.json", commission)
    status = "OPERATOR_REFUSAL" if not commission["pass_guard"] else "FIXED_WORK_DIAGNOSTIC_COMPLETE"
    records = []
    if commission["pass_guard"]:
        for name in ORDER:
            if time.monotonic()-start > 100:
                status = "RESOURCE_ENVELOPE_NOT_ALL_CASES_RUN"
                break
            item = data[name]
            hashes = [c.sha_bytes(v) for v in item["codes"]]
            views = []
            for i in range(7):
                mask = None if i < 5 else c.CALIB
                q = c.query(model, *c.geometry(i), mask)
                codes = item["codes"][i] if mask is None else item["codes"][i][mask]
                views.append(model.View(i, q, codes))
            result = model.fit(views[:5], views[5:], config)
            result.save(item["folder"]/"fit")
            c.preview(item["folder"]/"fit-complete.png", result.output_rgb_dn)
            c.preview(item["folder"]/"initial-complete.png", result.initial_rgb_dn)
            score = c.image_score(name, result.output_rgb_dn)
            held = []
            for i in (5, 6):
                prediction = model.predict(result, c.query(model, *c.geometry(i), c.HELD), source_id=i)
                held.append(dict(source=i, **c.held_guard(prediction, item["codes"][i][c.HELD], c.PHASE[c.HELD], c.XY[c.HELD])))
                np.save(item["folder"]/f"held-{i}-prediction.npy", prediction)
            finite = (bool(np.isfinite(result.x_rgb_dn).all())
                and bool(np.isfinite(result.output_rgb_dn).all())
                and all(h["complete"] and np.isfinite(h["total"]) and np.isfinite(h["gradient_max"]) for h in result.history)
                and all(np.isfinite(r["nll"]) for v in result.calibration.values() for r in v["evaluations"]))
            calibration_localized = all(v["numerical_converged"] for v in result.calibration.values())
            numerical_converged = bool(result.converged) and not result.unsupported
            if name == "compatible":
                numerical_converged = numerical_converged and calibration_localized
            if name == "flat-colour":
                mean = c.flat_mean(item["codes"])
                c.preview(item["folder"]/"same-data-flat-mean-complete.png", mean)
                reference = c.image_score(name, mean)
                image_pass = (score["rgb_rmse_dn"] <= 1.1*reference["rgb_rmse_dn"]+.5
                    and score["chroma_rmse_dn"] <= 1.1*reference["chroma_rmse_dn"]+.5)
                score.update(flat_mean_reference=reference, flat_relative_noise_pass=image_pass)
            else:
                image_pass = score["known_detail_pass"]
            image_only_pass = finite and not result.unsupported and image_pass and all(h["pass_guard"] for h in held)
            row = dict(case=name, numerical_converged=numerical_converged,
                numerical_refusal=not numerical_converged, joint_gradient_converged=bool(result.converged),
                calibration_parameter_localized=calibration_localized, fit_status=result.status,
                finite=finite, unsupported=result.unsupported, numerical_evaluations=result.evaluations,
                final_gradient_max=result.history[-1]["gradient_max"], image=score, held=held,
                image_only_diagnostic_pass=image_only_pass, operationally_accepted=False,
                photographic_admission=False, full_design_qualified=False,
                variances=result.variances, blur_identification_claim=False,
                original_u16_unchanged=hashes == [c.sha_bytes(v) for v in item["codes"]],
                original_u16_sha256=hashes)
            c.save_json(item["folder"]/"decision.json", row)
            records.append(row)
            del views, result
            gc.collect()
            torch.cuda.empty_cache()
            if not image_only_pass:
                status = "FIXED_WORK_IMAGE_DIAGNOSTIC_REFUSAL"
                break
    after = [c.file_ref(p) for p in (Path(__file__), PARENT/"independent-controls.py",
        PARENT/"model.py", HERE/"input-identities.json")]
    assert before == after
    complete = len(records) == len(ORDER)
    image_only_pass = complete and all(r["image_only_diagnostic_pass"] for r in records)
    numerical_refusal = any(r["numerical_refusal"] for r in records)
    c.save_json(args.out/"observations.json", dict(status=status,
        all_cases_completed=complete, all_pass=False, image_only_all_pass=image_only_pass,
        numerical_refusal=numerical_refusal, numerical_refusal_retained=True,
        photographic_admission=False, full_design_qualified=False, actual_native_baseline=False,
        RAW_reads=0, source_bindings=before, original_inputs_exact_run2=True,
        command=[sys.executable, *sys.orig_argv[1:]], commission=commission, cases=records,
        skipped=list(ORDER[len(records):]),
        not_requested=[v for v in c.CASES if v not in ORDER],
        deferred_guards=["Spatial-cell least-blurred-source ordering", "All adverse unknown fits and operational mismatch selectivity"],
        scope="Image-only fixed-work diagnostic. Same64iteration/160evaluation model and original gates; no gradient-tolerance change or admission override.",
        torch_version=torch.__version__, cuda_version=torch.version.cuda,
        tf32_matmul=torch.backends.cuda.matmul.allow_tf32, tf32_cudnn=torch.backends.cudnn.allow_tf32,
        seconds=time.monotonic()-start, cuda_peak_allocated=torch.cuda.max_memory_allocated(),
        cuda_peak_reserved=torch.cuda.max_memory_reserved()))
    print(json.dumps(dict(status=status, image_only_all_pass=image_only_pass,
        numerical_refusal=numerical_refusal, photographic_admission=False)))


if __name__ == "__main__":
    main()

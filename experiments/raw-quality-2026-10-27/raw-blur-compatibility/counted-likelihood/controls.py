"""Count-additive likelihood image diagnostic; numerical refusal remains explicit."""
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
MODEL_SHA = "e66ce20112592f8c0913ac01265d538b3fc073661247b94f972accd9e661befd"
PARENT_MODEL_SHA = "659da66d343908564b16262482dc55e3220dd15f8318bf49623a7b2d8d8106cc"
ORDER = ("flat-neutral", "flat-colour", "compatible")


def load(name, path, expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def partition_control(c, model, old_model, config, data, out):
    """Same actual source2 sensels, regrouped512/3584; no copied observations."""
    np, torch = c.np, c.torch
    whole = c.CENTRAL.copy()
    small = whole & (c.XY[:, 0] < 24)
    large = whole & ~small
    count = int(whole.sum())
    assert count == 4096 and int(small.sum()) == 512 and int(large.sum()) == 3584
    assert np.array_equal(small | large, whole) and not np.any(small & large)
    original_hash = c.sha_bytes(data["codes"][2])

    def evaluate(masks, wrong_average=False, independent_reference=False):
        x = torch.tensor(data["latent"], dtype=torch.float32, device="cuda", requires_grad=True)
        variance = torch.tensor(.8, dtype=torch.float32, device="cuda", requires_grad=True)
        loss = x.new_zeros(())
        reference = x.new_zeros(())
        for mask in masks:
            q = c.query(model, *c.geometry(2), mask)
            codes = torch.tensor(data["codes"][2][mask], dtype=torch.uint16, device="cuda")
            mu = model.forward(x, variance, q, config)
            term = model.data_term(mu, codes, q, config, count)
            if wrong_average:
                term = term*(count/int(mask.sum()))/len(masks)
            loss = loss+term
            if independent_reference:
                phase = q.phase.astype(np.int64)
                shot = torch.tensor(c.SHOT[phase], dtype=torch.float32, device="cuda")
                read = torch.tensor(c.READ[phase], dtype=torch.float32, device="cuda")
                black = torch.tensor(c.BLACK[phase], dtype=torch.float32, device="cuda")
                v = shot*(mu-black).clamp_min(0)+read+mu.new_tensor(1/12)
                reference = reference+((torch.log(v)+(codes.float()-mu).square()/v)*.5).sum()/count
        prior = model.prior_term(x, config, count)
        loss = loss+prior
        gradients = torch.autograd.grad(loss, (x, variance), retain_graph=independent_reference)
        g = np.concatenate((gradients[0].detach().cpu().numpy().ravel().astype(np.float64),
                            np.array([float(gradients[1])], dtype=np.float64)))
        row = dict(objective=float(loss), prior=float(prior), gradient_norm=float(np.linalg.norm(g)))
        ref = None
        if independent_reference:
            reference = reference+old_model._prior(x, config)*(c.PANEL*c.PANEL/count)
            rg = torch.autograd.grad(reference, (x, variance))
            refg = np.concatenate((rg[0].detach().cpu().numpy().ravel().astype(np.float64),
                                   np.array([float(rg[1])], dtype=np.float64)))
            ref = (dict(objective=float(reference), gradient_norm=float(np.linalg.norm(refg))), refg)
        return row, g, ref

    full, fullg, ref = evaluate([whole], independent_reference=True)
    split, splitg, _ = evaluate([small, large])
    wrong, wrongg, _ = evaluate([small, large], wrong_average=True)

    def compare(row, gradient, expected, expected_gradient):
        objective_error = abs(row["objective"]-expected["objective"])
        gradient_error = float(np.linalg.norm(gradient-expected_gradient))
        objective_limit = 2e-5*max(1., abs(expected["objective"]))
        gradient_limit = 2e-4*float(np.linalg.norm(expected_gradient))+1e-7
        return dict(objective_error=objective_error, gradient_l2_error=gradient_error,
            objective_limit=objective_limit, gradient_l2_limit=gradient_limit,
            pass_guard=objective_error <= objective_limit and gradient_error <= gradient_limit)

    literal = compare(full, fullg, ref[0], ref[1])
    invariant = compare(split, splitg, full, fullg)
    foil = compare(wrong, wrongg, full, fullg)
    unchanged = original_hash == c.sha_bytes(data["codes"][2])
    np.savez(out/"partition-gradients.npz", whole=fullg, split=splitg, wrong_mean=wrongg,
             independent_literal=ref[1])
    record = dict(source_id=2, source_u16_sha256=original_hash, original_unchanged=unchanged,
        eligible_count=count, partition_counts=[512, 3584], duplicate_count=0,
        prior_count=1, calibration_observations_counted=0, whole=full, split=split,
        wrong_unweighted_means=wrong, independent_literal=ref[0],
        literal_formula_check=literal, partition_invariance=invariant, wrong_mean_foil=foil,
        pass_guard=literal["pass_guard"] and invariant["pass_guard"] and not foil["pass_guard"] and unchanged,
        scope="Actual forward, NLL consumer and radiance/variance gradients. Same original rows regrouped, not new independent evidence.")
    c.save_json(out/"partition-control.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    args.out.mkdir(parents=True, exist_ok=False)
    c = load("fixed_parent_independent_controls", PARENT/"independent-controls.py", CONTROL_SHA)
    np, torch = c.np, c.torch
    before = [c.file_ref(p) for p in (Path(__file__), PARENT/"independent-controls.py",
        PARENT/"model.py", HERE/"model-counted.py", HERE/"input-identities.json")]
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no changed execution path")
    torch.cuda.set_per_process_memory_fraction(min(1., (4 << 30)/torch.cuda.get_device_properties(0).total_memory))
    model = load("counted_raw_blur", HERE/"model-counted.py", MODEL_SHA)
    old_model = load("frozen_parent_raw_blur", PARENT/"model.py", PARENT_MODEL_SHA)
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
    partition = partition_control(c, model, old_model, config, data["compatible"], args.out)
    status = "OPERATOR_REFUSAL" if not (commission["pass_guard"] and partition["pass_guard"]) else "FIXED_WORK_DIAGNOSTIC_COMPLETE"
    records = []
    if commission["pass_guard"] and partition["pass_guard"]:
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
            if name in ("flat-neutral", "flat-colour"):
                mean = c.flat_mean(item["codes"])
                c.preview(item["folder"]/"same-data-flat-mean-complete.png", mean)
                reference = c.image_score(name, mean)
                image_pass = (score["rgb_rmse_dn"] <= 1.1*reference["rgb_rmse_dn"]+.5
                    and score["chroma_rmse_dn"] <= 1.1*reference["chroma_rmse_dn"]+.5)
                score.update(flat_mean_reference=reference, flat_relative_noise_pass=image_pass)
            else:
                image_pass = score["known_detail_pass"]
            flat_nuisance = [flag for flag in result.unsupported
                if name in ("flat-neutral", "flat-colour")
                and flag in ("calibration_variance_ceiling:5", "calibration_variance_ceiling:6")]
            blocking_unsupported = [flag for flag in result.unsupported if flag not in flat_nuisance]
            image_only_pass = finite and not blocking_unsupported and image_pass and all(h["pass_guard"] for h in held)
            row = dict(case=name, numerical_converged=numerical_converged,
                numerical_refusal=not numerical_converged, joint_gradient_converged=bool(result.converged),
                calibration_parameter_localized=calibration_localized, fit_status=result.status,
                finite=finite, unsupported=result.unsupported,
                flat_unidentifiable_calibration_flags=flat_nuisance, blocking_unsupported=blocking_unsupported,
                numerical_evaluations=result.evaluations,
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
        PARENT/"model.py", HERE/"model-counted.py", HERE/"input-identities.json")]
    assert before == after
    complete = len(records) == len(ORDER)
    image_only_pass = complete and all(r["image_only_diagnostic_pass"] for r in records)
    numerical_refusal = any(r["numerical_refusal"] for r in records)
    c.save_json(args.out/"observations.json", dict(status=status,
        all_cases_completed=complete, all_pass=False, image_only_all_pass=image_only_pass,
        numerical_refusal=numerical_refusal, numerical_refusal_retained=True,
        photographic_admission=False, full_design_qualified=False, actual_native_baseline=False,
        RAW_reads=0, source_bindings=before, original_inputs_exact_run2=True,
        command=[sys.executable, *sys.orig_argv[1:]], commission=commission,
        partition_control=partition, cases=records,
        skipped=list(ORDER[len(records):]),
        not_requested=[v for v in c.CASES if v not in ORDER],
        deferred_guards=["Spatial-cell least-blurred-source ordering", "All adverse unknown fits and operational mismatch selectivity"],
        scope="One count-additive data likelihood with prior counted once; same64iteration/160evaluation algorithm and original gates. Only declared constant-scene calibration ceiling flags permit diagnostic progression. Admission remains false.",
        torch_version=torch.__version__, cuda_version=torch.version.cuda,
        tf32_matmul=torch.backends.cuda.matmul.allow_tf32, tf32_cudnn=torch.backends.cudnn.allow_tf32,
        seconds=time.monotonic()-start, cuda_peak_allocated=torch.cuda.max_memory_allocated(),
        cuda_peak_reserved=torch.cuda.max_memory_reserved()))
    print(json.dumps(dict(status=status, image_only_all_pass=image_only_pass,
        numerical_refusal=numerical_refusal, photographic_admission=False)))


if __name__ == "__main__":
    main()

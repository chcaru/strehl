"""One paired free-visibility continuation; all previous experiments stay frozen."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
CASES = ("flat", "layered", "far-only", "angular-mismatch")
KINDS = ("original", "matrix")
PARAMETERS = ["near", "far", "alpha_logit"]
FROZEN = {
    "model.py": "5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512",
    "convergence.py": "e755e29ec5494714818fae9c61428e6c10d085c2e2d2fd78e2959998c58df468",
    "visibility-oracle.py": "b2b718df8b13be042c8f51a07287ebbe2872936baacfd5b52c8a83dbaf91d6a9",
    "matrix-cauchy-prior.py": "6555432834b543f5102899e4c21931c050ce6994b898e5b0ac74f38b03880b9a",
    "in-focus-consumer.py": "3e75c94dbf0c2f4665f25161751ec28c6ef162ebdd06c5f4f4681b4a1f0fc013",
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


model = load_module("free_visibility_frozen_model", HERE/"model.py")
base = load_module("free_visibility_frozen_continuation", HERE/"convergence.py")
matrix = load_module("free_visibility_frozen_matrix", HERE/"matrix-cauchy-prior.py")
consumer = load_module("free_visibility_frozen_consumer", HERE/"in-focus-consumer.py")
sha, save, TRAIN, HELD = base.sha, base.save, base.TRAIN, base.HELD


def selected_prior(state, config, kind):
    if kind == "original":
        return state.prior()
    if kind == "matrix":
        return matrix.selected_prior(state, config)
    raise ValueError("unknown prior kind")


def run_arm(source, out, case, kind):
    original = source/case/"two-layer"
    paths = dict(state=original/"state.pt", receipt=original/"receipt.json",
        reconstruction=original/"reconstruction.npz", observations=source/case/"observations-u16.npy")
    paths.update({name: HERE/name for name in FROZEN})
    bindings = {k: dict(path=str(p), sha256=sha(p)) for k, p in paths.items()}
    old = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    if tuple(old["train_indices"]) != TRAIN or old["status"] != "iteration_limit" or old["mode"] != "two-layer":
        raise ValueError("requires original free-alpha160 two-layer checkpoint")
    config = model.Config(**old["config"])
    if config.device != "cuda" or (config.width, config.height) != (96, 96) or config.psf_sigma != consumer.SIGMA:
        raise ValueError("fixed CUDA96 extent and original in-focus PSF required")
    observed = base.TrainingOnly(np.load(paths["observations"], mmap_mode="r", allow_pickle=False))
    initialized = model.fit(observed, config, TRAIN, mode="two-layer", optimize=False)
    state = initialized.state
    weights = torch.load(paths["state"], map_location=config.device, weights_only=True)
    state.load_state_dict(weights, strict=True)
    if any(not torch.equal(state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("checkpoint restore changed parameters")
    parameter_names = [k for k, p in state.named_parameters() if p.requires_grad]
    if parameter_names != PARAMETERS or list(state.state_dict()) != PARAMETERS:
        raise AssertionError("all and only original near/far/alpha_logit must be trainable")
    if initialized.training_hashes != old["training_sha256"]:
        raise AssertionError("training source changed")
    initial = model.FitResult(state, config, "two-layer", [], initialized.training_hashes)
    with np.load(paths["reconstruction"], allow_pickle=False) as saved:
        identity = {field: bool(np.array_equal(saved[field], getattr(initial, field)))
                    for field in ("near_rgb", "far_rgb", "alpha", "pinhole_rgb")}
    if not all(identity.values()):
        raise AssertionError("restored fields differ from original free-alpha checkpoint")
    dest = out/case/kind
    dest.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(dest/"initial-reconstruction.npz", near_rgb=initial.near_rgb,
        far_rgb=initial.far_rgb, alpha=initial.alpha, pinhole_rgb=initial.pinhole_rgb)
    optimizer = torch.optim.LBFGS(state.parameters(), lr=1, max_iter=1000, max_eval=1400,
        history_size=10, tolerance_grad=1e-6, tolerance_change=1e-11, line_search_fn="strong_wolfe")
    history, started, evaluations, progress = [], time.monotonic(), 0, -1
    m, scale = config.valid_margin, config.saturation-config.black

    def evaluate(tag):
        nonlocal evaluations, progress
        if evaluations >= (1800 if tag == "final" else 1799):
            raise RuntimeError("hard1800 actual-evaluation cap reached")
        evaluations += 1
        row = dict(evaluation=evaluations, tag=tag, evaluation_status="started")
        history.append(row)
        optimizer.zero_grad(set_to_none=True)
        data = 0.0
        for index in TRAIN:
            near, far, alpha = state.fields()
            rgb = model.forward(near*scale, far*scale, alpha, config, index)
            current = torch.as_tensor(np.array(observed[index], dtype=np.float32, copy=True), device=config.device)
            loss = model.observation_nll(model.cfa(rgb)+config.black, current,
                gain=config.gain, read_variance=config.read_variance, black=config.black,
                saturation=config.saturation)[m:-m, m:-m].mean()/len(TRAIN)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite training likelihood")
            loss.backward()
            data += float(loss.detach())
            del near, far, alpha, rgb, current, loss
        prior = selected_prior(state, config, kind)
        prior.backward()
        gradient = torch.cat([p.grad.detach().reshape(-1) for p in state.parameters()])
        if not torch.isfinite(prior) or not torch.isfinite(gradient).all():
            raise FloatingPointError("nonfinite objective/gradient")
        converted = 0
        for p in state.parameters():
            logical, contiguous = p.grad.detach().reshape(-1), p.grad.contiguous()
            if not torch.equal(logical, contiguous.view(-1)):
                raise AssertionError("contiguous gradient changed logical values")
            converted += int(not p.grad.is_contiguous())
            p.grad = contiguous
        total = data+float(prior.detach())
        iteration = optimizer.state[state.near].get("n_iter", 0)
        row.update(evaluation_status="complete", data_nll=data, prior=float(prior.detach()), total=total,
            gradient_l2=float(torch.linalg.vector_norm(gradient)), gradient_max=float(gradient.abs().max()),
            optimizer_iteration=iteration, noncontiguous_gradients_converted=converted,
            gradient_storage_logical_exact=True, elapsed_seconds=time.monotonic()-started)
        if iteration//100 > progress:
            progress = iteration//100
            print("FREE_VISIBILITY_PROGRESS", json.dumps(dict(case=case, prior_kind=kind, **row)), flush=True)
        return torch.tensor(total, dtype=torch.float64, device=config.device)

    evaluate("initial")
    initial_record = dict(history[-1])
    error, accepted, final_record = None, True, None
    try:
        optimizer.step(lambda: evaluate("closure"))
    except (RuntimeError, FloatingPointError) as exc:
        error, accepted = str(exc), False
        if history[-1]["evaluation_status"] == "started":
            history[-1].update(evaluation_status="refused", error=str(exc))
    try:
        evaluate("final")
        final_record = dict(history[-1])
    except (RuntimeError, FloatingPointError) as exc:
        error, accepted = (error or "")+"; final monitor: "+str(exc), False
        if history[-1]["evaluation_status"] == "started":
            history[-1].update(evaluation_status="refused", error=str(exc))
    status = "numerical_refusal" if error else (
        "stationary_gradient" if final_record["gradient_max"] <= 1e-6 else "nonstationary_return")
    torch.save(state.state_dict(), dest/"state.pt")
    predictions, images = [], []
    try:
        result = model.FitResult(state, config, "two-layer", history, initialized.training_hashes)
        np.savez_compressed(dest/"reconstruction.npz", near_rgb=result.near_rgb,
            far_rgb=result.far_rgb, alpha=result.alpha, pinhole_rgb=result.pinhole_rgb)
        for label, image in (("pinhole", result.pinhole_rgb),
                             ("in-focus", consumer.apply_in_focus(result.pinhole_rgb))):
            name = f"{label}-rgb-f32.npy"
            np.save(dest/name, image, allow_pickle=False)
            images.append(dict(target=label, path=name, sha256=sha(dest/name),
                               psf_applications=int(label == "in-focus")))
        for index in HELD:  # optical settings only, after fitting; no held observation values
            name = f"predicted-cfa-{index}.npy"
            np.save(dest/name, result.predict(index), allow_pickle=False)
            predictions.append(dict(index=index, path=name, sha256=sha(dest/name)))
    except (RuntimeError, FloatingPointError) as exc:
        error, status, accepted = (error or "")+"; export: "+str(exc), "numerical_refusal", False
    if any(sha(p) != bindings[k]["sha256"] for k, p in paths.items()):
        raise AssertionError("bound inputs changed")
    internal = optimizer.state[state.near]
    receipt = dict(config=old["config"], mode="two-layer", prior_kind=kind,
        prior_definition="original-sheet-huber" if kind == "original" else matrix.PRIOR_KIND,
        visibility="free-original-sigmoid", train_indices=list(TRAIN),
        training_sha256=initialized.training_hashes, source_bindings=bindings,
        source_bindings_unchanged=True, source_state_sha256=sha(paths["state"]),
        state_sha256=sha(dest/"state.pt"), initial_checkpoint_exact=True,
        initial_parameter_names=parameter_names, gradient_parameter_names=parameter_names,
        initial_field_identity=identity, initial_objective=initial_record, final_objective=final_record,
        closure_history=history, status=status, error=error, returned_state_accepted=accepted,
        actual_evaluations=evaluations, hard_evaluation_cap=1800,
        completed_evaluations=sum(h["evaluation_status"] == "complete" for h in history),
        optimizer_n_iter=internal.get("n_iter", 0), optimizer_func_evals=internal.get("func_evals", 0),
        noncontiguous_gradients_converted=sum(h.get("noncontiguous_gradients_converted", 0) for h in history),
        wall_seconds=time.monotonic()-started, read_indices=sorted(set(observed.reads)),
        read_count=len(observed.reads), predictions=predictions, images=images,
        primary_target="one original common PSF applied to composed full96 pinhole",
        pinhole_target_retained=True, real_photo_admission=False,
        stationarity_scope="raw normalized softplus/logit parameter gradient; not physical opacity identification or global optimality")
    save(dest/"receipt.json", receipt)
    print("FREE_VISIBILITY_ARM", json.dumps(dict(case=case, prior_kind=kind, status=status,
        actual_evaluations=evaluations, final_objective=final_record)), flush=True)
    return dict(case=case, prior_kind=kind, status=status, receipt=str(dest/"receipt.json"),
                receipt_sha256=sha(dest/"receipt.json"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    bindings = json.loads((source/"bindings.json").read_text(encoding="utf-8"))
    if any(sha(HERE/name) != expected for name, expected in FROZEN.items()):
        raise AssertionError("frozen source changed")
    if bindings["model_sha256"] != base.MODEL_HASH or sha(HERE/"independent-controls.py") != bindings["controls_sha256"]:
        raise AssertionError("original model/controls binding changed")
    files = [HERE/name for name in FROZEN]+[HERE/name for name in
        ("design.md", "independent-controls.py", "free-visibility.py", "free-visibility-plan.md")]+[source/"bindings.json"]
    for case in CASES:
        files += [source/case/"observations-u16.npy"]
        files += [source/case/"two-layer"/name for name in ("state.pt", "receipt.json", "reconstruction.npz")]
    before = {str(p): sha(p) for p in files}
    out.mkdir(parents=True, exist_ok=False)
    save(out/"bindings-before.json", before)
    started = time.monotonic()
    rows = [run_arm(source, out, case, kind) for case in CASES for kind in KINDS]
    after = {str(p): sha(p) for p in files}
    save(out/"bindings-after.json", after)
    if before != after:
        raise AssertionError("immutable input/source binding changed")
    result = dict(status="FREE_VISIBILITY_COMPLETE", arms=rows, source_root=str(source),
        bindings_unchanged=True, wall_seconds=time.monotonic()-started,
        visibility_oracle_used=False, original_pinhole_admission_unchanged=True,
        real_photo_admission=False, primary_target="common-PSF of composed pinhole RGB",
        interpretation="Paired free-alpha original/matrix priors; same original160 starts and optimizer. Independent scoring required.")
    save(out/"result.json", result)
    print("FREE_VISIBILITY_COMPLETE", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()

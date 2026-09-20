"""One fixed image-prior placement comparison; original experiments stay frozen."""
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
KINDS = ("original", "composite")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


model = load_module("composite_frozen_model", HERE/"model.py")
base = load_module("composite_frozen_continuation", HERE/"convergence.py")
sha, save, TRAIN, HELD = base.sha, base.save, base.TRAIN, base.HELD


def image_regularizer(state, kind):
    if kind not in KINDS:
        raise ValueError("unknown prior kind")
    near, far, alpha = state.fields()
    images = [near] if state.far is None else [near, far]
    if kind == "composite" and state.far is not None:
        images = [alpha[..., None]*near+(1-alpha[..., None])*far]
    return sum(model._vector_huber(v*state.dn_scale, state.gradient_scale) for v in images)/len(images)


def selected_prior(state, kind):
    if kind not in KINDS:
        raise ValueError("unknown prior kind")
    if kind == "original" or state.far is None:
        return state.prior()  # exact frozen original / one-layer route
    near, far, alpha = state.fields()
    image = image_regularizer(state, kind)
    flux = (near.square().mean()+far.square().mean())/2
    alpha_tv = (torch.abs(alpha[1:]-alpha[:-1]).mean()+
                torch.abs(alpha[:, 1:]-alpha[:, :-1]).mean())/2
    binary = (alpha*(1-alpha)).mean()
    return image + 0.02*alpha_tv + 0.002*binary + 0.0001*flux


def run_arm(source, out, case, kind):
    original = source/case/"two-layer"
    source_files = {"state": original/"state.pt", "receipt": original/"receipt.json",
        "reconstruction": original/"reconstruction.npz", "observations": source/case/"observations-u16.npy",
        "model": HERE/"model.py", "continuation": HERE/"convergence.py"}
    source_bindings = {k: dict(path=str(p), sha256=sha(p)) for k, p in source_files.items()}
    old = json.loads((original/"receipt.json").read_text(encoding="utf-8"))
    if tuple(old["train_indices"]) != TRAIN or old["status"] != "iteration_limit" or old["mode"] != "two-layer":
        raise ValueError("not the fixed original two-layer 160-step checkpoint")
    config = model.Config(**old["config"])
    if config.device != "cuda":
        raise ValueError("CUDA required")
    raw = np.load(source/case/"observations-u16.npy", mmap_mode="r", allow_pickle=False)
    observed = base.TrainingOnly(raw)
    initialized = model.fit(observed, config, TRAIN, mode="two-layer", optimize=False)
    state = initialized.state
    weights = torch.load(original/"state.pt", map_location=config.device, weights_only=True)
    state.load_state_dict(weights, strict=True)
    if any(not torch.equal(state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("checkpoint restore changed parameters")
    if initialized.training_hashes != old["training_sha256"]:
        raise AssertionError("training source changed")
    restored = model.FitResult(state, config, "two-layer", [], initialized.training_hashes)
    with np.load(original/"reconstruction.npz", allow_pickle=False) as saved:
        for field in ("near_rgb", "far_rgb", "alpha", "pinhole_rgb"):
            if not np.array_equal(saved[field], getattr(restored, field)):
                raise AssertionError("restored image differs from original checkpoint")
    dest = out/case/kind
    dest.mkdir(parents=True, exist_ok=False)
    optimizer = torch.optim.LBFGS(state.parameters(), lr=1, max_iter=1000,
        max_eval=1400, history_size=10, tolerance_grad=1e-6,
        tolerance_change=1e-11, line_search_fn="strong_wolfe")
    history, started, evaluations, reported_iteration = [], time.monotonic(), 0, -1
    m, scale = config.valid_margin, config.saturation-config.black

    def evaluate(tag):
        nonlocal evaluations, reported_iteration
        if evaluations >= (1800 if tag == "final" else 1799):
            raise RuntimeError("hard1800 actual-evaluation cap reached")
        evaluations += 1
        record = dict(evaluation=evaluations, tag=tag, evaluation_status="started",
                      elapsed_seconds=time.monotonic()-started)
        history.append(record)
        optimizer.zero_grad(set_to_none=True)
        data = 0.0
        for index in TRAIN:
            near, far, alpha = state.fields()
            rgb = model.forward(near*scale, far*scale, alpha, config, index)
            current = torch.as_tensor(np.array(observed[index], dtype=np.float32, copy=True), device=config.device)
            loss = model.observation_nll(model.cfa(rgb)+config.black, current,
                gain=config.gain, read_variance=config.read_variance,
                black=config.black, saturation=config.saturation)[m:-m, m:-m].mean()/len(TRAIN)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite training likelihood")
            loss.backward()
            data += float(loss.detach())
            del near, far, alpha, rgb, current, loss
        prior = selected_prior(state, kind)
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
        internal = optimizer.state[next(iter(state.parameters()))]
        iteration = internal.get("n_iter", 0)
        record.update(evaluation_status="complete", data_nll=data, prior=float(prior.detach()), total=total,
            gradient_l2=float(torch.linalg.vector_norm(gradient)), gradient_max=float(gradient.abs().max()),
            optimizer_iteration=iteration, noncontiguous_gradients_converted=converted,
            gradient_storage_logical_exact=True, elapsed_seconds=time.monotonic()-started)
        if iteration//100 > reported_iteration:
            reported_iteration = iteration//100
            print("COMPOSITE_PROGRESS", json.dumps(dict(case=case, prior_kind=kind,
                iteration=iteration, evaluations=evaluations, total=total,
                elapsed_seconds=time.monotonic()-started)), flush=True)
        return torch.tensor(total, dtype=torch.float64, device=config.device)

    evaluate("initial")
    initial_record = dict(history[-1])
    error, accepted = None, True
    try:
        optimizer.step(lambda: evaluate("closure"))
    except (RuntimeError, FloatingPointError) as exc:
        error, accepted = str(exc), False
        if history[-1]["evaluation_status"] == "started":
            history[-1].update(evaluation_status="refused", error=str(exc))
    final_record = None
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
    prediction_files = []
    try:
        result = model.FitResult(state, config, "two-layer", history, initialized.training_hashes)
        np.savez_compressed(dest/"reconstruction.npz", near_rgb=result.near_rgb,
            far_rgb=result.far_rgb, alpha=result.alpha, pinhole_rgb=result.pinhole_rgb)
        for index in HELD:  # after optimization; reads optical index, never held-out values
            name = f"predicted-cfa-{index}.npy"
            np.save(dest/name, result.predict(index), allow_pickle=False)
            prediction_files.append(dict(index=index, path=name, sha256=sha(dest/name)))
    except (RuntimeError, FloatingPointError) as exc:
        error, status, accepted = (error or "")+"; export: "+str(exc), "numerical_refusal", False
    internal = optimizer.state[next(iter(state.parameters()))]
    if any(sha(p) != source_bindings[k]["sha256"] for k, p in source_files.items()):
        raise AssertionError("arm inputs changed")
    receipt = dict(config=old["config"], mode="two-layer", prior_kind=kind, train_indices=list(TRAIN),
        source_bindings=source_bindings, source_bindings_unchanged=True, initial_checkpoint_exact=True,
        training_sha256=initialized.training_hashes, source_state_sha256=sha(original/"state.pt"),
        state_sha256=sha(dest/"state.pt"), initial_objective=initial_record, final_objective=final_record,
        closure_history=history, status=status, error=error, returned_state_accepted=accepted,
        optimizer_n_iter=internal.get("n_iter", 0), optimizer_func_evals=internal.get("func_evals", 0),
        actual_evaluations=evaluations,
        completed_evaluations=sum(h["evaluation_status"] == "complete" for h in history),
        noncontiguous_gradients_converted=sum(h.get("noncontiguous_gradients_converted", 0) for h in history),
        wall_seconds=time.monotonic()-started, read_indices=sorted(set(observed.reads)),
        read_count=len(observed.reads), predictions=prediction_files,
        stationarity_scope="raw normalized softplus/logit parameter gradient, not a global-optimum claim")
    save(dest/"receipt.json", receipt)
    print("COMPOSITE_ARM", json.dumps(dict(case=case, prior_kind=kind, status=status,
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
    if sha(HERE/"model.py") != base.MODEL_HASH or bindings["model_sha256"] != base.MODEL_HASH:
        raise AssertionError("frozen model changed")
    if sha(HERE/"independent-controls.py") != bindings["controls_sha256"]:
        raise AssertionError("frozen controls changed")
    if sha(HERE/"convergence.py") != "e755e29ec5494714818fae9c61428e6c10d085c2e2d2fd78e2959998c58df468":
        raise AssertionError("frozen continuation helper changed")
    files = [HERE/p for p in ("model.py", "design.md", "independent-controls.py", "convergence.py",
        "composite-prior.py", "composite-prior-plan.md")]+[source/"bindings.json"]
    for case in CASES:
        files += [source/case/"observations-u16.npy"]
        files += [source/case/"two-layer"/p for p in ("state.pt", "receipt.json", "reconstruction.npz")]
    before = {str(p): sha(p) for p in files}
    out.mkdir(parents=True, exist_ok=False)
    save(out/"bindings-before.json", before)
    started = time.monotonic()
    rows = [run_arm(source, out, case, kind) for case in CASES for kind in KINDS]
    after = {str(p): sha(p) for p in files}
    save(out/"bindings-after.json", after)
    if before != after:
        raise AssertionError("immutable input/source binding changed")
    receipt = dict(status="COMPOSITE_COMPARISON_COMPLETE", arms=rows, source_root=str(source),
        bindings_unchanged=True, wall_seconds=time.monotonic()-started,
        frozen_first_screen_pass=False, real_photo_admission=False,
        interpretation="Only image-prior placement differs. Independent scoring remains separate.")
    save(out/"result.json", receipt)
    print("COMPOSITE_COMPLETE", json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()

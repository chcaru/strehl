"""Radiance-only numerical diagnostic with independently supplied exact alpha."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("visibility_frozen_comparison", HERE/"composite-prior.py")
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
model, base = common.model, common.base
sha, save, TRAIN, HELD = common.sha, common.save, common.TRAIN, common.HELD


class FixedVisibility(torch.nn.Module):
    def __init__(self, restored, alpha):
        super().__init__()
        self.dn_scale, self.gradient_scale = restored.dn_scale, restored.gradient_scale
        self.near = torch.nn.Parameter(restored.near.detach().clone())
        self.far = torch.nn.Parameter(restored.far.detach().clone())
        self.register_buffer("fixed_alpha", alpha.detach().clone())

    def fields(self):
        return torch.nn.functional.softplus(self.near), torch.nn.functional.softplus(self.far), self.fixed_alpha

    prior = model._State.prior  # verbatim original sheet prior; alpha terms are constants


def run_arm(source, alpha_dir, out, case):
    original = source/case/"two-layer"
    paths = dict(state=original/"state.pt", receipt=original/"receipt.json",
        reconstruction=original/"reconstruction.npz", observations=source/case/"observations-u16.npy",
        alpha=alpha_dir/f"{case}-alpha-f32.npy", model=HERE/"model.py",
        comparison=HERE/"composite-prior.py", continuation=HERE/"convergence.py")
    bindings = {k: dict(path=str(p), sha256=sha(p)) for k, p in paths.items()}
    old = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    if old["mode"] != "two-layer" or old["status"] != "iteration_limit" or tuple(old["train_indices"]) != TRAIN:
        raise ValueError("requires frozen two-layer 160-step checkpoint")
    config = model.Config(**old["config"])
    if config.device != "cuda":
        raise ValueError("CUDA required")
    alpha = np.load(paths["alpha"], allow_pickle=False)
    if alpha.dtype != np.float32 or alpha.shape != (config.height, config.width) or not np.isfinite(alpha).all() or np.any((alpha < 0) | (alpha > 1)):
        raise ValueError("oracle alpha must be finite f32 HW in [0,1]")
    observed = base.TrainingOnly(np.load(paths["observations"], mmap_mode="r", allow_pickle=False))
    initialized = model.fit(observed, config, TRAIN, mode="two-layer", optimize=False)
    weights = torch.load(paths["state"], map_location=config.device, weights_only=True)
    initialized.state.load_state_dict(weights, strict=True)
    if any(not torch.equal(initialized.state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("original state restoration changed parameters")
    if initialized.training_hashes != old["training_sha256"]:
        raise AssertionError("training observation hash changed")
    state = FixedVisibility(initialized.state, torch.as_tensor(alpha, device=config.device))
    if [name for name, _ in state.named_parameters()] != ["near", "far"] or state.fixed_alpha.requires_grad:
        raise AssertionError("only near/far radiances may receive gradients")
    if any(not torch.equal(getattr(state, k), weights[k]) for k in ("near", "far")):
        raise AssertionError("initial sheet parameters changed")
    initial = model.FitResult(state, config, "two-layer", [], initialized.training_hashes)
    with np.load(paths["reconstruction"], allow_pickle=False) as old_images:
        if not all(np.array_equal(getattr(initial, k), old_images[k]) for k in ("near_rgb", "far_rgb")):
            raise AssertionError("initial sheet images changed")
        initial_pinhole_change = float(np.max(np.abs(initial.pinhole_rgb-old_images["pinhole_rgb"])))
    dest = out/case/"fixed-alpha"
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
            near, far, fixed = state.fields()
            rgb = model.forward(near*scale, far*scale, fixed, config, index)
            current = torch.as_tensor(np.array(observed[index], dtype=np.float32, copy=True), device=config.device)
            loss = model.observation_nll(model.cfa(rgb)+config.black, current,
                gain=config.gain, read_variance=config.read_variance, black=config.black,
                saturation=config.saturation)[m:-m, m:-m].mean()/len(TRAIN)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite training likelihood")
            loss.backward()
            data += float(loss.detach())
            del near, far, fixed, rgb, current, loss
        prior = state.prior()
        prior.backward()
        gradient = torch.cat([p.grad.detach().reshape(-1) for p in state.parameters()])
        if not torch.isfinite(prior) or not torch.isfinite(gradient).all():
            raise FloatingPointError("nonfinite objective/gradient")
        converted = 0
        for p in state.parameters():
            logical, contiguous = p.grad.detach().reshape(-1), p.grad.contiguous()
            if not torch.equal(logical, contiguous.view(-1)):
                raise AssertionError("gradient layout changed logical values")
            converted += int(not p.grad.is_contiguous())
            p.grad = contiguous
        total = data+float(prior.detach())
        iteration = optimizer.state[state.near].get("n_iter", 0)
        row.update(evaluation_status="complete", data_nll=data, prior=float(prior.detach()), total=total,
            gradient_max=float(gradient.abs().max()), gradient_l2=float(torch.linalg.vector_norm(gradient)),
            optimizer_iteration=iteration, noncontiguous_gradients_converted=converted,
            gradient_storage_logical_exact=True, elapsed_seconds=time.monotonic()-started)
        if iteration//100 > progress:
            progress = iteration//100
            print("VISIBILITY_PROGRESS", json.dumps(dict(case=case, **row)), flush=True)
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
    if not np.array_equal(state.fixed_alpha.detach().cpu().numpy(), alpha):
        raise AssertionError("fixed alpha changed")
    torch.save(state.state_dict(), dest/"state.pt")
    predictions = []
    try:
        result = model.FitResult(state, config, "two-layer", history, initialized.training_hashes)
        np.savez_compressed(dest/"reconstruction.npz", near_rgb=result.near_rgb,
            far_rgb=result.far_rgb, alpha=result.alpha, pinhole_rgb=result.pinhole_rgb)
        for index in HELD:
            name = f"predicted-cfa-{index}.npy"
            np.save(dest/name, result.predict(index), allow_pickle=False)
            predictions.append(dict(index=index, path=name, sha256=sha(dest/name)))
    except (RuntimeError, FloatingPointError) as exc:
        error, status, accepted = (error or "")+"; export: "+str(exc), "numerical_refusal", False
    if any(sha(p) != bindings[k]["sha256"] for k, p in paths.items()):
        raise AssertionError("input binding changed")
    internal = optimizer.state[state.near]
    receipt = dict(config=old["config"], mode="two-layer", prior_kind="original", visibility="oracle-fixed",
        train_indices=list(TRAIN), training_sha256=initialized.training_hashes, source_bindings=bindings,
        source_bindings_unchanged=True, source_state_sha256=sha(paths["state"]), state_sha256=sha(dest/"state.pt"),
        alpha_sha256=sha(paths["alpha"]), fixed_alpha_exact=True, initial_sheet_parameters_exact=True,
        initial_sheet_images_exact=True, initial_pinhole_max_abs_change_dn=initial_pinhole_change,
        gradient_parameter_names=[name for name, _ in state.named_parameters()],
        initial_objective=initial_record, final_objective=final_record, closure_history=history,
        status=status, error=error, returned_state_accepted=accepted, actual_evaluations=evaluations,
        completed_evaluations=sum(h["evaluation_status"] == "complete" for h in history),
        optimizer_n_iter=internal.get("n_iter", 0), optimizer_func_evals=internal.get("func_evals", 0),
        noncontiguous_gradients_converted=sum(h.get("noncontiguous_gradients_converted", 0) for h in history),
        wall_seconds=time.monotonic()-started, read_indices=sorted(set(observed.reads)),
        read_count=len(observed.reads), predictions=predictions,
        stationarity_scope="raw normalized softplus radiance parameter gradient; not global optimality")
    save(dest/"receipt.json", receipt)
    print("VISIBILITY_ARM", json.dumps(dict(case=case, status=status, final_objective=final_record)), flush=True)
    return dict(case=case, status=status, receipt=str(dest/"receipt.json"), receipt_sha256=sha(dest/"receipt.json"))


def main():
    parser = argparse.ArgumentParser()
    for name in ("source", "alpha-root", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    source, alpha_dir, out = args.source.resolve(), args.alpha_root.resolve(), args.out.resolve()
    bindings = json.loads((source/"bindings.json").read_text(encoding="utf-8"))
    if sha(HERE/"model.py") != base.MODEL_HASH or bindings["model_sha256"] != base.MODEL_HASH:
        raise AssertionError("frozen model changed")
    if sha(HERE/"composite-prior.py") != "856003f26de6ec841a5b4e6ff1dd06ac35bdc3a95baec1683e5fa91889038a6d":
        raise AssertionError("frozen comparison helper changed")
    if sha(HERE/"convergence.py") != "e755e29ec5494714818fae9c61428e6c10d085c2e2d2fd78e2959998c58df468":
        raise AssertionError("frozen continuation helper changed")
    if sha(HERE/"independent-controls.py") != bindings["controls_sha256"]:
        raise AssertionError("frozen truth generator changed")
    out.mkdir(parents=True, exist_ok=False)
    rows = [run_arm(source, alpha_dir, out, case) for case in ("flat", "layered")]
    result = dict(status="VISIBILITY_ORACLE_COMPLETE", arms=rows, source_root=str(source),
        alpha_directory=str(alpha_dir), real_photo_admission=False,
        interpretation="Only supplied visibility is changed; original sheets/prior/solver retained.")
    save(out/"result.json", result)
    print("VISIBILITY_COMPLETE", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()

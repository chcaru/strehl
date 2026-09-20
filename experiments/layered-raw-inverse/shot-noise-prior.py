"""One supplied-noise radiance prior, with fixed independently supplied alpha."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shot_frozen_visibility", HERE/"visibility-oracle.py")
visibility = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = visibility
spec.loader.exec_module(visibility)
model, base, sha, save = visibility.model, visibility.base, visibility.sha, visibility.save
TRAIN, HELD = visibility.TRAIN, visibility.HELD
PRIOR_KIND = "shot-noise-stabilized-sheets"


def image_huber_dn(image, gain, read_variance):
    """Cancellation-safe h differences; supplied noise only, all derivatives live."""
    c = read_variance+1/12
    # Convert the existing 1e-12 DN² norm safeguard to reference-normalized units.
    epsilon = 1e-12/(2*(gain*2048+c))
    result = image.new_zeros(())
    for first, second in ((image[:-1], image[1:]), (image[:, :-1], image[:, 1:])):
        delta = math.sqrt(2)*(second-first)/(torch.sqrt(gain*second+c)+torch.sqrt(gain*first+c))
        magnitude = torch.sqrt(delta.square().sum(-1)+epsilon)
        result = result+torch.where(magnitude <= 2, .5*magnitude.square(), 2*magnitude-2).mean()/2
    return result


def shot_image_prior(state, config):
    near, far, _ = state.fields()
    images = [near] if state.far is None else [near, far]
    return sum(image_huber_dn(v*state.dn_scale, config.gain, config.read_variance) for v in images)/len(images)


def selected_prior(state, config):
    near, far, alpha = state.fields()
    images = [near] if state.far is None else [near, far]
    image = shot_image_prior(state, config)
    flux = sum(v.square().mean() for v in images)/len(images)
    alpha_tv = (torch.abs(alpha[1:]-alpha[:-1]).mean()+
                torch.abs(alpha[:, 1:]-alpha[:, :-1]).mean())/2
    binary = (alpha*(1-alpha)).mean()
    return image+0.02*alpha_tv+0.002*binary+0.0001*flux


class ShotState(visibility.FixedVisibility):
    def __init__(self, restored, alpha, config):
        super().__init__(restored, alpha)
        self.config = config

    def prior(self):
        return selected_prior(self, self.config)


def run_arm(source, alpha_root, out, case):
    original = source/case/"two-layer"
    paths = dict(state=original/"state.pt", receipt=original/"receipt.json",
        reconstruction=original/"reconstruction.npz", observations=source/case/"observations-u16.npy",
        alpha=alpha_root/f"{case}-alpha-f32.npy", model=HERE/"model.py", visibility=HERE/"visibility-oracle.py",
        reference=HERE/"visibility-1"/"output"/case/"fixed-alpha"/"receipt.json")
    bindings = {k: dict(path=str(p), sha256=sha(p)) for k, p in paths.items()}
    old = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    reference = json.loads(paths["reference"].read_text(encoding="utf-8"))
    if old["mode"] != "two-layer" or old["status"] != "iteration_limit" or tuple(old["train_indices"]) != TRAIN:
        raise ValueError("requires frozen original160 two-layer checkpoint")
    if bindings["alpha"]["sha256"] != reference["alpha_sha256"] or old["config"] != reference["config"] or bindings["state"]["sha256"] != reference["source_state_sha256"]:
        raise AssertionError("initial sheets/alpha/config differ from retained visibility baseline")
    config = model.Config(**old["config"])
    if config.device != "cuda":
        raise ValueError("CUDA required")
    alpha = np.load(paths["alpha"], allow_pickle=False)
    if alpha.dtype != np.float32 or alpha.shape != (config.height, config.width) or not np.isfinite(alpha).all() or np.any((alpha < 0) | (alpha > 1)):
        raise ValueError("fixed alpha must be finite f32 HW in [0,1]")
    observed = base.TrainingOnly(np.load(paths["observations"], mmap_mode="r", allow_pickle=False))
    initialized = model.fit(observed, config, TRAIN, mode="two-layer", optimize=False)
    weights = torch.load(paths["state"], map_location=config.device, weights_only=True)
    initialized.state.load_state_dict(weights, strict=True)
    if any(not torch.equal(initialized.state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("checkpoint restore changed parameters")
    if initialized.training_hashes != old["training_sha256"]:
        raise AssertionError("training source changed")
    state = ShotState(initialized.state, torch.as_tensor(alpha, device=config.device), config)
    if [k for k, _ in state.named_parameters()] != ["near", "far"] or state.fixed_alpha.requires_grad:
        raise AssertionError("only sheet radiances may be optimized")
    if any(not torch.equal(getattr(state, k), weights[k]) for k in ("near", "far")):
        raise AssertionError("initial sheet parameters differ")
    initial = model.FitResult(state, config, "two-layer", [], initialized.training_hashes)
    with np.load(paths["reconstruction"], allow_pickle=False) as saved:
        if not all(np.array_equal(getattr(initial, k), saved[k]) for k in ("near_rgb", "far_rgb")):
            raise AssertionError("initial sheet images differ")
        initial_change = float(np.max(np.abs(initial.pinhole_rgb-saved["pinhole_rgb"])))
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
            y = torch.as_tensor(np.array(observed[index], dtype=np.float32, copy=True), device=config.device)
            loss = model.observation_nll(model.cfa(rgb)+config.black, y,
                gain=config.gain, read_variance=config.read_variance, black=config.black,
                saturation=config.saturation)[m:-m, m:-m].mean()/len(TRAIN)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite likelihood")
            loss.backward()
            data += float(loss.detach())
            del near, far, fixed, rgb, y, loss
        prior = state.prior()
        prior.backward()
        gradient = torch.cat([p.grad.detach().reshape(-1) for p in state.parameters()])
        if not torch.isfinite(prior) or not torch.isfinite(gradient).all():
            raise FloatingPointError("nonfinite objective/gradient")
        converted = 0
        for p in state.parameters():
            logical, contiguous = p.grad.detach().reshape(-1), p.grad.contiguous()
            if not torch.equal(logical, contiguous.view(-1)):
                raise AssertionError("gradient layout changed values")
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
            print("SHOT_PRIOR_PROGRESS", json.dumps(dict(case=case, **row)), flush=True)
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
        raise AssertionError("bound inputs changed")
    internal = optimizer.state[state.near]
    receipt = dict(config=old["config"], mode="two-layer", prior_kind=PRIOR_KIND, visibility="oracle-fixed",
        train_indices=list(TRAIN), training_sha256=initialized.training_hashes, source_bindings=bindings,
        source_bindings_unchanged=True, source_state_sha256=sha(paths["state"]), state_sha256=sha(dest/"state.pt"),
        alpha_sha256=sha(paths["alpha"]), fixed_alpha_exact=True, initial_sheet_parameters_exact=True,
        initial_sheet_images_exact=True, initial_pinhole_max_abs_change_dn=initial_change,
        gradient_parameter_names=[k for k, _ in state.named_parameters()], initial_objective=initial_record,
        final_objective=final_record, closure_history=history, status=status, error=error,
        returned_state_accepted=accepted, actual_evaluations=evaluations,
        completed_evaluations=sum(h["evaluation_status"] == "complete" for h in history),
        optimizer_n_iter=internal.get("n_iter", 0), optimizer_func_evals=internal.get("func_evals", 0),
        noncontiguous_gradients_converted=sum(h.get("noncontiguous_gradients_converted", 0) for h in history),
        wall_seconds=time.monotonic()-started, read_indices=sorted(set(observed.reads)),
        read_count=len(observed.reads), predictions=predictions,
        stationarity_scope="raw normalized softplus radiance parameter gradient; not global optimality")
    save(dest/"receipt.json", receipt)
    print("SHOT_PRIOR_ARM", json.dumps(dict(case=case, status=status, final_objective=final_record)), flush=True)
    return dict(case=case, status=status, receipt=str(dest/"receipt.json"), receipt_sha256=sha(dest/"receipt.json"))


def main():
    parser = argparse.ArgumentParser()
    for name in ("source", "alpha-root", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    source, alpha_root, out = args.source.resolve(), args.alpha_root.resolve(), args.out.resolve()
    if sha(HERE/"visibility-oracle.py") != "b2b718df8b13be042c8f51a07287ebbe2872936baacfd5b52c8a83dbaf91d6a9" or sha(HERE/"model.py") != base.MODEL_HASH:
        raise AssertionError("frozen source changed")
    out.mkdir(parents=True, exist_ok=False)
    rows = [run_arm(source, alpha_root, out, case) for case in ("flat", "layered")]
    save(out/"result.json", dict(status="SHOT_NOISE_PRIOR_COMPLETE", prior_kind=PRIOR_KIND,
        arms=rows, source_root=str(source), alpha_directory=str(alpha_root), real_photo_admission=False,
        interpretation="Known-alpha, one fixed supplied-noise image-prior change; independent scoring required."))


if __name__ == "__main__":
    main()

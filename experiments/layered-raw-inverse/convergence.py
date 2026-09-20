"""Fixed numerical continuation only; frozen first-screen failure is unchanged."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ARMS = (("flat", "two-layer"), ("far-only", "far-only"), ("layered", "two-layer"))
TRAIN = (0, 1, 3, 4, 5, 7, 8)
HELD = (2, 6)
MODEL_HASH = "5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


class TrainingOnly:
    def __init__(self, array):
        self.array, self.dtype, self.shape = array, array.dtype, array.shape
        self.reads = []

    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        if not isinstance(index, (int, np.integer)) or index not in TRAIN:
            raise AssertionError("optimization attempted a held-out/non-scalar read")
        self.reads.append(int(index))
        return self.array[index]


def run_arm(model, source, out, case, arm):
    original = source/case/arm
    source_files = {"state": original/"state.pt", "receipt": original/"receipt.json",
        "reconstruction": original/"reconstruction.npz", "observations": source/case/"observations-u16.npy",
        "model": HERE/"model.py"}
    source_bindings = {k: dict(path=str(p), sha256=sha(p)) for k, p in source_files.items()}
    old = json.loads((original/"receipt.json").read_text(encoding="utf-8"))
    if tuple(old["train_indices"]) != TRAIN or old["status"] != "iteration_limit":
        raise ValueError("not the frozen 160-step training checkpoint")
    expected_mode = "one-layer" if arm == "far-only" else "two-layer"
    if old["mode"] != expected_mode:
        raise ValueError("checkpoint mode mismatch")
    config = model.Config(**old["config"])
    if config.device != "cuda":
        raise ValueError("this continuation is CUDA only")
    raw = np.load(source/case/"observations-u16.npy", mmap_mode="r", allow_pickle=False)
    observed = TrainingOnly(raw)
    initialized = model.fit(observed, config, TRAIN, mode=expected_mode, optimize=False)
    state = initialized.state
    weights = torch.load(original/"state.pt", map_location=config.device, weights_only=True)
    state.load_state_dict(weights, strict=True)
    if any(not torch.equal(state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("saved checkpoint was not restored exactly")
    if initialized.training_hashes != old["training_sha256"]:
        raise AssertionError("training observation hashes changed")
    restored = model.FitResult(state, config, expected_mode, [], initialized.training_hashes)
    with np.load(original/"reconstruction.npz", allow_pickle=False) as saved:
        for field in ("near_rgb", "far_rgb", "alpha", "pinhole_rgb"):
            if not np.array_equal(saved[field], getattr(restored, field)):
                raise AssertionError("restored state differs from saved reconstruction")
    dest = out/case/arm
    dest.mkdir(parents=True, exist_ok=False)
    optimizer = torch.optim.LBFGS(state.parameters(), lr=1, max_iter=100,
        max_eval=140, history_size=10, tolerance_grad=1e-4,
        tolerance_change=1e-9, line_search_fn="strong_wolfe")
    history, started, evaluations = [], time.monotonic(), 0
    m, scale = config.valid_margin, config.saturation-config.black

    def evaluate(tag):
        nonlocal evaluations
        # Reserve one of the 200 actual evaluations for the final-state monitor.
        limit = 200 if tag == "final" else 199
        if evaluations >= limit:
            raise RuntimeError("hard actual-closure evaluation cap reached")
        evaluations += 1
        record = dict(evaluation=evaluations, tag=tag, evaluation_status="started",
                      elapsed_seconds=time.monotonic()-started)
        history.append(record)
        optimizer.zero_grad(set_to_none=True)
        data = 0.0
        for index in TRAIN:
            near, far, alpha = state.fields()
            depth = config.inverse_depths[1] if expected_mode == "one-layer" else None
            rgb = model.forward(near*scale, far*scale, alpha, config, index, single_depth=depth)
            current = torch.as_tensor(np.array(observed[index], dtype=np.float32, copy=True), device=config.device)
            loss = model.observation_nll(model.cfa(rgb)+config.black, current,
                gain=config.gain, read_variance=config.read_variance,
                black=config.black, saturation=config.saturation)[m:-m, m:-m].mean()/len(TRAIN)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite training likelihood")
            loss.backward()
            data += float(loss.detach())
            del near, far, alpha, rgb, current, loss
        prior = state.prior()
        prior.backward()
        gradient = torch.cat([p.grad.detach().reshape(-1) for p in state.parameters()])
        if not torch.isfinite(prior) or not torch.isfinite(gradient).all():
            raise FloatingPointError("nonfinite unchanged objective/gradient")
        total = data+float(prior.detach())
        record.update(dict(evaluation_status="complete", data_nll=data,
            prior=float(prior.detach()), total=total, gradient_l2=float(torch.linalg.vector_norm(gradient)),
            gradient_max=float(gradient.abs().max()), elapsed_seconds=time.monotonic()-started))
        # LBFGS consumes scalar value and already-populated parameter gradients.
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
        evaluate("final")  # re-evaluate actual returned state, not last line-search trial
        final_record = dict(history[-1])
    except (RuntimeError, FloatingPointError) as exc:
        error, accepted = (error or "")+"; final monitor: "+str(exc), False
        if history[-1]["evaluation_status"] == "started":
            history[-1].update(evaluation_status="refused", error=str(exc))
    status = "numerical_refusal" if error else (
        "stationary_gradient" if final_record["gradient_max"] <= 1e-4 else "nonstationary_return")
    torch.save(state.state_dict(), dest/"state.pt")
    prediction_files = []
    try:
        result = model.FitResult(state, config, expected_mode, history, initialized.training_hashes)
        np.savez_compressed(dest/"reconstruction.npz", near_rgb=result.near_rgb,
            far_rgb=result.far_rgb, alpha=result.alpha, pinhole_rgb=result.pinhole_rgb)
        # Only optical indices are consulted now; no held-out observation is read.
        for index in HELD:
            name = f"predicted-cfa-{index}.npy"
            np.save(dest/name, result.predict(index), allow_pickle=False)
            prediction_files.append(dict(index=index, path=name, sha256=sha(dest/name)))
    except (RuntimeError, FloatingPointError) as exc:
        error, status = (error or "")+"; export: "+str(exc), "numerical_refusal"
        accepted = False
    internal = optimizer.state[next(iter(state.parameters()))]
    if any(sha(p) != source_bindings[k]["sha256"] for k, p in source_files.items()):
        raise AssertionError("arm input changed during continuation")
    receipt = dict(config=old["config"], mode=expected_mode, train_indices=list(TRAIN),
        source_bindings=source_bindings, source_bindings_unchanged=True,
        training_sha256=initialized.training_hashes, source_state_sha256=sha(original/"state.pt"),
        state_sha256=sha(dest/"state.pt"), initial_objective=initial_record,
        final_objective=final_record, closure_history=history, status=status, error=error,
        returned_state_accepted=accepted, optimizer_n_iter=internal.get("n_iter", 0),
        optimizer_func_evals=internal.get("func_evals", 0), actual_evaluations=evaluations,
        completed_evaluations=sum(h["evaluation_status"] == "complete" for h in history),
        wall_seconds=time.monotonic()-started, read_indices=sorted(set(observed.reads)),
        read_count=len(observed.reads), predictions=prediction_files,
        stationarity_scope="raw normalized softplus/logit parameter gradient; no image/truth guarantee")
    save(dest/"receipt.json", receipt)
    print("LAYERED_CONVERGENCE_ARM", json.dumps(dict(case=case, arm=arm, status=status,
          actual_evaluations=evaluations, final_objective=final_record)), flush=True)
    return dict(case=case, arm=arm, status=status, receipt=str(dest/"receipt.json"),
                receipt_sha256=sha(dest/"receipt.json"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    bindings = json.loads((source/"bindings.json").read_text(encoding="utf-8"))
    if sha(HERE/"model.py") != MODEL_HASH or bindings["model_sha256"] != MODEL_HASH:
        raise AssertionError("frozen model changed")
    if sha(HERE/"independent-controls.py") != bindings["controls_sha256"]:
        raise AssertionError("frozen independent controls changed")
    files = [HERE/"model.py", HERE/"design.md", HERE/"independent-controls.py",
             Path(__file__).resolve(), HERE/"convergence-plan.md", source/"bindings.json"]
    for case, arm in ARMS:
        files += [source/case/"observations-u16.npy"]
        files += [source/case/arm/name for name in ("state.pt", "receipt.json", "reconstruction.npz")]
    before = {str(p): sha(p) for p in files}
    out.mkdir(parents=True, exist_ok=False)
    save(out/"bindings-before.json", before)
    spec = importlib.util.spec_from_file_location("layered_frozen_model", HERE/"model.py")
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    started = time.monotonic()
    rows = [run_arm(model, source, out, case, arm) for case, arm in ARMS]
    after = {str(p): sha(p) for p in files}
    save(out/"bindings-after.json", after)
    if before != after:
        raise AssertionError("immutable source/checkpoint/observations changed")
    receipt = dict(status="NUMERICAL_DIAGNOSTIC_COMPLETE", arms=rows,
        source_root=str(source), bindings_unchanged=True, wall_seconds=time.monotonic()-started,
        frozen_first_screen_pass=False, real_photo_admission=False,
        interpretation="Continuation at unchanged objective; original 160-step budget failed. No promotion.")
    save(out/"result.json", receipt)
    print("LAYERED_CONVERGENCE", json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()

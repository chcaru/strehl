"""Read-only physical-radiance directional derivatives at one saved oracle state."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("direction_frozen_visibility", HERE/"visibility-oracle.py")
visibility = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = visibility
spec.loader.exec_module(visibility)
model, base, sha, save, TRAIN = visibility.model, visibility.base, visibility.sha, visibility.save, visibility.TRAIN
STEP = .001


class DirectionalState:
    prior = model._State.prior

    def __init__(self, state, direction, coefficient):
        self.near, self.far, self.alpha = (v.detach() for v in state.fields())
        self.dn_scale, self.gradient_scale = state.dn_scale, state.gradient_scale
        self.direction, self.coefficient = direction/self.dn_scale, coefficient

    def fields(self):
        return self.near, self.far+self.coefficient*self.direction, self.alpha


def measure(state, direction, coefficient, config, observed, gradients):
    t = torch.tensor(coefficient, dtype=torch.float32, device=config.device, requires_grad=gradients)
    current = DirectionalState(state, direction, t)
    near, far, alpha = current.fields()
    if not torch.isfinite(far).all() or (far < 0).any():
        raise ValueError("direction leaves finite nonnegative far-radiance domain; no clamping allowed")
    if coefficient == 0 and not torch.equal(far, state.fields()[1]):
        raise AssertionError("zero direction changed the saved far field")
    pinhole = (alpha[..., None]*near*current.dn_scale+
               (1-alpha[..., None])*far*current.dn_scale).detach().cpu().numpy().copy()
    m, data, data_grad = config.valid_margin, 0.0, 0.0
    for index in TRAIN:
        near, far, alpha = current.fields()
        rgb = model.forward(near*current.dn_scale, far*current.dn_scale, alpha, config, index)
        y = torch.as_tensor(np.array(observed[index], dtype=np.float32, copy=True), device=config.device)
        loss = model.observation_nll(model.cfa(rgb)+config.black, y, gain=config.gain,
            read_variance=config.read_variance, black=config.black,
            saturation=config.saturation)[m:-m, m:-m].mean()/len(TRAIN)
        if not torch.isfinite(loss):
            raise FloatingPointError("nonfinite data objective")
        data += float(loss.detach())
        if gradients:
            data_grad += float(torch.autograd.grad(loss, t)[0])
        del near, far, alpha, rgb, y, loss
    prior = current.prior()
    if not torch.isfinite(prior):
        raise FloatingPointError("nonfinite prior")
    prior_value = float(prior.detach())
    derivative = None
    if gradients:
        prior_grad = float(torch.autograd.grad(prior, t)[0])
        derivative = dict(data_nll=data_grad, prior=prior_grad, total=data_grad+prior_grad)
        if not all(np.isfinite(v) for v in derivative.values()):
            raise FloatingPointError("nonfinite directional derivative")
    return dict(data_nll=data, prior=prior_value, total=data+prior_value), derivative, pinhole


def main():
    parser = argparse.ArgumentParser()
    for name in ("checkpoint", "source", "directions", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    checkpoint, directions, out = args.checkpoint.resolve(), args.directions.resolve(), args.out.resolve()
    receipt = json.loads((checkpoint/"receipt.json").read_text(encoding="utf-8"))
    if (args.source.resolve()/"layered"/"observations-u16.npy") != Path(receipt["source_bindings"]["observations"]["path"]).resolve():
        raise ValueError("source directory differs from checkpoint binding")
    if receipt["visibility"] != "oracle-fixed" or not receipt["returned_state_accepted"] or tuple(receipt["train_indices"]) != TRAIN:
        raise ValueError("requires accepted fixed-visibility training checkpoint")
    if receipt["state_sha256"] != "a4481365ba6ebfa19165770d2fa4b0417d95f1266fe8933152decdeec4310280" or sha(checkpoint/"state.pt") != receipt["state_sha256"]:
        raise ValueError("not the commissioned visibility-1 layered checkpoint")
    if sha(HERE/"visibility-oracle.py") != "b2b718df8b13be042c8f51a07287ebbe2872936baacfd5b52c8a83dbaf91d6a9":
        raise AssertionError("frozen state adapter changed")
    for key in ("model", "comparison", "continuation", "observations", "alpha"):
        bound = receipt["source_bindings"][key]
        if sha(bound["path"]) != bound["sha256"]:
            raise AssertionError("bound source changed: "+key)
    config = model.Config(**receipt["config"])
    weights = torch.load(checkpoint/"state.pt", map_location=config.device, weights_only=True)
    zero = torch.zeros((config.height, config.width, 3), dtype=torch.float32, device=config.device)
    skeleton = model._State(zero, zero, "two-layer", config)
    state = visibility.FixedVisibility(skeleton, weights["fixed_alpha"])
    state.load_state_dict(weights, strict=True)
    state.requires_grad_(False)
    if any(not torch.equal(state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("checkpoint restoration changed values")
    initial = model.FitResult(state, config, "two-layer", [], receipt["training_sha256"])
    with np.load(checkpoint/"reconstruction.npz", allow_pickle=False) as saved:
        if not all(np.array_equal(saved[k], getattr(initial, k)) for k in ("near_rgb", "far_rgb", "alpha", "pinhole_rgb")):
            raise AssertionError("saved state fields did not reproduce")
    observed = base.TrainingOnly(np.load(receipt["source_bindings"]["observations"]["path"], mmap_mode="r", allow_pickle=False))
    out.mkdir(parents=True, exist_ok=False)
    np.save(out/"base-pinhole-rgb-f32.npy", initial.pinhole_rgb, allow_pickle=False)
    results, base_value = {}, None
    for label in ("glint", "shifted-glint"):
        path = directions/f"{label}-dn.npy"
        vector = np.load(path, allow_pickle=False)
        if vector.dtype != np.float32 or vector.shape != zero.shape or not np.isfinite(vector).all() or (vector < 0).any() or not (vector > 0).any():
            raise ValueError("direction must be nonzero finite nonnegative f32 HWC DN")
        d = torch.as_tensor(vector, device=config.device)
        center, derivative, center_image = measure(state, d, 0., config, observed, True)
        if not np.array_equal(center_image, initial.pinhole_rgb):
            raise AssertionError("t0 changed the delivered image")
        for key, value in center.items():
            reference = receipt["final_objective"][key]
            if abs(value-reference) > 1e-6+1e-6*abs(reference):
                raise AssertionError("t0 objective differs from saved final monitor: "+key)
        if base_value is not None and center != base_value:
            raise AssertionError("direction-dependent t0 objective")
        base_value = center
        folder = out/label
        folder.mkdir()
        values = {"zero": center}
        for name, t in (("minus", -STEP), ("plus", STEP)):
            values[name], _, image = measure(state, d, t, config, observed, False)
            np.save(folder/f"{name}-pinhole-rgb-f32.npy", image, allow_pickle=False)
        fd = {k: (values["plus"][k]-values["minus"][k])/(2*STEP) for k in center}
        tolerances = {k: 1e-3+2e-3*abs(derivative[k]) for k in center}
        agreement = {k: abs(fd[k]-derivative[k]) <= tolerances[k] for k in center}
        results[label] = dict(direction_sha256=sha(path), step=STEP, values=values,
            autograd=derivative, central_difference=fd, agreement=agreement,
            derivative_tolerance=tolerances, nonnegative_far_checked=True)
        print("RADIANCE_DIRECTION", json.dumps(dict(label=label, **results[label])), flush=True)
    if any(not torch.equal(state.state_dict()[k], v) for k, v in weights.items()):
        raise AssertionError("read-only probe changed state")
    save(out/"result.json", dict(status="RADIANCE_DIRECTION_COMPLETE", base_objective=base_value,
        directions=results, checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint/"state.pt"),
        state_unchanged=True, read_indices=sorted(set(observed.reads)), read_count=len(observed.reads),
        base_objective_tolerance=dict(absolute=1e-6, relative=1e-6), real_photo_admission=False))


if __name__ == "__main__":
    main()

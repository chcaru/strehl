"""One fixed supplied-phase, dense-pupil original-CFA reconstruction experiment."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
TRAIN, HELD, REFERENCE = (0, 2, 3, 4, 6, 7), (1, 5), 3
PARAMETERS = ["near", "far", "alpha_logit"]
FROZEN = {
    "model.py": "5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512",
    "pupil-stencil.py": "2be60901ed7a3ee8eb007c8611a4d690fe1ecc859ecaf6e375cb5cd0603e14d6",
    "matrix-cauchy-prior.py": "6555432834b543f5102899e4c21931c050ce6994b898e5b0ac74f38b03880b9a",
    "in-focus-consumer.py": "3e75c94dbf0c2f4665f25161751ec28c6ef162ebdd06c5f4f4681b4a1f0fc013",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if any(sha(HERE/name) != expected for name, expected in FROZEN.items()):
    raise AssertionError("frozen model/operator changed")
stencil = load("phase_aware_frozen_stencil", HERE/"pupil-stencil.py")
matrix = load("phase_aware_frozen_matrix", HERE/"matrix-cauchy-prior.py")
consumer = load("phase_aware_frozen_consumer", HERE/"in-focus-consumer.py")
model = stencil.model


def phase_schedule():
    """Common SOURCE displacement -> negative centered period2 latent query."""
    old = HERE.parent/"quality-september14"
    paths = [old/"chip-baseline-1/chip.warpmap.txt", old/"local-green-translation-1/result.json",
             old/"chip-local-sample-diversity-1.json", old/"chip-corrected-sample-diversity-1.json"]
    expected = ["ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922",
                "ed8880a95a4dc7f0af5da6b27968ae74805eb205780d5281c84790c53eac1b6e",
                "72e267c31b84ef78f29405bdf8349498d591c0aede383f9b958a1961df6bc5ba"]
    if [sha(p) for p in paths[:3]] != expected:
        raise AssertionError("phase authority changed")
    mapping = {}
    for line in paths[0].read_text().splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[0].isdigit() and fields[1] == "placed":
            re, im, bx, by = [struct.unpack(">d", bytes.fromhex(v))[0] for v in fields[2:6]]
            mapping[int(fields[0])] = (complex(re, im), complex(bx, by))
    correction = json.loads(paths[1].read_text())
    corrected = {v["frame"]: v for v in correction["frames"]}
    retained = json.loads(paths[3].read_text())["sites"]["centre"]
    if retained["reference_active_native"] != [1527.5, 1299.5]:
        raise AssertionError("fixed reference centre changed")
    point, centre, displacement = complex(1527.5, 1299.5), complex(3516, 2344), []
    for k in range(146, 154):
        if corrected[k]["at_translation_bound"]:
            raise ValueError("bounded-out correction cannot supply a phase")
        a, b = mapping[k]
        # Preserve the retained map's source-native correction arithmetic order.
        d = centre+a*(point-centre)+2*(b+complex(*corrected[k]["delta_source_native"])/2)-point
        displacement.append([d.real, d.imag])
    d = np.asarray(displacement, dtype=np.float64)
    reference = np.asarray([v["mapped_displacement_native"]
        for v in retained["arms"]["corrected-eight"]["frames"]], dtype=np.float64)
    if not np.allclose(d, reference, rtol=0, atol=1e-10):
        raise AssertionError("independent map+correction does not reproduce retained displacement")
    translations = -((d-d[REFERENCE]+1) % 2-1)
    if not np.array_equal(translations[REFERENCE], [0., 0.]):
        raise AssertionError("reference phase is not exactly zero")
    return translations, {str(p): sha(p) for p in paths}


def build_translated_table(pupil_xy, near_shift, far_shift, translation_xy):
    """Same-ray tent products at x+t+d*u; not a post-integration RGB warp."""
    pupil = stencil._pupil(pupil_xy)
    shifts, t = np.asarray([near_shift, far_shift], dtype=np.float64), np.asarray(translation_xy, dtype=np.float64)
    if t.shape != (2,) or not np.isfinite(t).all() or np.any(np.abs(t) > 1):
        raise ValueError("finite common native translation with abs<=1 required")
    if not np.isfinite(shifts).all() or np.any(np.abs(shifts) > 24):
        raise ValueError("finite optical shifts in[-24,24] required")
    def tents(shift):
        position = pupil*shift+t
        lower = np.floor(position).astype(np.int32)
        f = position-lower
        corners = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.int32)
        weights = np.stack(((1-f[:, 0])*(1-f[:, 1]), f[:, 0]*(1-f[:, 1]),
                            (1-f[:, 0])*f[:, 1], f[:, 0]*f[:, 1]), axis=1)
        return lower[:, None, :]+corners[None], weights
    p, pw = tents(shifts[0]); q, qw = tents(shifts[1])
    entries = np.concatenate((np.broadcast_to(p[:, :, None, :], (len(p), 4, 4, 2)),
                              np.broadcast_to(q[:, None, :, :], (len(q), 4, 4, 2))), axis=3).reshape(-1, 4)
    mass = (pw[:, :, None]*qw[:, None, :]/len(pupil)).reshape(-1)
    positive = mass > 0
    offsets, inverse = np.unique(entries[positive], axis=0, return_inverse=True)
    accumulated = np.bincount(inverse, weights=mass[positive], minlength=len(offsets))
    weights = accumulated.astype(np.float32)
    no, ni = np.unique(offsets[:, :2], axis=0, return_inverse=True)
    nw = np.bincount(ni, weights=weights.astype(np.float64), minlength=len(no)).astype(np.float32)
    if not 1 <= len(weights) <= 65536 or np.any(weights <= 0) or not np.isfinite(weights).all():
        raise ValueError("invalid joint table")
    if abs(float(accumulated.sum())-1) > 1e-12 or abs(float(weights.astype(np.float64).sum())-1) > 1e-6:
        raise ArithmeticError("joint mass changed")
    arrays = [np.ascontiguousarray(a) for a in (offsets, weights, no, nw)]
    for a in arrays:
        a.setflags(write=False)
    metadata = dict(pupil_count=len(pupil), pupil_sha256=array_sha(pupil),
        near_shift=float(shifts[0]), far_shift=float(shifts[1]), translation_native=t.tolist(),
        entries=len(weights), near_entries=len(nw), joint_sum_f64=float(accumulated.sum()),
        stored_joint_sum_f64=float(weights.astype(np.float64).sum()), bytes=sum(a.nbytes for a in arrays),
        array_sha256=[array_sha(a) for a in arrays], offset_abs_max=int(np.abs(offsets).max()),
        setup="f64 same-ray translated tent products; storedf32; marginal from stored joint; no renormalization")
    return stencil.JointTable(*arrays, metadata)


def forward(near, far, alpha, config, index, *, table):
    if not 0 <= index < len(config.focus_coordinates) or alpha.shape != (config.height, config.width):
        raise ValueError("invalid optical index/geometry")
    shifts = tuple(config.defocus_scale*(config.focus_coordinates[index]-d) for d in config.inverse_depths)
    if (table.metadata["near_shift"], table.metadata["far_shift"]) != shifts:
        raise ValueError("table focus mismatch")
    return model._blur(stencil.joint_pupil(near.contiguous(), far.contiguous(), alpha.contiguous(), table), config.psf_sigma)


def initialize(codes149, config):
    """Both sheets from the SAME observed training reference; alpha=.5."""
    if codes149.dtype != np.uint16 or codes149.shape != (config.height, config.width) or np.any(codes149 > 16383):
        raise ValueError("original reference uint16 CFA required")
    image = model._interpolate_cfa(codes149, config, config.device)
    return model._State(image.clone(), image.clone(), "two-layer", config).to(config.device)


class TrainingOnly:
    def __init__(self, array):
        if array.dtype != np.uint16 or array.shape != (8, 96, 96):
            raise ValueError("eight original96square uint16 observations required")
        self.array, self.reads = array, []
    def __getitem__(self, index):
        if not isinstance(index, (int, np.integer)) or index not in TRAIN:
            raise AssertionError("held/non-scalar observation read refused")
        self.reads.append(int(index))
        return self.array[index]


def run(data, case, geometry, out):
    manifest_path = data/"manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["schema"] != 1 or tuple(manifest["train_indices"]) != TRAIN or tuple(manifest["held_indices"]) != HELD or manifest["reference_index"] != REFERENCE:
        raise ValueError("fixed eight-source split required")
    config = model.Config(**manifest["config"])
    if (config.width, config.height, config.device) != (96, 96, "cuda") or list(config.focus_coordinates) != [i/7 for i in range(8)] or tuple(config.inverse_depths) != (1., 0.) or config.defocus_scale != 12 or config.psf_sigma != consumer.SIGMA or config.pupil_points is not None:
        raise ValueError("fixed supplied optics/config required; dense pupil lives outside64-ray Config")
    phases, provenance = phase_schedule()
    if not np.allclose(np.asarray(manifest["translations_native"]), phases, rtol=0, atol=1e-10):
        raise AssertionError("generated sampling schedule differs from authority")
    selected = "identity" if geometry == "identity" else "phase"
    paths = dict(manifest=manifest_path, observations=data/manifest["cases"][case][selected], pupil=data/manifest["pupil_path"])
    paths.update({name: HERE/name for name in FROZEN})
    paths.update({"author": HERE/"phase-aware.py", "plan": HERE/"phase-aware-plan.md"})
    paths.update({p: Path(p) for p in provenance})
    bindings = {k: dict(path=str(p.resolve()), sha256=sha(p)) for k, p in paths.items()}
    pupil = np.load(paths["pupil"], allow_pickle=False)
    radial = np.sqrt((np.arange(128, dtype=np.float64)+.5)/128)
    angle = 2*np.pi*(np.arange(128, dtype=np.float64)+.5)/128+.23
    expected = np.stack(np.broadcast_arrays(radial[:, None]*np.cos(angle), radial[:, None]*np.sin(angle)), axis=-1).reshape(-1, 2)
    if pupil.dtype != np.float64 or pupil.shape != (16384, 2) or not np.allclose(pupil, expected, rtol=0, atol=1e-14):
        raise ValueError("fixed16384 equal-area polar pupil phase.23 required")
    observed = TrainingOnly(np.load(paths["observations"], mmap_mode="r", allow_pickle=False))
    training_hashes = [array_sha(observed[i]) for i in TRAIN]
    if any(np.any(observed[i] > config.saturation) for i in TRAIN):
        raise ValueError("original codes exceed digital maximum")
    state = initialize(observed[REFERENCE], config)
    if [n for n, p in state.named_parameters() if p.requires_grad] != PARAMETERS:
        raise AssertionError("all original free-visibility parameters must be trainable")
    tables = [build_translated_table(pupil, *(config.defocus_scale*(f-d) for d in config.inverse_depths),
                                    phases[i] if geometry == "phase" else (0., 0.))
              for i, f in enumerate(config.focus_coordinates)]
    if any(t.metadata["offset_abs_max"]+math.ceil(4*config.psf_sigma) > 16 for t in tables):
        raise ValueError("fixed16:80 score/likelihood interior is unsupported")
    out.mkdir(parents=True, exist_ok=False)
    initial = model.FitResult(state, config, "two-layer", [], training_hashes)
    fields = ("near_rgb", "far_rgb", "alpha", "pinhole_rgb")
    np.savez_compressed(out/"initial-reconstruction.npz", **{f: getattr(initial, f) for f in fields})
    initial_field_sha = {f: array_sha(getattr(initial, f)) for f in fields}
    initial_parameter_sha = {n: array_sha(p.detach().cpu().numpy()) for n, p in state.named_parameters()}
    torch.save(state.state_dict(), out/"initial-state.pt")
    adam = torch.optim.Adam(state.parameters(), lr=.03)
    lbfgs = torch.optim.LBFGS(state.parameters(), lr=1, max_iter=1000, max_eval=1400,
        history_size=10, tolerance_grad=1e-6, tolerance_change=1e-11, line_search_fn="strong_wolfe")
    history, evaluations, progress, started = [], 0, -1, time.monotonic()
    torch.cuda.reset_peak_memory_stats()

    def evaluate(tag, optimizer, step=None):
        nonlocal evaluations, progress
        if tag != "adam":
            if evaluations >= (1800 if tag == "final" else 1799):
                raise RuntimeError("hard1800 LBFGS evaluation cap reached")
            evaluations += 1
        row = dict(tag=tag, evaluation=evaluations, step=step, evaluation_status="started")
        history.append(row)
        optimizer.zero_grad(set_to_none=True)
        data_nll = 0.
        for i in TRAIN:
            near, far, alpha = state.fields()
            rgb = forward(near*state.dn_scale, far*state.dn_scale, alpha, config, i, table=tables[i])
            current = torch.as_tensor(np.array(observed[i], dtype=np.float32, copy=True), device=config.device)
            loss = model.observation_nll(model.cfa(rgb)+config.black, current, gain=config.gain,
                read_variance=config.read_variance, black=config.black, saturation=config.saturation)[16:80, 16:80].mean()/len(TRAIN)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite training likelihood")
            loss.backward(); data_nll += float(loss.detach())
            del near, far, alpha, rgb, current, loss
        prior = matrix.selected_prior(state, config)
        prior.backward()
        gradient = torch.cat([p.grad.detach().reshape(-1) for p in state.parameters()])
        if not torch.isfinite(prior) or not torch.isfinite(gradient).all():
            raise FloatingPointError("nonfinite prior/gradient")
        converted = 0
        for p in state.parameters():
            flat, contiguous = p.grad.detach().reshape(-1), p.grad.contiguous()
            if not torch.equal(flat, contiguous.view(-1)):
                raise AssertionError("gradient storage conversion changed values")
            converted += int(not p.grad.is_contiguous()); p.grad = contiguous
        if torch.cuda.max_memory_allocated() > 8 << 30:
            raise RuntimeError("CUDA allocated memory exceeded8GiB")
        total = data_nll+float(prior.detach())
        iteration = lbfgs.state[state.near].get("n_iter", 0)
        row.update(evaluation_status="complete", data_nll=data_nll, prior=float(prior.detach()), total=total,
            gradient_l2=float(torch.linalg.vector_norm(gradient)), gradient_max=float(gradient.abs().max()),
            optimizer_iteration=iteration, noncontiguous_gradients_converted=converted,
            learning_rate=optimizer.param_groups[0]["lr"], elapsed_seconds=time.monotonic()-started)
        if tag == "adam" and step % 40 == 0 or tag != "adam" and iteration//100 > progress:
            if tag != "adam": progress = iteration//100
            print("PHASE_AWARE_PROGRESS", json.dumps(dict(case=case, geometry=geometry, **row)), flush=True)
        return torch.tensor(total, dtype=torch.float64, device=config.device)

    error, accepted, final = None, True, None
    initial_record, initial_lbfgs = None, None
    try:
        for step in range(160):
            adam.param_groups[0]["lr"] = .001+.5*(.03-.001)*(1+math.cos(math.pi*step/159))
            evaluate("adam", adam, step)
            if step == 0: initial_record = dict(history[-1])
            adam.step()
        evaluate("initial", lbfgs); initial_lbfgs = dict(history[-1])
        lbfgs.step(lambda: evaluate("closure", lbfgs))
    except (RuntimeError, FloatingPointError) as exc:
        error, accepted = str(exc), False
        if history and history[-1]["evaluation_status"] == "started":
            history[-1].update(evaluation_status="refused", error=error)
    try:
        evaluate("final", lbfgs); final = dict(history[-1])
    except (RuntimeError, FloatingPointError) as exc:
        error, accepted = (error or "")+"; final monitor: "+str(exc), False
        if history[-1]["evaluation_status"] == "started": history[-1].update(evaluation_status="refused", error=str(exc))
    status = "numerical_refusal" if error else ("stationary_gradient" if final["gradient_max"] <= 1e-6 else "nonstationary_return")
    torch.save(state.state_dict(), out/"state.pt")
    predictions = []
    try:
        result = model.FitResult(state, config, "two-layer", history, training_hashes)
        np.savez_compressed(out/"reconstruction.npz", **{f: getattr(result, f) for f in fields})
        np.save(out/"pinhole-rgb-f32.npy", result.pinhole_rgb, allow_pickle=False)
        np.save(out/"in-focus-rgb-f32.npy", consumer.apply_in_focus(result.pinhole_rgb), allow_pickle=False)
        with torch.no_grad():
            for i in HELD:
                n, f, a = state.fields()
                value = model.cfa(forward(n*state.dn_scale, f*state.dn_scale, a, config, i, table=tables[i]))+config.black
                name = f"predicted-cfa-{i}.npy"
                np.save(out/name, value.cpu().numpy(), allow_pickle=False)
                predictions.append(dict(index=i, path=name, sha256=sha(out/name)))
    except (RuntimeError, FloatingPointError) as exc:
        error, status, accepted = (error or "")+"; export: "+str(exc), "numerical_refusal", False
    if any(sha(p) != bindings[k]["sha256"] for k, p in paths.items()):
        raise AssertionError("bound source/observation changed")
    internal = lbfgs.state[state.near]
    receipt = dict(case=case, geometry=geometry, observed_geometry=selected, config=manifest["config"],
        dense_pupil=dict(path=str(paths["pupil"]), sha256=sha(paths["pupil"]), count=len(pupil)),
        applied_translations_native=[t.metadata["translation_native"] for t in tables],
        tables=[t.metadata for t in tables], mode="two-layer", prior_kind=matrix.PRIOR_KIND,
        visibility="free-original-sigmoid", train_indices=list(TRAIN), held_indices=list(HELD),
        training_sha256=training_hashes, source_bindings=bindings, source_bindings_unchanged=True,
        observation_sha256=sha(paths["observations"]), state_sha256=sha(out/"state.pt"),
        initial_reference_u16_sha256=array_sha(observed[REFERENCE]),
        initial_parameter_sha256=initial_parameter_sha, initial_field_sha256=initial_field_sha,
        gradient_parameter_names=PARAMETERS, initial_objective=initial_record,
        initial_lbfgs_objective=initial_lbfgs, final_objective=final, closure_history=history,
        status=status, error=error, returned_state_accepted=accepted, actual_evaluations=evaluations,
        hard_evaluation_cap=1800, adam_evaluations=sum(r["tag"] == "adam" for r in history),
        adam_steps_completed=sum(r["tag"] == "adam" and r["evaluation_status"] == "complete" for r in history),
        optimizer_n_iter=internal.get("n_iter", 0), optimizer_func_evals=internal.get("func_evals", 0),
        read_indices=sorted(set(observed.reads)), read_count=len(observed.reads), predictions=predictions,
        peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(), peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),
        wall_seconds=time.monotonic()-started, runtime=stencil.runtime_metadata(), support_native_xywh=[16, 16, 64, 64],
        primary_target="common PSF once after full96 composed pinhole", real_photo_admission=False,
        stationarity_scope="raw normalized softplus/logit parameters, not physical opacity or global optimality")
    save(out/"receipt.json", receipt)
    print("PHASE_AWARE_COMPLETE", json.dumps(dict(case=case, geometry=geometry, status=status,
        receipt_sha256=sha(out/"receipt.json"), wall_seconds=receipt["wall_seconds"])), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--case", choices=("flat", "layered"), required=True)
    parser.add_argument("--geometry", choices=("identity", "phase", "wrong"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.case == "flat" and args.geometry == "wrong":
        raise ValueError("only five prospectively specified fits")
    run(args.data.resolve(), args.case, args.geometry, args.out.resolve())

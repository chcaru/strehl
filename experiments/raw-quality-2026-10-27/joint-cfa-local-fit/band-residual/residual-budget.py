"""One fixed saved-flat residual budget. No fitting or image reconstruction."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PINNED = {
    HERE / "sensor-operator.py": "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac",
    HERE / "controls.py": "094b633678e44e7ebfa63c9648db03c2e3aa182406383b4989d0f42ba7a36120",
    HERE / "fixtures.py": "759f3b7d24ec480ab7158e149eb3030e613c4d3e6ae7000d5dd07644c9ab1ba6",
    ROOT / "outputs/raw-quality-2026-10-27/joint-cfa-band-prepare-1/output/fixture-manifest.json":
        "3ae6d223b9c534a8340a292586b76fc4cf5ce3bcdb49b4ab0c2f120f495c049a",
    ROOT / "outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/result.json":
        "57bd069f0734afc75a7ee597a3ab85fa57059cb094007997e992442083e24668",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding(path, expected=None):
    path = Path(path).resolve()
    stat = path.stat()
    actual = digest(path)
    if expected is not None and actual != expected:
        raise ValueError("changed bound input: " + str(path))
    return dict(path=str(path), sha256=actual, bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def save_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (not args.out.is_absolute() or out.exists()
            or str(out).lower().startswith("d:\\personal\\macro")):
        raise ValueError("fresh absolute output outside capture corpus required")
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(key) != "4":
            raise ValueError(key + " must be4")
    bounds = [binding(path, sha) for path, sha in PINNED.items()]
    bounds.append(binding(__file__))
    # Imports happen only in root's explicitly scheduled process, after binding.
    import numpy as np
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    spec = importlib.util.spec_from_file_location("frozen_budget_controls", HERE / "controls.py")
    controls = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = controls
    spec.loader.exec_module(controls)
    model = controls.load_model(PINNED[HERE / "sensor-operator.py"])
    fixture_path = next(p for p in PINNED if p.name == "fixture-manifest.json")
    result_path = next(p for p in PINNED if p.name == "result.json")
    manifest = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    row, arrays = controls.fx.load_case(manifest, "flat-neutral")
    if (row["id"] != "flat-neutral" or len(arrays) != 7
            or row["noise"]["phase_order"] != ["R", "G1", "G2", "B"]
            or [s["source_id"] for s in row["sources"]] != list(range(7))):
        raise ValueError("fixed flat/phase/source inventory changed")
    for source in row["sources"]:
        bounds.append(binding(source["path"], source["sha256"]))
    for key in ("latent", "output"):
        bounds.append(binding(result[key]["path"], result[key]["sha256"]))
    bounds.append(binding(row["truth"]["path"], row["truth"]["sha256"]))
    saved_x = np.load(result["latent"]["path"], allow_pickle=False)
    saved_output = np.load(result["output"]["path"], allow_pickle=False)
    truth = np.load(row["truth"]["path"], allow_pickle=False)
    if (saved_x.dtype != np.float32 or saved_x.shape != (144, 144, 3)
            or saved_output.dtype != np.float32 or saved_output.shape != (128, 128, 3)
            or truth.dtype != np.float32 or truth.shape != (128, 128, 3)
            or not np.all(truth == np.float32(2048))
            or not np.isfinite(saved_x).all() or not np.isfinite(saved_output).all()):
        raise ValueError("fixed finite saved field/known flat changed")
    config = controls.config_for(model, row)
    if json.loads(json.dumps(config.public())) != result["evidence"]["config"]:
        raise ValueError("consumed model/shape/levels differ from saved fit")
    sources = controls.make_sources(model, row, arrays)
    started = time.perf_counter()
    problem = model.prepare(sources, config, mode="candidate")
    for current, previous in zip(problem.evidence["sources"], result["evidence"]["sources"]):
        for key in ("source_id", "original_u16_sha256", "original_xy_sha256",
                    "footprint_nodes_sha256", "footprint_weights_sha256", "metric_sha256"):
            if current[key] != previous[key]:
                raise ValueError("producing source/operator/weight mismatch: " + key)
    if problem.evidence["metric_scale_f32"] != result["evidence"]["metric_scale_f32"]:
        raise ValueError("global metric scale changed")
    x = torch.from_numpy(saved_x.copy())
    x0 = torch.full_like(x, 2048)
    error = x - x0
    delivered_x = model.integrate_reference(x, config)
    delivered_x0 = model.integrate_reference(x0, config)
    delivered_error = model.integrate_reference(error, config)
    if not np.array_equal(delivered_x.numpy(), saved_output):
        raise ValueError("saved complete delivery did not reproduce exactly")
    out.mkdir(parents=True, exist_ok=False)
    np.save(out / "latent-error.npy", error.numpy(), allow_pickle=False)
    np.save(out / "delivered-error.npy", delivered_error.numpy(), allow_pickle=False)

    def stats(value):
        value = value.reshape(-1)
        if not bool(torch.isfinite(value).all()) or value.numel() == 0:
            raise ValueError("nonfinite/empty budget vector")
        norm = model.norm_pair(value)
        mean_square = norm.scaled(np.float32(1 / value.numel()))
        one = model.SquaredNorm(torch.tensor(.5, dtype=torch.float32), 1)
        return dict(count=value.numel(), mean=float(value.mean()),
                    rms=float(mean_square.root_ratio(one)), minimum=float(value.min()),
                    maximum=float(value.max()), sum_squares=norm.receipt())

    def band_budget(values, variance, metric, factor):
        answer = {}
        for name, value in values.items():
            scaled = model.norm_pair(value * factor)
            answer[name] = dict(raw=stats(value), marginal_sigma_units=stats(value / torch.sqrt(variance)),
                objective_contribution=scaled.scaled(problem.metric_scale).receipt(),
                scaled_objective_contribution=scaled.receipt())
        return dict(metric_min=float(metric.min()), metric_max=float(metric.max()), **answer)

    source_rows, band_rows, aggregate = [], [], {}
    weighted = {key: [] for key in ("signal_error", "noise", "fit_residual")}
    for index, ((measurement, plan), y, variance, metric, factor) in enumerate(zip(
            problem.source_operators, problem.observations, problem.variances,
            problem.metrics, problem.factors)):
        a0 = measurement.forward(x0)
        ax = measurement.forward(x)
        ae = measurement.forward(error)
        noise = y - a0
        residual = ax - y
        phase = torch.from_numpy(sources[index].query.phase.astype(np.int64))
        original_variance = (torch.tensor(config.shot4, dtype=torch.float32)[phase]
            * y.clamp_min(0) + torch.tensor(config.read4, dtype=torch.float32)[phase])
        if bool((original_variance <= 0).any()):
            raise ValueError("sigma-unit report requires the fixed positive model")
        fields = dict(signal_error=ae, noise=noise, fit_residual=residual)
        coefficients = {name: plan.forward(value) for name, value in fields.items()}
        phases = []
        for p in range(4):
            mask = phase == p
            phases.append(dict(phase=p, channel=["R", "G1", "G2", "B"][p],
                injected_sigma_dn=stats(torch.sqrt(original_variance[mask])),
                **{name: dict(dn=stats(value[mask]),
                    injected_temporal_sigma_units=stats(value[mask] / torch.sqrt(original_variance[mask])))
                    for name, value in fields.items()}))
        source_rows.append(dict(source_id=index, phases=phases,
            linear_decomposition_roundoff_dn=stats(residual - (ae - noise)),
            constant_prediction_error_dn=stats(a0 - np.float32(2048))))
        np.savez(out / f"source-{index}-budget.npz", original_variance=original_variance.numpy(),
            q=metric.numpy(), haar_variance=variance.numpy(),
            **{name: value.numpy() for name, value in fields.items()},
            **{"haar_" + name: value.numpy() for name, value in coefficients.items()})
        for name, value in coefficients.items():
            weighted[name].append(value * factor)
        for band in plan.bands:
            lo, hi = band["start"], band["end"]
            values = {name: value[lo:hi] for name, value in coefficients.items()}
            band_rows.append(dict(source_id=index, **band,
                budget=band_budget(values, variance[lo:hi], metric[lo:hi], factor[lo:hi])))
            key = (band["phase"], band["level"], band["kind"])
            bucket = aggregate.setdefault(key, {name: [] for name in
                (*coefficients.keys(), "variance", "metric", "factor")})
            for name, value in values.items():
                bucket[name].append(value)
            for name, value in (("variance", variance), ("metric", metric), ("factor", factor)):
                bucket[name].append(value[lo:hi])
    summaries = []
    for (phase, level, kind), bucket in sorted(aggregate.items()):
        joined = {name: torch.cat(value) for name, value in bucket.items()}
        values = {name: joined[name] for name in weighted}
        summaries.append(dict(phase=phase, level=level, kind=kind,
            budget=band_budget(values, joined["variance"], joined["metric"], joined["factor"])))
    objectives = {name: model.norm_pair(value).scaled(problem.metric_scale).receipt()
                  for name, value in weighted.items()}
    objective_x0 = problem.objective(x0)
    objective_x = problem.objective(x)
    delivery = dict(complete_rgb=stats(delivered_error),
        scored_rgb=stats(delivered_error[16:112, 16:112]),
        scored_channels={name: stats(delivered_error[16:112, 16:112, c])
                         for c, name in enumerate(("R", "G", "B"))},
        delivery_linearity_roundoff_dn=stats(delivered_error - (delivered_x - delivered_x0)),
        constant_delivery_error_dn=stats(delivered_x0 - np.float32(2048)),
        saved_delivery_pixel_exact=True)
    # Recheck every consumed artifact and source after all evaluations.
    for item in bounds:
        if binding(item["path"]) != item:
            raise ValueError("bound bytes/stat changed during residual budget")
    for source, previous in zip(sources, result["evidence"]["sources"]):
        if model._hash(source.codes) != previous["original_u16_sha256"]:
            raise ValueError("original in-memory CFA changed")
    receipt = dict(schema=1, status="COMPLETE_SAVED_FLAT_RESIDUAL_BUDGET", fit_calls=0,
        RAW_reads=0, cpu_workers=torch.get_num_threads(), cuda_math=False,
        wall_seconds=time.perf_counter()-started, inputs=bounds,
        unchanged_inputs_and_source=True, exact_source_and_metric_hashes=True,
        definitions={"X0": "known2048DN continuous flat, all channels including apron",
            "E": "saved latent X minus X0", "signal_error": "A_i E",
            "noise": "n_i=y_i-A_i X0", "fit_residual": "A_i Xsaved-y_i",
            "delivery": "D(E), complete128x128 reference-cell RGB",
            "sigma": "one supplied temporal noise model evaluated on observed signal; no scene spatial SD",
            "band_variance": "marginal Haar variance, no independence or likelihood claim"},
        global_metric_scale=problem.evidence["metric_scale_f32"],
        original_sensel_count=problem.count, config=config.public(),
        objective_known_truth=objective_x0, objective_saved=objective_x,
        saved_last_objective=result["history"][-1], error_budget_objectives=objectives,
        delivered_error=delivery, sources=source_rows,
        per_source_phase_level=band_rows, all_sources_phase_level=summaries,
        complete_fields=[binding(out / "latent-error.npy"), binding(out / "delivered-error.npy")],
        source_arrays=[binding(out / f"source-{i}-budget.npz") for i in range(7)],
        interpretation="Only this measured error direction is tested; no spectral/nullspace proof or reconstructed truth claim.",
        admission=False, quality_claim=False, photographic_admission=False)
    save_json(out / "residual-budget.json", receipt)
    print(json.dumps(dict(status=receipt["status"], fit_calls=0,
        report=str(out / "residual-budget.json"), wall_seconds=receipt["wall_seconds"])), flush=True)


if __name__ == "__main__":
    main()

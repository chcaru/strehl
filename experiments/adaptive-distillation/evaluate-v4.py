"""Development-only tensor fidelity evaluation, including V3 and mismatch controls.

Only validation rows are evaluated. Test/control rows remain untouched.
These metrics describe model outputs, not the quality of rendered photographs.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import torch


def import_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXPORT = import_file(Path(__file__).with_name("export-v4.py"), "strehl_v4_export_helpers")
V4 = EXPORT.V4


def metrics(reference, prediction, key):
    if reference.dtype != np.float32 or prediction.dtype != np.float32 or reference.shape != prediction.shape:
        raise ValueError(f"{key}: metric requires matching FP32 shapes")
    if not np.isfinite(reference).all() or not np.isfinite(prediction).all():
        raise ValueError(f"{key}: metric received non-finite values")
    if key in V4.GAIN_KEYS:
        if not (reference > 0).all() or not (prediction > 0).all():
            raise ValueError("gain metric requires strictly positive fields")
        reference, prediction = np.log2(reference), np.log2(prediction)
    delta = prediction - reference
    absolute = np.abs(delta).reshape(-1)
    rank = max(0, math.ceil(.99 * len(absolute)) - 1)
    return {"mae": float(absolute.mean()), "mse": float(np.mean(delta * delta)),
            "max_absolute": float(absolute.max()), "p99_absolute": float(np.partition(absolute, rank)[rank]),
            "signed_mean": float(delta.mean())}


def aggregate(values):
    return {key: max(row[key] for row in values) if key == "max_absolute" else
            float(np.mean(np.asarray([row[key] for row in values], dtype=np.float32)))
            for key in values[0]}


def donor_assignments(records, selected):
    def source_aliases(record, index):
        aliases = set()
        for key in ("source_id", "source_sha256", "decoded_sha256"):
            if record.get(key) is not None:
                aliases.add((key, str(record[key]).casefold()))
        for key in ("path", "paired_display_render"):
            if record.get(key):
                aliases.add(("path", str(record[key]).replace("\\", "/").casefold()))
        return aliases or {("row", index)}

    identities = {index: source_aliases(records[index], index) for index in selected}
    by_variant = defaultdict(list)
    for index in selected:
        by_variant[str(records[index].get("variant", 0))].append(index)
    result = {}
    for index in selected:
        record = records[index]
        options = [other for other in by_variant[str(record.get("variant", 0))]
                   if not identities[index].intersection(identities[other])]
        cross_group = [other for other in options if records[other]["group_id"] != record["group_id"]]
        options = cross_group or options
        if not options:
            raise ValueError("a distinct-image, same-mask-variant mismatch control does not exist")
        identity = record.get("path", str(index)) + "|" + str(record.get("variant", 0))
        digest = hashlib.sha256(identity.encode()).digest()
        result[index] = options[int.from_bytes(digest[:8], "little") % len(options)]
    return result


def summarize(rows, arms):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["group_id"]].append(row)
    groups = {}
    for group, items in sorted(grouped.items()):
        # First average variants per photograph, then photographs per physical
        # group. Additional synthetic mask variants do not add statistical votes.
        by_source = defaultdict(list)
        for row in items:
            by_source[row["source_identity"]].append(row)
        heads = {key: {arm: aggregate([aggregate([row["heads"][key][arm] for row in variants])
                                     for variants in by_source.values()]) for arm in arms}
                 for key in V4.OUTPUT_NAMES}
        groups[group] = {"records": len(items), "source_count": len(by_source), "heads": heads}
    equal_group = {key: {arm: aggregate([value["heads"][key][arm] for value in groups.values()])
                        for arm in arms} for key in V4.OUTPUT_NAMES}
    for heads in [equal_group, *(group["heads"] for group in groups.values())]:
        for key, values in heads.items():
            for arm in arms:
                values[arm]["rmse"] = math.sqrt(values[arm]["mse"])
                values[arm]["units"] = "log2_gain_stops" if key in V4.GAIN_KEYS else "model_output_units"
                values[arm]["p99_scope"] = "mean of per-image elementwise nearest-rank 99th percentiles, not a pooled percentile"
            baseline, v4 = values["training_mean"]["rmse"], values["v4"]["rmse"]
            values["comparisons"] = {
                "v4_rmse_over_training_mean": v4 / baseline if baseline > 1e-12 else None,
                "mismatch_teacher_rmse": values["wrong_teacher"]["rmse"],
                "correct_assignment_better": v4 < values["v4_against_wrong_teacher"]["rmse"],
                "mismatch_has_resolvable_signal": values["wrong_teacher"]["rmse"] > 1e-12,
                "v4_rmse_over_v3": v4 / values["v3"]["rmse"] if "v3" in arms and values["v3"]["rmse"] > 1e-12 else None}
    return {"groups": groups, "equal_group_heads": equal_group,
            "group_count": len(groups), "sample_mae_tails": {
                key: {arm: {"p95": float(np.quantile([row["heads"][key][arm]["mae"] for row in rows], .95)),
                            "p99": float(np.quantile([row["heads"][key][arm]["mae"] for row in rows], .99)),
                            "max": max(row["heads"][key][arm]["mae"] for row in rows)} for arm in arms}
                for key in V4.OUTPUT_NAMES}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--training-means", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--v3-checkpoint", type=Path)
    parser.add_argument("--v3-source", type=Path, default=Path(__file__).with_name("student.py"))
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if min(args.batch, args.threads) < 1:
        parser.error("batch/threads must be positive")
    if args.output.exists():
        parser.error("output file must not already exist")
    torch.set_num_threads(args.threads)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    manifest_path = args.cache / "manifest.json"
    manifest_hash = EXPORT.sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_contract = EXPORT.INPUT.select_manifest_contract(manifest, manifest_hash)
    records = manifest["records"]
    selected = [index for index, record in enumerate(records) if record["split"] == "validation"]
    if not selected:
        raise ValueError("no development rows selected")
    donors = donor_assignments(records, selected)
    inputs = np.load(args.cache / "inputs.npy", mmap_mode="r", allow_pickle=False)
    if inputs.shape != (len(records), 5, 384, 512) or inputs.dtype not in (np.uint8, np.float32):
        raise ValueError("input cache header differs")
    labels = {key: np.load(args.cache / f"{key}.npy", mmap_mode="r", allow_pickle=False) for key in V4.OUTPUT_NAMES}
    for key, shape in EXPORT.expected_shapes(len(records)).items():
        if labels[key].dtype != np.float32 or labels[key].shape != shape:
            raise ValueError(f"label cache header differs: {key}")
    means = {key: value.numpy() for key, value in torch.load(args.training_means, map_location="cpu", weights_only=True).items()}
    EXPORT.validate_outputs(means)
    v4, checkpoint = EXPORT.load_v4(args.checkpoint)
    EXPORT.assert_checkpoint_input(checkpoint, input_contract)
    means_digest = EXPORT.sha256(args.training_means)
    if checkpoint.get("training_means_sha256") != means_digest:
        raise ValueError("training means are not bound to this checkpoint; migrate a trusted legacy checkpoint with its original fitted-mean digest explicitly")
    device = torch.device(args.device)
    models = {"v4": v4.to(device).eval()}
    if args.v3_checkpoint:
        v3_module = import_file(args.v3_source, "strehl_student_v3_comparison")
        old = torch.load(args.v3_checkpoint, map_location="cpu", weights_only=True)
        EXPORT.assert_checkpoint_input(old, input_contract)
        v3 = v3_module.AdaptiveStudent(v3_module.StudentConfig(**old["config"]))
        v3.load_state_dict(old["state_dict"], strict=True)
        models["v3"] = v3.to(device).eval()
    arms = [*models, "training_mean", "v4_against_wrong_teacher", "wrong_teacher"]
    started, rows = time.perf_counter(), []
    with torch.inference_mode():
        for offset in range(0, len(selected), args.batch):
            ids = selected[offset:offset + args.batch]
            value = EXPORT.INPUT.prepare_numpy(inputs[ids], input_contract)
            if not np.isfinite(value).all() or not ((value >= -2e-6) & (value <= 1 + 2e-6)).all():
                raise ValueError("development inputs violate provisional normalized [0,1] contract")
            tensor = torch.from_numpy(value).to(device)
            predictions = {name: {key: result.cpu().numpy() for key, result in model(tensor).items()}
                           for name, model in models.items()}
            for values in predictions.values():
                EXPORT.validate_outputs(values, len(ids))
            for local, index in enumerate(ids):
                record, donor = records[index], donors[index]
                targets = {key: np.array(labels[key][index:index + 1], copy=True) for key in V4.OUTPUT_NAMES}
                wrong = {key: np.array(labels[key][donor:donor + 1], copy=True) for key in V4.OUTPUT_NAMES}
                EXPORT.validate_outputs(targets)
                EXPORT.validate_outputs(wrong)
                heads = {}
                for key in V4.OUTPUT_NAMES:
                    heads[key] = {name: metrics(targets[key], values[key][local:local + 1], key) for name, values in predictions.items()}
                    heads[key]["training_mean"] = metrics(targets[key], means[key], key)
                    heads[key]["v4_against_wrong_teacher"] = metrics(wrong[key], predictions["v4"][key][local:local + 1], key)
                    heads[key]["wrong_teacher"] = metrics(targets[key], wrong[key], key)
                rows.append({"cache_index": index, "group_id": record["group_id"], "variant": record.get("variant", 0),
                             "original_split": record["split"], "role": "development",
                             "source_identity": str(record.get("source_id") or record.get("paired_display_render") or record.get("path") or index),
                             "wrong_teacher_index": donor, "wrong_teacher_group": records[donor]["group_id"],
                             "mismatch_cross_group": records[donor]["group_id"] != record["group_id"], "heads": heads})
    summary = summarize(rows, arms)
    report = {"scope": "Development tensor fidelity, not a rendered-image or final-test quality claim",
              "failure_directions": ["A constant output can score well when targets vary little; compare exact training means.",
                                     "Uniform tensor error overweights unused gain/LUT coordinates; rendered occupancy is not measured here.",
                                     "Small average error can hide rare defects; per-head/per-group element and sample tails are retained.",
                                     "Mismatch controls test correspondence, not photographic quality or causal correctness."],
              "cache_manifest_sha256": manifest_hash, "checkpoint_sha256": EXPORT.sha256(args.checkpoint),
              "model_input_contract": input_contract, "model_input_contract_sha256": EXPORT.INPUT.contract_sha256(input_contract),
              "training_means_sha256": means_digest, "training_means_bound_to_checkpoint": True,
              "checkpoint_step": checkpoint.get("step"),
              "evaluation_split": "validation", "fresh_final_test_rows_read": False,
              "models_weights_only_load": True, "record_count": len(rows), "seconds": time.perf_counter() - started,
              "mismatch_cross_group_rows": sum(row["mismatch_cross_group"] for row in rows), **summary, "rows": rows}
    if args.v3_checkpoint:
        report["v3_checkpoint_sha256"] = EXPORT.sha256(args.v3_checkpoint)
        report["v3_source_sha256"] = EXPORT.sha256(args.v3_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "records": len(rows), "groups": summary["group_count"],
                      "seconds": report["seconds"], "scope": report["scope"]}, indent=2))


if __name__ == "__main__":
    main()

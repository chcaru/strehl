"""Stream a prepared V4 cache; no teacher execution or test-label access.

The cache contract is manifest records plus inputs.npy and ten FP32 output arrays.
Only training/validation row data are read. All fitted statistics/PCA use training.
Run scheduling, native rendering, and final test evaluation belong to coordinator.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler


SPEC = importlib.util.spec_from_file_location("strehl_student_v4", Path(__file__).with_name("student-v4.py"))
V4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V4
SPEC.loader.exec_module(V4)
INPUT_SPEC = importlib.util.spec_from_file_location("strehl_v4_input_contract", Path(__file__).with_name("input-contract.py"))
INPUT = importlib.util.module_from_spec(INPUT_SPEC)
sys.modules[INPUT_SPEC.name] = INPUT
INPUT_SPEC.loader.exec_module(INPUT)


class CacheDataset(Dataset):
    def __init__(self, cache: Path, indices: list[int]) -> None:
        self.cache, self.indices, self.arrays = cache, indices, None

    def __len__(self) -> int:
        return len(self.indices)

    def open(self):
        if self.arrays is None:
            self.arrays = {key: np.load(self.cache / f"{key}.npy", mmap_mode="r", allow_pickle=False)
                           for key in ("inputs", *V4.OUTPUT_NAMES)}
        return self.arrays

    def __getstate__(self):
        return {**self.__dict__, "arrays": None}

    def __getitem__(self, local: int):
        index, arrays = self.indices[local], self.open()
        image = torch.from_numpy(np.array(arrays["inputs"][index], copy=True))
        labels = {key: torch.from_numpy(np.array(arrays[key][index], copy=True)) for key in V4.OUTPUT_NAMES}
        return image, labels, index


def training_weights(records: list[dict], indices: list[int], macro_share: float, complete_share: float) -> np.ndarray:
    """Equal macro physical-group influence; derivative/augmentation counts do not buy weight."""
    result = np.zeros(len(indices), np.float32)
    macro, general = defaultdict(list), []
    for local, index in enumerate(indices):
        record = records[index]
        if record.get("category") == "macro" or record["group_id"].startswith("macro-"):
            macro[record["group_id"]].append(local)
        else:
            general.append(local)
    macro_mass = macro_share if macro and general else 1.0 if macro else 0.0

    def give(locals_: list[int], mass: float) -> None:
        if not locals_:
            return
        sources = defaultdict(list)
        for local in locals_:
            record = records[indices[local]]
            identity = record.get("source_id") or record.get("paired_display_render") or record.get("path") or str(indices[local])
            sources[str(identity)].append(local)
        for variants in sources.values():
            result[variants] += mass / len(sources) / len(variants)

    give(general, 1 - macro_mass)
    for locals_ in macro.values():
        complete = [local for local in locals_ if records[indices[local]].get("kind", "").startswith("complete_stack")]
        other = [local for local in locals_ if local not in complete]
        mass = macro_mass / len(macro)
        if complete and other:
            give(complete, mass * complete_share)
            give(other, mass * (1 - complete_share))
        else:
            give(locals_, mass)
    if not np.isfinite(result).all() or not (result > 0).all():
        raise ValueError("training sampler produced invalid weights")
    return result / result.sum()


def validate_headers(cache: Path, records: list[dict]) -> np.dtype:
    expected = {**{key: (len(records), 16, 96, 128) for key in V4.GAIN_KEYS},
                **{key: (len(records), 3, 32, 32, 32) for key in V4.LUT_KEYS},
                **{key: (len(records), 1) for key in V4.EXPOSURE_KEYS}}
    for key, shape in expected.items():
        array = np.load(cache / f"{key}.npy", mmap_mode="r", allow_pickle=False)
        if array.shape != shape or array.dtype != np.float32:
            raise ValueError(f"{key} cache contract differs: {array.shape}, {array.dtype}")
    inputs = np.load(cache / "inputs.npy", mmap_mode="r", allow_pickle=False)
    if inputs.shape != (len(records), 5, 384, 512) or inputs.dtype not in (np.uint8, np.float32):
        raise ValueError("input cache must be uint8/FP32 [N,5,384,512]")
    return inputs.dtype


def validate_split_identities(records: list[dict]) -> None:
    """Conservatively reject a physical group or source alias in two splits."""
    seen = {}
    for record in records:
        split = record["split"]
        identities = [("group", str(record["group_id"]))]
        if record.get("source_id") is not None:
            identities.append(("source_id", str(record["source_id"])))
        for field in ("path", "paired_display_render"):
            if record.get(field):
                identities.append(("path", str(record[field]).replace("\\", "/").casefold()))
        for field in ("source_sha256", "decoded_sha256"):
            if record.get(field):
                identities.append((field, str(record[field]).casefold()))
        for identity in identities:
            if identity in seen and seen[identity] != split:
                raise ValueError(f"cross-split source/group identity: {identity}")
            seen[identity] = split


def cache_file_receipt(cache: Path) -> dict:
    """Cheap immutability checks supplement selected-row content hashes."""
    result = {}
    for name in ("manifest.json", *(f"{key}.npy" for key in ("inputs", *V4.OUTPUT_NAMES))):
        stat = (cache / name).stat()
        result[name] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                        "ctime_ns": stat.st_ctime_ns, "inode": stat.st_ino, "device": stat.st_dev}
    return result


def validate_label_values(batch: dict) -> None:
    for key, value in batch.items():
        if not torch.isfinite(value).all():
            raise ValueError(f"non-finite label: {key}")
        if key in V4.GAIN_KEYS and (not (value > 0).all() or not (value.log().abs() <= 12).all()):
            raise ValueError("teacher gain target falls outside model's positive log-gain support")
        if key in V4.LUT_KEYS and not ((value >= -2e-6) & (value <= 1 + 2e-6)).all():
            raise ValueError("teacher color table materially outside [0,1]")


def validation_group_summary(records: list[dict], measurements: list[dict]) -> dict:
    """Average variants within each source, then sources within each group.

    Adding a mask variation must not give its photograph an extra statistical
    vote when choosing the best checkpoint. This matches the final evaluator.
    """
    groups = defaultdict(lambda: defaultdict(list))
    for measured in measurements:
        record = records[measured["row"]]
        identity = str(record.get("source_id") or record.get("paired_display_render")
                       or record.get("path") or measured["row"])
        for family in ("mae", "baseline"):
            if set(measured[family]) != set(V4.OUTPUT_NAMES):
                raise ValueError("validation measurement must include every output")
            if any(not np.isfinite(value) or value < 0 for value in measured[family].values()):
                raise ValueError("validation errors must be finite and nonnegative")
        groups[record["group_id"]][identity].append(measured)
    if not groups:
        raise ValueError("validation measurements must be nonempty")
    return {group: {"count": sum(map(len, sources.values())), "source_count": len(sources),
                    **{family: {key: float(np.mean([
                        np.mean([row[family][key] for row in variants])
                        for variants in sources.values()])) for key in V4.OUTPUT_NAMES}
                       for family in ("mae", "baseline")}}
            for group, sources in groups.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=12000)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--evaluate-every", type=int, default=500)
    parser.add_argument("--macro-share", type=float, default=.5)
    parser.add_argument("--complete-share", type=float, default=.7)
    parser.add_argument("--pca-fit", type=Path, help="reuse a fit from identical training cache/weights only")
    parser.add_argument("--seed", type=int, default=41022)
    args = parser.parse_args()
    if min(args.steps, args.batch, args.rank, args.threads, args.evaluate_every) < 1 or args.workers < 0:
        parser.error("positive training counts required")
    if not 0 < args.macro_share < 1 or not 0 < args.complete_share < 1:
        parser.error("sampling shares must lie strictly between zero and one")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output must be new or empty")
    manifest_path = args.cache / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    input_contract = INPUT.select_manifest_contract(manifest, manifest_digest)
    input_contract_digest = INPUT.contract_sha256(input_contract)
    records = manifest["records"]
    validate_split_identities(records)
    indices = {split: [i for i, record in enumerate(records) if record["split"] == split]
               for split in ("train", "validation")}
    if not all(indices.values()):
        raise ValueError("train and validation must both be nonempty")
    input_dtype = validate_headers(args.cache, records)
    if input_dtype != np.dtype(input_contract["storage_dtype"]):
        raise ValueError("cache input dtype differs from its model-input contract")
    initial_receipt = cache_file_receipt(args.cache)
    divisor = 255.0 if input_dtype == np.uint8 else 1.0
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    device = torch.device(args.device)
    use_pin = device.type == "cuda"
    started = time.perf_counter()
    weights = training_weights(records, indices["train"], args.macro_share, args.complete_share)
    weight_lookup = {index: float(weight) for index, weight in zip(indices["train"], weights)}
    label_arrays = {key: np.load(args.cache / f"{key}.npy", mmap_mode="r", allow_pickle=False) for key in V4.OUTPUT_NAMES}
    input_array = np.load(args.cache / "inputs.npy", mmap_mode="r", allow_pickle=False)
    provenance = {"manifest_sha256": manifest_digest, "model_input_contract_sha256": input_contract_digest,
                  "train_indices_sha256": hashlib.sha256(np.asarray(indices["train"], np.int64).tobytes()).hexdigest(),
                  "weights_sha256": hashlib.sha256(weights.tobytes()).hexdigest(), "rank": args.rank}

    def assert_cache_unchanged():
        if cache_file_receipt(args.cache) != initial_receipt:
            raise ValueError("cache file identity/metadata changed during training")

    def input_preflight(rows: list[int], hasher) -> None:
        values = np.array(input_array[rows], copy=True)
        if values.dtype == np.float32 and (not np.isfinite(values).all() or not ((values >= 0) & (values <= 1)).all()):
            raise ValueError("FP32 predictor input must be finite and normalized to [0,1]")
        hasher.update(values.tobytes(order="C"))

    def label_batches(keys=V4.OUTPUT_NAMES, *, audit=False):
        for offset in range(0, len(indices["train"]), args.batch):
            rows = indices["train"][offset:offset + args.batch]
            batch = {}
            for key in keys:
                values = np.array(label_arrays[key][rows], copy=True)
                if audit:
                    train_hashers[key].update(values.tobytes(order="C"))
                batch[key] = torch.from_numpy(values).to(device)
            if audit:
                validate_label_values(batch)
                input_preflight(rows, train_hashers["inputs"])
            mass = torch.tensor([weight_lookup[index] for index in rows], dtype=torch.float32, device=device)
            yield batch, mass

    # Two streaming passes fit exact weighted full-output means and residual scales.
    centers, normalizers = {}, {}
    train_hashers = {key: hashlib.sha256() for key in ("inputs", *V4.OUTPUT_NAMES)}
    total_mass = 0.0
    for batch, mass in label_batches(audit=True):
        total_mass += float(mass.sum())
        for key, value in batch.items():
            transformed = value.log() if key in V4.GAIN_KEYS else value
            contribution = (transformed * mass.reshape(-1, *([1] * (value.ndim - 1)))).sum(0, keepdim=True)
            centers[key] = centers.get(key, torch.zeros_like(contribution)) + contribution
    centers = {key: value / total_mass for key, value in centers.items()}
    provenance["training_content"] = {
        key: {"sha256": hasher.hexdigest(), "dtype": str(input_dtype if key == "inputs" else np.dtype(np.float32)),
              "shape": [len(indices["train"]), *(input_array if key == "inputs" else label_arrays[key]).shape[1:]]}
        for key, hasher in train_hashers.items()}
    # Only selected validation rows are preflighted; reserved test arrays are never indexed.
    validation_hashers = {key: hashlib.sha256() for key in ("inputs", *V4.OUTPUT_NAMES)}
    for offset in range(0, len(indices["validation"]), args.batch):
        rows = indices["validation"][offset:offset + args.batch]
        input_preflight(rows, validation_hashers["inputs"])
        batch = {}
        for key in V4.OUTPUT_NAMES:
            values = np.array(label_arrays[key][rows], copy=True)
            validation_hashers[key].update(values.tobytes(order="C"))
            batch[key] = torch.from_numpy(values).to(device)
        validate_label_values(batch)
    assert_cache_unchanged()
    audit = {"files": initial_receipt, "train": provenance["training_content"],
             "validation_content_sha256": {key: hasher.hexdigest() for key, hasher in validation_hashers.items()},
             "validation_indices_sha256": hashlib.sha256(np.asarray(indices["validation"], np.int64).tobytes()).hexdigest(),
             "reserved_rows_read": False}
    (args.output / "cache-receipt.json").write_text(json.dumps(audit, indent=2) + "\n")
    for batch, mass in label_batches():
        for key, value in batch.items():
            transformed = value.log() if key in V4.GAIN_KEYS else value
            error = (transformed - centers[key]).abs().flatten(1).mean(1)
            normalizers[key] = normalizers.get(key, 0.0) + float((error * mass).sum()) / total_mass
    normalizers = {key: max(value, .002 if key in V4.GAIN_KEYS else .001 if key in V4.LUT_KEYS else .05)
                   for key, value in normalizers.items()}
    means = {key: value.exp() if key in V4.GAIN_KEYS else value for key, value in centers.items()}
    torch.save({key: value.cpu() for key, value in means.items()}, args.output / "training-means.pt")
    training_means_sha256 = hashlib.sha256((args.output / "training-means.pt").read_bytes()).hexdigest()

    def pca_batches():
        for batch, mass in label_batches(V4.LUT_KEYS):
            yield torch.stack([batch[key] for key in V4.LUT_KEYS], dim=1), mass

    if args.pca_fit:
        saved = torch.load(args.pca_fit, map_location="cpu", weights_only=True)
        if saved["provenance"] != provenance:
            raise ValueError("cached PCA training provenance differs")
        pca = saved["pca"]
    else:
        print(json.dumps({"stage": "fitting_train_only_PCA", "provenance": provenance}), flush=True)
        pca = V4.fit_lut_pca(pca_batches, rank=args.rank, device=str(device), seed=args.seed)
    assert_cache_unchanged()
    torch.save({"pca": pca, "provenance": provenance}, args.output / "pca-fit.pt")
    model = V4.StudentV4(V4.V4Config(lut_rank=args.rank)).to(device)
    model.initialize_from_training(pca,
        gain_log_center=torch.stack([centers[key][0].mean((-2, -1)) for key in V4.GAIN_KEYS]),
        exposure_center=torch.cat([means[key].reshape(1) for key in V4.EXPOSURE_KEYS]),
        exposure_scale=torch.tensor([normalizers[key] for key in V4.EXPOSURE_KEYS], dtype=torch.float32))
    criterion = V4.V4Loss(normalizers)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.0001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, args.steps, eta_min=.00003)
    generator = torch.Generator().manual_seed(args.seed)
    sampler = WeightedRandomSampler(torch.from_numpy(weights), args.steps * args.batch, replacement=True, generator=generator)
    train_loader = DataLoader(CacheDataset(args.cache, indices["train"]), batch_size=args.batch, sampler=sampler,
                              num_workers=args.workers, pin_memory=use_pin, persistent_workers=args.workers > 0)
    validation_loader = DataLoader(CacheDataset(args.cache, indices["validation"]), batch_size=args.batch, shuffle=False,
                                   num_workers=args.workers, pin_memory=use_pin, persistent_workers=args.workers > 0)
    configuration = {"arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                     "model": model.describe(), "provenance": provenance, "normalizers": normalizers,
                     "training_means_sha256": training_means_sha256,
                     "input_divisor": divisor, "domain": manifest.get("domain"), "masks": manifest.get("masks"),
                     "model_input_contract": input_contract, "model_input_contract_sha256": input_contract_digest,
                     "input_contract_implementation_sha256": INPUT.implementation_sha256(),
                     "checkpoint_selection_weighting": "equal groups; equal sources per group; equal variants per source",
                     "train_count": len(indices["train"]), "validation_count": len(indices["validation"])}
    (args.output / "configuration.json").write_text(json.dumps(configuration, indent=2) + "\n")

    @torch.no_grad()
    def evaluate():
        assert_cache_unchanged()
        model.eval()
        validation_rows = []
        sample_errors = defaultdict(list)
        oracle = defaultdict(list)
        for image, batch, rows in validation_loader:
            measured_rows = [{"row": row, "mae": {}, "baseline": {}} for row in rows.tolist()]
            targets = {key: value.to(device, non_blocking=use_pin) for key, value in batch.items()}
            predictions = model(INPUT.prepare_torch(image.to(device, non_blocking=use_pin), input_contract))
            coefficients = model.coefficient_targets(targets) * model.lut_coefficient_scale[None]
            oracle_tables = (coefficients @ model.lut_basis + model.lut_mean[None]).clamp(0, 1)
            for index, key in enumerate(V4.LUT_KEYS):
                target = targets[key].flatten(1)
                oracle[key].extend((oracle_tables[:, index] - target).abs().mean(1).cpu().tolist())
            for key in V4.OUTPUT_NAMES:
                prediction, target, baseline = predictions[key], targets[key], means[key]
                if key in V4.GAIN_KEYS:
                    prediction, target, baseline = prediction.log(), target.log(), baseline.log()
                errors = (prediction - target).abs().flatten(1).mean(1).cpu().tolist()
                baselines = (baseline - target).abs().flatten(1).mean(1).cpu().tolist()
                if not all(np.isfinite(value) for value in errors):
                    raise ValueError(f"non-finite validation prediction: {key}")
                sample_errors[key].extend(errors)
                for measured, error, baseline_error in zip(measured_rows, errors, baselines):
                    measured["mae"][key] = error
                    measured["baseline"][key] = baseline_error
            validation_rows.extend(measured_rows)
        grouped = validation_group_summary(records, validation_rows)
        errors = {key: float(np.mean([value["mae"][key] for value in grouped.values()])) for key in V4.OUTPUT_NAMES}
        baseline = {key: float(np.mean([value["baseline"][key] for value in grouped.values()])) for key in V4.OUTPUT_NAMES}
        ratios = {key: errors[key] / max(baseline[key], normalizers[key] * .05) for key in V4.OUTPUT_NAMES}
        family = {"gain": float(np.mean([ratios[key] for key in V4.GAIN_KEYS])),
                  "lut": float(np.mean([ratios[key] for key in V4.LUT_KEYS])),
                  "exposure": float(np.mean([ratios[key] for key in V4.EXPOSURE_KEYS]))}
        return {"score": float(np.mean(list(family.values()))), "families": family,
                "group_balanced_mae": errors, "group_balanced_baseline": baseline, "groups": grouped,
                "sample_mae_tails": {key: {"p95": float(np.quantile(values, .95)),
                                           "p99": float(np.quantile(values, .99)), "max": float(max(values))}
                                     for key, values in sample_errors.items()},
                "pca_oracle_sample_mean_mae": {key: float(np.mean(values)) for key, values in oracle.items()}}

    def save(step, validation):
        assert_cache_unchanged()
        torch.save({"state_dict": model.state_dict(), "config": dataclasses.asdict(model.config),
                    "step": step, "validation": validation, "normalizers": normalizers, "provenance": provenance,
                    "model_input_contract": input_contract, "model_input_contract_sha256": input_contract_digest,
                    "training_means_sha256": training_means_sha256}, args.output / "best.pt")
        # Verify the actual emitted schema, including statistics, remains loadable
        # through the restricted loader required by export and evaluation.
        torch.load(args.output / "best.pt", map_location="cpu", weights_only=True)

    initial = evaluate()
    best, history = initial["score"], []
    save(0, initial)
    print(json.dumps({"step": 0, "model": model.describe(), "validation": initial["families"]}), flush=True)
    model.train()
    for step, (image, batch, _) in enumerate(train_loader, 1):
        targets = {key: value.to(device, non_blocking=use_pin) for key, value in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        predictions, aux = model.forward_with_aux(INPUT.prepare_torch(image.to(device, non_blocking=use_pin), input_contract))
        with torch.no_grad():
            coefficient_target = model.coefficient_targets(targets)
        losses = criterion(predictions, targets, aux=aux, coefficient_target=coefficient_target)
        if not torch.isfinite(losses["total"]):
            raise ValueError("non-finite training loss")
        losses["total"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5, error_if_nonfinite=True)
        optimizer.step()
        scheduler.step()
        if step % args.evaluate_every == 0 or step == args.steps:
            validation = evaluate()
            record = {"step": step, "seconds": time.perf_counter() - started,
                      "losses": {key: float(value.detach()) for key, value in losses.items()}, "validation": validation}
            history.append(record)
            if validation["score"] < best:
                best = validation["score"]
                save(step, validation)
            (args.output / "training-history.json").write_text(json.dumps({"initial": initial, "history": history}, indent=2) + "\n")
            print(json.dumps({"step": step, "seconds": record["seconds"], "validation": validation["families"], "best": best}), flush=True)
            model.train()
    print(json.dumps({"complete": True, "checkpoint": str(args.output / "best.pt"), "seconds": time.perf_counter() - started}), flush=True)


if __name__ == "__main__":
    main()

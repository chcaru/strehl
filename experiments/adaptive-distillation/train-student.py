"""Train the original FP32 student from an explicitly supplied local tensor cache.

No teacher is opened or executed, and no photograph is discovered or decoded here.
See README.md for the cache contract and the limits of output-space distillation.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from student import (
    AdaptiveStudent, StudentConfig, DistillationLoss, LossConfig, OUTPUT_NAMES,
    GAIN_KEYS, LUT_KEYS, LUT_NUMERICAL_TOLERANCE, output_shapes,
)


def cache_arrays(cache: Path) -> tuple[dict, np.ndarray, dict, dict[str, np.ndarray]]:
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    if not records or not isinstance(manifest.get("domain"), str) or not isinstance(manifest.get("masks"), str):
        raise ValueError("manifest requires nonempty records and explicit domain/masks descriptions")
    groups: dict[str, str] = {}
    for record in records:
        group, split = record.get("group_id"), record.get("split")
        if not isinstance(group, str) or not group or split not in ("train", "validation", "test", "control"):
            raise ValueError("every record needs a nonempty group_id and a recognized split")
        if group in groups and groups[group] != split:
            raise ValueError(f"scene group crosses split boundaries: {group}")
        groups[group] = split
    indices = {split: np.array([i for i, r in enumerate(records) if r["split"] == split], dtype=np.int64)
               for split in ("train", "validation")}
    if any(len(rows) == 0 for rows in indices.values()):
        raise ValueError("nonempty train and validation splits are required")
    inputs = np.load(cache / "inputs.npy", mmap_mode="r", allow_pickle=False)
    if inputs.shape != (len(records), 5, 384, 512) or inputs.dtype not in (np.uint8, np.float32):
        raise ValueError("inputs.npy must be uint8 or FP32 [N,5,384,512]")
    labels = {key: np.load(cache / f"{key}.npy", mmap_mode="r", allow_pickle=False) for key in OUTPUT_NAMES}
    expected = output_shapes(batch=len(records))
    for key, array in labels.items():
        if array.shape != expected[key] or array.dtype != np.float32:
            raise ValueError(f"{key}.npy must be FP32 {expected[key]}")
    # Inspect only selected train/validation rows. Test/control contents stay unread.
    selected = np.concatenate(list(indices.values()))
    for offset in range(0, len(selected), 8):
        rows = selected[offset:offset + 8]
        if not np.isfinite(inputs[rows]).all():
            raise ValueError("non-finite training/validation input")
        for key, array in labels.items():
            values = array[rows]
            if not np.isfinite(values).all():
                raise ValueError(f"non-finite {key} labels")
            if key in GAIN_KEYS and np.any(values <= 0):
                raise ValueError(f"nonpositive {key} gains")
            if key in LUT_KEYS and (np.any(values < -LUT_NUMERICAL_TOLERANCE)
                                     or np.any(values > 1 + LUT_NUMERICAL_TOLERANCE)):
                raise ValueError(f"{key} is materially outside [0,1]")
    return manifest, inputs, labels, indices


def family_mean(values: dict[str, float]) -> dict[str, float]:
    return {"gain": sum(values[key] for key in GAIN_KEYS) / 2,
            "lut": sum(values[key] for key in LUT_KEYS) / 6,
            "exposure": sum(value for key, value in values.items() if key.startswith("exposure")) / 2}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new or empty run directory")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--steps", type=int, default=2400)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--grid", type=int, default=9)
    parser.add_argument("--rank", type=int, default=4)
    parser.add_argument("--shared-residual", action="store_true")
    parser.add_argument("--evaluate-every", type=int, default=100)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args()
    if min(args.steps, args.batch, args.evaluate_every, args.threads) < 1:
        parser.error("steps, batch, evaluate-every, and threads must be positive")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory must be empty; existing runs are never overwritten")
    manifest, input_array, label_arrays, original_split = cache_arrays(args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    device = torch.device(args.device)
    started = time.perf_counter()
    selected = np.concatenate(list(original_split.values()))
    lookup = {int(old): new for new, old in enumerate(selected)}
    split = {name: torch.tensor([lookup[int(i)] for i in rows], device=device)
             for name, rows in original_split.items()}
    # Whole selected cache is resident for a simple, reproducible training loop.
    # Select a small cache or CPU device when accelerator memory is insufficient.
    inputs = torch.from_numpy(input_array[selected].copy()).to(device)
    labels = {key: torch.from_numpy(array[selected].copy()).to(device) for key, array in label_arrays.items()}
    input_divisor = 255.0 if inputs.dtype == torch.uint8 else 1.0
    means, normalizers = {}, {}
    for key, values in labels.items():
        training_values = values[split["train"]]
        transformed = training_values.log() if key in GAIN_KEYS else training_values
        center = transformed.mean(0, keepdim=True)
        means[key] = center.exp() if key in GAIN_KEYS else center
        floor = .002 if key in GAIN_KEYS else .001 if key in LUT_KEYS else .05
        normalizers[key] = max(float((transformed - center).abs().mean()), floor)
    del training_values, transformed, center
    torch.save({key: value.cpu() for key, value in means.items()}, args.output / "training-means.pt")
    model = AdaptiveStudent(StudentConfig(lut_grid=args.grid, lut_rank=args.rank,
                                          shared_training_residual=args.shared_residual)).to(device)
    model.initialize_from_training_means(means)
    criterion = DistillationLoss(LossConfig(exposure_weight=.5, validate_values=False), normalizers)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.0001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, args.steps, eta_min=.00006)
    baseline = {}
    for key in OUTPUT_NAMES:
        target, prediction = labels[key][split["validation"]], means[key]
        if key in GAIN_KEYS:
            target, prediction = target.log(), prediction.log()
        baseline[key] = float((target - prediction).abs().mean())
    config = {
        "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "model": model.describe(), "normalizers": normalizers, "validation_baseline": baseline,
        "torch": torch.__version__, "device": str(device),
        "precision": "FP32; TF32/autocast disabled; cuDNN algorithm selection enabled",
        "domain": manifest["domain"], "masks": manifest["masks"],
        "cache_manifest_sha256": hashlib.sha256((args.cache / "manifest.json").read_bytes()).hexdigest(),
        "input_divisor": input_divisor,
        "counts": {name: len(rows) for name, rows in split.items()},
    }
    (args.output / "configuration.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    @torch.no_grad()
    def evaluate() -> dict:
        model.eval()
        totals, count = {key: 0.0 for key in OUTPUT_NAMES}, 0
        for rows in split["validation"].split(args.batch):
            predictions = model(inputs[rows].float() / input_divisor)
            for key, prediction in predictions.items():
                target = labels[key][rows]
                if key in GAIN_KEYS:
                    prediction, target = prediction.log(), target.log()
                if not torch.isfinite(prediction).all():
                    raise ValueError(f"non-finite validation prediction: {key}")
                totals[key] += float((prediction - target).abs().mean()) * len(rows)
            count += len(rows)
        errors = {key: value / count for key, value in totals.items()}
        ratios = {key: value / max(baseline[key], 1e-8) for key, value in errors.items()}
        scaled = {key: errors[key] / max(baseline[key], normalizers[key] * .05) for key in OUTPUT_NAMES}
        return {"mae": errors, "relative_to_mean": ratios, "families": family_mean(ratios),
                "score": sum(family_mean(scaled).values()) / 3}

    def save_checkpoint(step: int, validation: dict) -> None:
        torch.save({"state_dict": model.state_dict(), "config": dataclasses.asdict(model.config),
                    "step": step, "validation": validation, "normalizers": normalizers}, args.output / "best.pt")

    initial = evaluate()
    best, history = initial["score"], []
    save_checkpoint(0, initial)
    print(json.dumps({"step": 0, "loaded_seconds": time.perf_counter() - started,
                      "model": model.describe(), "validation": initial}), flush=True)
    for step in range(1, args.steps + 1):
        model.train()
        rows = split["train"][torch.randint(len(split["train"]), (args.batch,), device=device)]
        optimizer.zero_grad(set_to_none=True)
        predictions = model(inputs[rows].float() / input_divisor)
        losses = criterion(predictions, {key: value[rows] for key, value in labels.items()})
        if not torch.isfinite(losses["total"]):
            raise ValueError("non-finite training loss")
        losses["total"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0, error_if_nonfinite=True)
        optimizer.step()
        scheduler.step()
        if step % args.evaluate_every == 0 or step == args.steps:
            validation = evaluate()
            record = {"step": step, "elapsed_seconds": time.perf_counter() - started,
                      "training_loss": float(losses["total"].detach()), "validation": validation}
            history.append(record)
            if validation["score"] < best:
                best = validation["score"]
                save_checkpoint(step, validation)
            print(json.dumps({"step": step, "loss": record["training_loss"],
                              "validation": validation["families"], "best": best}), flush=True)
            (args.output / "training-history.json").write_text(
                json.dumps({"initial": initial, "history": history}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"complete": True, "best": best, "seconds": time.perf_counter() - started,
                      "checkpoint": str(args.output / "best.pt")}), flush=True)


if __name__ == "__main__":
    main()

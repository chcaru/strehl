"""Freeze input-only sites, then fit the preregistered source-only USM model.

`sites` opens only four Sharpness-0 source frames.
`model` opens source pairs but refuses every competitive output path.
Neither mode writes a file; frozen literals are committed separately.
"""

from __future__ import annotations

import argparse
import json
import sys

import sharpening_core as sc


def _frozen():
    try:
        import sharpening_frozen as frozen
    except ImportError as exc:
        raise SystemExit("sharpening_frozen.py has not been committed yet") from exc
    return frozen


def sites_mode() -> int:
    result = sc.select_sites()
    print("SOURCE_SITES_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def model_mode() -> int:
    frozen = _frozen()
    selected = sc.select_sites()
    if selected["digest"] != frozen.SITE_DIGEST:
        raise RuntimeError(
            f"source site digest changed: {selected['digest']} != {frozen.SITE_DIGEST}"
        )
    for key in ("flat_0", "flat_1", "detail_0", "detail_1"):
        if selected[key] != getattr(frozen, key.upper()):
            raise RuntimeError(f"frozen site mismatch: {key}")

    train_sites = frozen.FLAT_0 + frozen.DETAIL_0
    holdout_sites = frozen.FLAT_1 + frozen.DETAIL_1
    train = sc.aggregate_transfer(
        sc.SOURCE_0, sc.SOURCE_40, sc.TRAIN_IDS, train_sites
    )
    holdout = sc.aggregate_transfer(
        sc.SOURCE_0, sc.SOURCE_40, sc.HOLDOUT_IDS, holdout_sites
    )
    model, table = sc.fit_model(train, holdout)
    if model.sigma in (0.30, 2.50) or model.amount in (0.00, 3.00):
        raise RuntimeError(f"model optimum is on a grid boundary: {model}")
    train_improvement = 1.0 - model.train_loss / model.train_identity_loss
    holdout_improvement = 1.0 - model.holdout_loss / model.holdout_identity_loss
    rows = sc.source_holdout_rows(holdout_sites, model.sigma, model.amount)
    target = sc.bootstrap_log_ratio(rows["actual_pred"])
    result = {
        "site_digest": frozen.SITE_DIGEST,
        "train_count": train["count"],
        "holdout_count": holdout["count"],
        "sigma": model.sigma,
        "amount": model.amount,
        "train_loss": model.train_loss,
        "train_identity_loss": model.train_identity_loss,
        "train_improvement": train_improvement,
        "holdout_loss": model.holdout_loss,
        "holdout_identity_loss": model.holdout_identity_loss,
        "holdout_improvement": holdout_improvement,
        "holdout_target": target,
        "table_digest": __import__("hashlib").sha256(
            json.dumps(table, separators=(",", ":")).encode("ascii")
        ).hexdigest().upper(),
        "unlicensed": sc.UNLICENSED,
    }
    result["model_green"] = bool(
        train_improvement >= 0.25
        and holdout_improvement >= 0.25
        and target["ci_low"] >= 0.85
        and target["ci_high"] <= 1.15
    )
    print("SOURCE_MODEL_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["model_green"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("sites", "model"))
    args = parser.parse_args(argv)
    sc.source_manifest()
    return sites_mode() if args.mode == "sites" else model_mode()


if __name__ == "__main__":
    sys.exit(main())

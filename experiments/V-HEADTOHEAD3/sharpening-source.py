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
    boundary = model.sigma in (0.30, 2.50) or model.amount in (0.00, 3.00)
    train_improvement = 1.0 - model.train_loss / model.train_identity_loss
    holdout_improvement = 1.0 - model.holdout_loss / model.holdout_identity_loss
    probe_a = sc.green(sc.source_path(sc.SOURCE_0, sc.HOLDOUT_IDS[0]))
    probe_b = sc.green(sc.source_path(sc.SOURCE_40, sc.HOLDOUT_IDS[0]))
    _, _, source_probe = sc.registered_pair(
        probe_a, probe_b, holdout_sites[0], max_shift=8
    )
    source_geometry_nonzero = source_probe[:2] != (0, 0)
    target = None
    source_flat = None
    source_detail = None
    source_hull = None
    if not boundary and not source_geometry_nonzero:
        rows = sc.source_holdout_rows(holdout_sites, model.sigma, model.amount)
        target = sc.bootstrap_log_ratio(rows["actual_pred"])
        n_flat = len(frozen.FLAT_1)
        source_flat = sc.bootstrap_log_ratio(rows["sharp_base"][:n_flat])
        source_detail = sc.bootstrap_log_ratio(rows["sharp_base"][n_flat:])
        source_hull = sc.bootstrap_mean(rows["hull"][:n_flat])
    result = {
        "site_digest": frozen.SITE_DIGEST,
        "train_count": train["count"],
        "holdout_count": holdout["count"],
        "sigma": model.sigma,
        "amount": model.amount,
        "boundary": boundary,
        "source_registration_probe": list(source_probe),
        "source_geometry_nonzero": source_geometry_nonzero,
        "train_loss": model.train_loss,
        "train_identity_loss": model.train_identity_loss,
        "train_improvement": train_improvement,
        "holdout_loss": model.holdout_loss,
        "holdout_identity_loss": model.holdout_identity_loss,
        "holdout_improvement": holdout_improvement,
        "holdout_target": target,
        "source_flat_q25": source_flat,
        "source_detail_q25": source_detail,
        "source_flat_hull": source_hull,
        "table_digest": __import__("hashlib").sha256(
            json.dumps(table, separators=(",", ":")).encode("ascii")
        ).hexdigest().upper(),
        "unlicensed": sc.UNLICENSED,
    }
    result["model_green"] = bool(
        not boundary
        and not source_geometry_nonzero
        and train_improvement >= 0.25
        and holdout_improvement >= 0.25
        and target is not None
        and target["ci_low"] >= 0.85
        and target["ci_high"] <= 1.15
    )
    result["failure_reasons"] = [
        name
        for name, failed in (
            ("grid_boundary", boundary),
            ("source_geometry_nonzero", source_geometry_nonzero),
            ("train_improvement", train_improvement < 0.25),
            ("holdout_improvement", holdout_improvement < 0.25),
            (
                "target_interval",
                target is None
                or target["ci_low"] < 0.85
                or target["ci_high"] > 1.15,
            ),
        )
        if failed
    ]
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

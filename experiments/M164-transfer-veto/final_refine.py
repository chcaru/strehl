"""Run the frozen M164 amendment-3 localization arms."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from scipy import ndimage

import commission as base
import transfer_veto as veto


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "final-refinement.json"
USM_VALUES = (0.0025, 0.0030, 0.0035, 0.0040, 0.0045)
SHIFT_VALUES = (0.0001, 0.0002, 0.0004, 0.0006, 0.0008)


def run() -> dict:
    run1 = json.loads(
        (HERE / "commissioning-run1-pre-clipping-control.json").read_text(
            encoding="utf-8"
        )
    )
    refinement = json.loads(
        (HERE / "refinement.json").read_text(encoding="utf-8")
    )
    crop_records, crops = base.load_crops()
    usm_records: list[dict] = []
    shift_records: list[dict] = []

    for crop_record, scene in zip(crop_records, crops, strict=True):
        crop_id = crop_record["id"]
        prepared = veto.prepare_transfer_veto(scene, base.Q)
        blurred = ndimage.gaussian_filter(
            scene, sigma=1.0, mode="reflect", truncate=4.0
        )
        for amount in USM_VALUES:
            raw = scene + amount * (scene - blurred)
            clipped_samples = int(((raw < 0.0) | (raw > 1.0)).sum())
            record = base.evaluate_prepared(
                prepared,
                raw,
                crop=crop_id,
                radius=1.0,
                amount=amount,
            )
            record["clipped_samples"] = clipped_samples
            usm_records.append(record)
        for distance in SHIFT_VALUES:
            shift_records.append(
                base.evaluate_prepared(
                    prepared,
                    base.interpolation_roundtrip(scene, distance),
                    crop=crop_id,
                    kind="bilinear-shift-roundtrip",
                    distance=distance,
                )
            )
        print(f"final refinement: {crop_id}", flush=True)

    original_usm = [
        record
        for record in run1["unsharp_mask"]["trials"]
        if float(record["amount"]) <= 0.20
    ]
    original_shift = [
        record
        for record in run1["resampling"]["trials"]
        if record["kind"] == "bilinear-shift-roundtrip"
    ]
    amendment2_shift = refinement["resampling_shift_combined"][
        "refinement_trials"
    ]
    usm_strengths = tuple(
        sorted(
            set(
                amount
                for amount in base.USM_AMOUNTS
                if amount <= 0.20
            )
            | set(USM_VALUES)
        )
    )
    shift_strengths = tuple(
        sorted(
            set(base.SHIFT_DISTANCES)
            | set((0.001, 0.002, 0.005, 0.010, 0.020, 0.030, 0.040))
            | set(SHIFT_VALUES)
        )
    )
    result = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "instrument_sha256": base.sha256_file(HERE / "transfer_veto.py"),
        "amendment_sha256": base.sha256_file(HERE / "AMENDMENT-3.md"),
        "original_contrast_unsharp_combined": {
            **base.group_by_strength(
                original_usm + usm_records,
                "amount",
                usm_strengths,
            ),
            "zero_clipped_samples_in_refinement": all(
                record["clipped_samples"] == 0 for record in usm_records
            ),
            "refinement_trials": usm_records,
        },
        "resampling_shift_combined": {
            **base.group_by_strength(
                original_shift + amendment2_shift + shift_records,
                "distance",
                shift_strengths,
            ),
            "refinement_trials": shift_records,
        },
    }
    result["checks"] = {
        "usm_refinement_has_no_clipping": result[
            "original_contrast_unsharp_combined"
        ]["zero_clipped_samples_in_refinement"],
        "usm_has_final_threshold": result[
            "original_contrast_unsharp_combined"
        ]["reliable_threshold"]
        is not None,
        "shift_has_final_threshold": result["resampling_shift_combined"][
            "reliable_threshold"
        ]
        is not None,
    }
    return result


def main() -> int:
    try:
        result = run()
        OUTPUT.write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result["checks"], indent=2, sort_keys=True))
        print(f"wrote {OUTPUT}")
        return 0
    except Exception as error:
        failure = {
            "schema": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "final_refinement_failed": True,
            "error": f"{type(error).__name__}: {error}",
        }
        OUTPUT.write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"FAIL: {failure['error']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

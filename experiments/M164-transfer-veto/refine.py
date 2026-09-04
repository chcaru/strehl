"""Run the frozen M164 amendment-2 refinement battery."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
from scipy import ndimage

import commission as base
import transfer_veto as veto


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "refinement.json"
RUN1 = HERE / "commissioning-run1-pre-clipping-control.json"

BLUR_REFINEMENT = (0.26, 0.27, 0.28, 0.29)
USM_REFINEMENT = (0.0025, 0.0030, 0.0035, 0.0040, 0.0045)
GAIN_REFINEMENT = (0.00012, 0.00014, 0.00016, 0.00018)
SHIFT_REFINEMENT = (0.001, 0.002, 0.005, 0.010, 0.020, 0.030, 0.040)


def clipping_record(values: np.ndarray) -> dict[str, float | int]:
    below = values < 0.0
    above = values > 1.0
    clipped = below | above
    return {
        "samples": int(values.size),
        "clipped_samples": int(np.count_nonzero(clipped)),
        "clipped_fraction": float(np.mean(clipped)),
        "minimum_before_clip": float(values.min()),
        "maximum_before_clip": float(values.max()),
    }


def run() -> dict:
    original = json.loads(RUN1.read_text(encoding="utf-8"))
    crop_records, crops = base.load_crops()

    blur_records: list[dict] = []
    gain_records: list[dict] = []
    shift_records: list[dict] = []
    headroom_records: list[dict] = []
    original_clipping: list[dict] = []

    combined_usm = tuple(sorted(set(base.USM_AMOUNTS + USM_REFINEMENT)))

    for crop_record, scene in zip(crop_records, crops, strict=True):
        crop_id = crop_record["id"]
        prepared = veto.prepare_transfer_veto(scene, base.Q)
        for sigma in BLUR_REFINEMENT:
            image_b = ndimage.gaussian_filter(
                scene, sigma=sigma, mode="reflect", truncate=4.0
            )
            blur_records.append(
                base.evaluate_prepared(
                    prepared, image_b, crop=crop_id, sigma=sigma
                )
            )
        for delta in GAIN_REFINEMENT:
            gain_records.append(
                base.evaluate_prepared(
                    prepared,
                    scene * (1.0 + delta),
                    crop=crop_id,
                    gain_delta=delta,
                )
            )
        for distance in SHIFT_REFINEMENT:
            shift_records.append(
                base.evaluate_prepared(
                    prepared,
                    base.interpolation_roundtrip(scene, distance),
                    crop=crop_id,
                    kind="bilinear-shift-roundtrip",
                    distance=distance,
                )
            )

        original_blur = ndimage.gaussian_filter(
            scene, sigma=1.0, mode="reflect", truncate=4.0
        )
        for amount in base.USM_AMOUNTS:
            raw = scene + amount * (scene - original_blur)
            original_clipping.append(
                {
                    "crop": crop_id,
                    "amount": amount,
                    **clipping_record(raw),
                }
            )

        headroom = base.quantize(0.5 + 0.2 * (scene - 0.5))
        headroom_blur = ndimage.gaussian_filter(
            headroom, sigma=1.0, mode="reflect", truncate=4.0
        )
        headroom_prepared = veto.prepare_transfer_veto(headroom, base.Q)
        for amount in combined_usm:
            raw = headroom + amount * (headroom - headroom_blur)
            clip = clipping_record(raw)
            record = base.evaluate_prepared(
                headroom_prepared,
                raw,
                crop=crop_id,
                radius=1.0,
                amount=amount,
            )
            record.update(clip)
            headroom_records.append(record)
        print(f"refinement arms: {crop_id}", flush=True)

    original_blur_records = original["gaussian_blur"]["trials"]
    original_gain_records = original["scalar_gain"]["trials"]
    original_shift_records = [
        record
        for record in original["resampling"]["trials"]
        if record["kind"] == "bilinear-shift-roundtrip"
    ]

    combined_blur_strengths = tuple(
        sorted(set(base.BLUR_SIGMAS + BLUR_REFINEMENT))
    )
    combined_gain_strengths = tuple(
        sorted(set(base.GAIN_DELTAS + GAIN_REFINEMENT))
    )
    combined_shift_strengths = tuple(
        sorted(set(base.SHIFT_DISTANCES + SHIFT_REFINEMENT))
    )
    result = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "run1_sha256": base.sha256_file(RUN1),
        "instrument_sha256": base.sha256_file(HERE / "transfer_veto.py"),
        "amendment_sha256": base.sha256_file(HERE / "AMENDMENT-2.md"),
        "gaussian_blur_combined": {
            **base.group_by_strength(
                original_blur_records + blur_records,
                "sigma",
                combined_blur_strengths,
            ),
            "refinement_trials": blur_records,
        },
        "scalar_gain_combined": {
            **base.group_by_strength(
                original_gain_records + gain_records,
                "gain_delta",
                combined_gain_strengths,
            ),
            "refinement_trials": gain_records,
        },
        "resampling_shift_combined": {
            **base.group_by_strength(
                original_shift_records + shift_records,
                "distance",
                combined_shift_strengths,
            ),
            "refinement_trials": shift_records,
        },
        "clipping_free_unsharp_mask": {
            **base.group_by_strength(
                headroom_records,
                "amount",
                combined_usm,
            ),
            "zero_clipped_samples": all(
                record["clipped_samples"] == 0 for record in headroom_records
            ),
            "trials": headroom_records,
        },
        "original_unsharp_clipping_audit": {
            "by_amount": {
                f"{amount:g}": {
                    "trials_with_clipping": sum(
                        record["clipped_samples"] > 0
                        for record in original_clipping
                        if record["amount"] == amount
                    ),
                    "total_clipped_samples": sum(
                        record["clipped_samples"]
                        for record in original_clipping
                        if record["amount"] == amount
                    ),
                    "maximum_clipped_fraction": max(
                        record["clipped_fraction"]
                        for record in original_clipping
                        if record["amount"] == amount
                    ),
                }
                for amount in base.USM_AMOUNTS
            },
            "trials": original_clipping,
        },
    }
    result["checks"] = {
        "headroom_has_no_clipping": result["clipping_free_unsharp_mask"][
            "zero_clipped_samples"
        ],
        "headroom_sharpening_has_reliable_threshold": result[
            "clipping_free_unsharp_mask"
        ]["reliable_threshold"]
        is not None,
        "blur_has_refined_threshold": result["gaussian_blur_combined"][
            "reliable_threshold"
        ]
        is not None,
        "gain_has_refined_threshold": result["scalar_gain_combined"][
            "reliable_threshold"
        ]
        is not None,
        "shift_has_refined_threshold": result["resampling_shift_combined"][
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
            "refinement_failed": True,
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

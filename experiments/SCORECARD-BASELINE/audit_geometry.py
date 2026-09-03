from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from common import OUT, WORK, write_json
from measure import output_luma


PAIRS = {
    "m1-bright-a12": "bright_reference8.npy",
    "m1-bright-b12": "bright_reference8.npy",
    "m1-second-a12": "second_reference8.npy",
    "m1-second-b12": "second_reference8.npy",
    "m2-bright-first16": "bright_second16.npy",
    "m2-bright-second16": "bright_first16.npy",
    "m2-second-first16": "second_second16.npy",
    "m2-second-second16": "second_first16.npy",
}


def estimate(reference: np.ndarray, moving: np.ndarray, downsample: int = 8) -> dict[str, object]:
    height, width = reference.shape
    size = (width // downsample, height // downsample)
    ref = cv2.resize(
        np.asarray(reference, dtype=np.float32),
        size,
        interpolation=cv2.INTER_AREA,
    )
    mov = cv2.resize(
        np.asarray(moving, dtype=np.float32),
        size,
        interpolation=cv2.INTER_AREA,
    )
    ref = (ref - float(np.mean(ref))) / max(float(np.std(ref)), 1e-9)
    mov = (mov - float(np.mean(mov))) / max(float(np.std(mov)), 1e-9)
    warp = np.eye(2, 3, dtype=np.float32)
    correlation, warp = cv2.findTransformECC(
        ref,
        mov,
        warp,
        cv2.MOTION_AFFINE,
        (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
            300,
            1e-8,
        ),
        None,
        5,
    )
    linear = warp[:, :2].astype(np.float64)
    singular = np.linalg.svd(linear, compute_uv=False)
    scale = math.sqrt(abs(float(np.linalg.det(linear))))
    rotation = math.degrees(
        math.atan2(
            float(linear[1, 0] - linear[0, 1]),
            float(linear[0, 0] + linear[1, 1]),
        )
    )
    return {
        "correlation": float(correlation),
        "matrix_downsampled": warp.tolist(),
        "isotropic_scale": scale,
        "scale_disagreement_percent": 100.0 * abs(scale - 1.0),
        "rotation_deg": rotation,
        "singular_values": singular.tolist(),
        "anisotropy_percent": 100.0 * abs(float(singular[0] - singular[1])),
        "translation_yx_fullres": [
            float(warp[1, 2] * downsample),
            float(warp[0, 2] * downsample),
        ],
        "scorecard_scale_pass": abs(scale - 1.0) <= 0.001,
        "scorecard_rotation_pass": abs(rotation) <= 0.02,
    }


def synthetic(side: int = 1024) -> np.ndarray:
    rng = np.random.default_rng(5511)
    image = rng.normal(size=(side, side)).astype(np.float32)
    return cv2.GaussianBlur(image, (0, 0), 2.0)


def commission() -> dict[str, object]:
    image = synthetic()
    height, width = image.shape
    identity = estimate(image, image)
    translation_matrix = np.asarray([[1.0, 0.0, 3.0], [0.0, 1.0, -2.0]], np.float32)
    translated = cv2.warpAffine(
        image,
        translation_matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )
    translation_null = estimate(image, translated)
    planted_matrix = cv2.getRotationMatrix2D(
        ((width - 1) / 2.0, (height - 1) / 2.0),
        0.015,
        1.003,
    )
    planted_matrix[:, 2] += np.asarray([2.0, -1.0])
    planted = cv2.warpAffine(
        image,
        planted_matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )
    scale_plant = estimate(image, planted)
    null_green = (
        identity["scale_disagreement_percent"] <= 0.02
        and translation_null["scale_disagreement_percent"] <= 0.02
    )
    plant_red = (
        not scale_plant["scorecard_scale_pass"]
        and abs(scale_plant["isotropic_scale"] - 1.003) <= 0.0005
    )
    return {
        "identity_null": identity,
        "translation_null": translation_null,
        "scale_rotation_plant": scale_plant,
        "null_stayed_green": null_green,
        "plant_went_red": plant_red,
        "commissioned": null_green and plant_red,
    }


def main() -> int:
    commissioning = commission()
    if not commissioning["commissioned"]:
        write_json(OUT / "GEOMETRY-AUDIT.json", {"commissioning": commissioning})
        raise RuntimeError("geometry scale audit did not commission")
    rows = []
    for name, reference_name in PAIRS.items():
        reference = np.load(WORK / "input-cache" / reference_name, mmap_mode="r")
        moving = output_luma(OUT / "renders" / f"{name}.tiff")
        rows.append(
            {
                "render": name,
                "reference": reference_name,
                **estimate(reference, moving),
            }
        )
    result = {
        "status": "POST_SCORE_REJECTION_AUDIT_NOT_A_V1_1_SCORE",
        "reason": (
            "The pre-registered 0.10% scale threshold is applied, but this conventional "
            "external estimator was added after first score bytes and therefore only "
            "invalidates; it cannot rescue or score the arms."
        ),
        "commissioning": commissioning,
        "rows": rows,
        "all_scale_invalid": all(not row["scorecard_scale_pass"] for row in rows),
    }
    write_json(OUT / "GEOMETRY-AUDIT.json", result)
    for row in rows:
        print(
            row["render"],
            f"scale disagreement={row['scale_disagreement_percent']:.4f}%",
            f"rotation={row['rotation_deg']:.5f}deg",
            f"corr={row['correlation']:.6f}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

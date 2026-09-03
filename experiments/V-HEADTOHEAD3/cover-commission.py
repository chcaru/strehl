"""Commission the author cover-mode instrument before the treatment render."""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage, signal

import cover_core as cc
from ordinal import _scale_score, midrank_field


class Recorder:
    def __init__(self) -> None:
        self.controls = 0
        self.plants = 0
        self.failed: list[str] = []

    def control(self, name: str, ok: bool, reading: str) -> None:
        self.controls += 1
        print(f"CONTROL {'GREEN' if ok else 'FAIL '} {name}: {reading}")
        if not ok:
            self.failed.append("control " + name)

    def plant(self, name: str, caught: bool, reading: str) -> None:
        self.plants += 1
        print(f"PLANT   {'RED  ' if caught else 'MISS '} {name}: {reading}")
        if not caught:
            self.failed.append("plant " + name)

    def finish(self) -> int:
        if self.failed:
            print("COVER COMMISSION FAILED: " + ", ".join(self.failed))
            return 1
        print(
            f"COVER COMMISSION GREEN: {self.controls}/{self.controls} controls GREEN; "
            f"{self.plants}/{self.plants} plants RED"
        )
        return 0


def fixture(n: int = 256, seed: int = 311) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:n, :n]
    return (
        0.8 * np.sin(2 * np.pi * x / 23)
        + 0.5 * np.sin(2 * np.pi * (x + y) / 9)
        + 0.35 * np.sin(2 * np.pi * (2 * x - y) / 6)
        + 0.2 * (x > n // 2)
        + rng.normal(0, 0.18, (n, n))
    )


def direct_usm(a: np.ndarray, sigma: float = 1.0, amount: float = 1.4) -> np.ndarray:
    radius = int(math.ceil(4 * sigma))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= np.sum(kernel)
    blurred = signal.convolve2d(
        a,
        np.outer(kernel, kernel),
        mode="same",
        boundary="symm",
    )
    return a + amount * (a - blurred)


def fitted_scale(reference: np.ndarray, moving: np.ndarray) -> tuple[float, bool]:
    rr = midrank_field(reference)
    mr = midrank_field(moving)
    coarse = np.arange(0.94, 1.0801, 0.005)
    scores = [_scale_score(rr, mr, float(scale))[0] for scale in coarse]
    best = int(np.argmax(scores))
    centre = float(coarse[best])
    fine = np.arange(centre - 0.005, centre + 0.00501, 0.001)
    fine_scores = [_scale_score(rr, mr, float(scale))[0] for scale in fine]
    selected = int(np.argmax(fine_scores))
    return float(fine[selected]), bool(
        0 < best < len(coarse) - 1 and 0 < selected < len(fine) - 1
    )


def schema_ok(payload: dict) -> bool:
    expected = set(cc.BAND_NAMES) | {"gt_0.25"}
    return (
        set(payload) == expected
        and payload["gt_0.25"] == cc.UNLICENSED
        and all(
            isinstance(payload[name], (float, int)) for name in cc.BAND_NAMES
        )
    )


def main() -> int:
    r = Recorder()
    caps = {
        name: int(os.environ.get(name, "8"))
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        )
    }
    r.control(
        "maximum eight numerical threads",
        all(1 <= value <= 8 for value in caps.values()),
        str(caps),
    )

    # Fixed external bin membership, including a cap mutant.
    membership = [
        [
            index
            for index, (lo, hi) in enumerate(cc.BANDS)
            if lo <= frequency < hi
        ]
        for frequency in (0.03125, 0.078125, 0.15625, 0.234375)
    ]
    rejected = not any(lo <= 0.28125 < hi for lo, hi in cc.BANDS)
    r.control(
        "four-band fixed-bin oracle",
        membership == [[0], [1], [2], [3]] and rejected,
        f"membership={membership}, 0.28125 rejected={rejected}",
    )
    mutant_accepts = any(
        lo <= 0.28125 < hi for lo, hi in cc.BANDS + ((0.25, 0.30),)
    )
    r.plant(
        "above-cap fifth band",
        mutant_accepts and rejected,
        f"mutant accepts 0.28125={mutant_accepts}",
    )

    image = fixture()
    base = np.asarray(cc.rank_energy(image), np.float64)
    curves = {
        "affine": 2.1 * image + 4.0,
        "gamma3": (image - np.min(image) + 1e-9) ** 3,
        "logistic": 1.0 / (1.0 + np.exp(-3.0 * (image - np.median(image)))),
    }
    tone_moves = {
        name: float(
            np.max(np.abs(np.asarray(cc.rank_energy(value), np.float64) - base))
        )
        for name, value in curves.items()
    }
    r.control(
        "strict point-tone invariance",
        max(tone_moves.values()) <= 1e-12,
        ", ".join(f"{name}={move:.3e}" for name, move in tone_moves.items()),
    )
    raw_base = np.asarray(cc.raw_energy(image))
    raw_move = max(
        float(np.max(np.abs(np.asarray(cc.raw_energy(value)) / raw_base - 1)))
        for value in curves.values()
    )
    r.plant(
        "raw-power substitution",
        raw_move >= 0.05,
        f"raw max move={raw_move:.3f}",
    )

    identity = np.asarray(cc.rank_energy(image.copy()), np.float64)
    blurred = np.asarray(
        cc.rank_energy(ndimage.gaussian_filter(image, 1.2, mode="reflect")),
        np.float64,
    )
    sharpened = np.asarray(cc.rank_energy(direct_usm(image)), np.float64)
    blur_ratio = float(blurred[2] / base[2])
    usm_ratio = float(sharpened[2] / base[2])
    r.control(
        "identity plus bidirectional reach",
        np.array_equal(identity, base)
        and blur_ratio < 0.95
        and usm_ratio > 1.05,
        f"identity={np.max(abs(identity-base)):.3e}, "
        f"blur={blur_ratio:.4f}, USM={usm_ratio:.4f}",
    )
    r.plant(
        "disabled blur",
        not (float(identity[2] / base[2]) < 0.95),
        "identity mutant fails degradation bar",
    )
    r.plant(
        "disabled USM",
        not (float(identity[2] / base[2]) > 1.05),
        "identity mutant fails improvement bar",
    )

    # Known translation and sign.
    shifted = np.roll(image, (5, -7), axis=(0, 1))
    correction = cc.phase_correction(
        midrank_field(image), midrank_field(shifted), max_shift=12
    )
    aa, bb = cc.overlap_after_shift(image, shifted, correction[:2])
    r.control(
        "known translation correction",
        correction[:2] == (-5, 7) and np.array_equal(aa, bb),
        f"expected={(-5,7)}, got={correction[:2]}",
    )
    wrong_a, wrong_b = cc.overlap_after_shift(image, shifted, (5, -7))
    noop_a, noop_b = cc.overlap_after_shift(image, shifted, (0, 0))
    r.plant(
        "wrong registration sign",
        not np.array_equal(wrong_a, wrong_b),
        "wrong sign fails source equality",
    )
    r.plant(
        "registration no-op",
        not np.array_equal(noop_a, noop_b),
        "zero shift fails source equality",
    )

    # Same-sized content with a planted scale defeats dimension inference.
    pmax = fixture(320, 917)
    truth = 1.035
    enlarged = ndimage.zoom(pmax, truth, order=1, mode="reflect", prefilter=False)
    arm = enlarged[11:-13, 17:-7]
    recovered, interior = fitted_scale(arm, pmax)
    dimension = 0.5 * (
        arm.shape[0] / pmax.shape[0] + arm.shape[1] / pmax.shape[1]
    )
    r.control(
        "image-measured planted scale",
        interior and abs(recovered - truth) <= 0.003,
        f"truth={truth:.4f}, fitted={recovered:.4f}, dimensions={dimension:.4f}",
    )
    r.plant(
        "dimension-assumed scale",
        abs(dimension - truth) > 0.01 and abs(recovered - truth) <= 0.003,
        f"dimension={dimension:.4f}, image-fit={recovered:.4f}",
    )

    # Exact crop-origin mapping and all four neighbouring mutants.
    source = np.arange(180 * 220, dtype=np.int64).reshape(180, 220)
    origin = np.asarray((23, 31))
    emitted = source[23 : 23 + 120, 31 : 31 + 140]
    source_centre = np.asarray((83, 101))
    expected = cc.crop_centered(source, *source_centre, 48)
    mapped = source_centre - origin
    actual = cc.crop_centered(emitted, *mapped, 48)
    r.control(
        "exact centred crop mapping",
        expected is not None and np.array_equal(expected, actual),
        f"origin={origin.tolist()}, mapped={mapped.tolist()}",
    )
    for label, delta in (
        ("origin y-1", (-1, 0)),
        ("origin y+1", (1, 0)),
        ("origin x-1", (0, -1)),
        ("origin x+1", (0, 1)),
    ):
        mutant = cc.crop_centered(
            emitted,
            *(source_centre - (origin + np.asarray(delta))),
            48,
        )
        r.plant(
            label,
            mutant is not None and not np.array_equal(expected, mutant),
            "one-pixel origin mutant differs",
        )

    sites = [
        {"centre": [600 + 20 * i, 700 + 17 * i], "label": "detail"}
        for i in range(12)
    ] + [
        {"centre": [900 + 20 * i, 1100 + 17 * i], "label": "flat"}
        for i in range(6)
    ]
    digest = cc.site_digest(sites)
    changed = [dict(row) for row in sites]
    changed[0] = {"centre": [601, 700], "label": "detail"}
    r.control(
        "input-fixed site digest",
        digest == cc.site_digest(sites),
        digest[:16],
    )
    r.plant(
        "post-treatment site reselection",
        cc.site_digest(changed) != digest,
        "changed centre changes digest",
    )
    clearance = min(240, 600, 1200 - 680, 1200 - 640)
    r.plant(
        "omitted border clearance",
        clearance < cc.BORDER,
        f"bounds-only mutant admits clearance={clearance}",
    )

    payload = {
        **{name: float(base[index]) for index, name in enumerate(cc.BAND_NAMES)},
        "gt_0.25": cc.UNLICENSED,
    }
    r.control("strict capped schema", schema_ok(payload), json.dumps(payload))
    r.control(
        "epsilon-above-cap rejection",
        cc.rank_energy(image, 1.0 - 2e-12)[3] is None,
        "0.25/(1-2e-12) is unlicensed",
    )
    mutant_payload = dict(payload)
    mutant_payload["gt_0.25"] = 0.28125
    r.plant(
        "numeric above-cap output",
        not schema_ok(mutant_payload),
        "numeric sentinel mutation rejected",
    )

    scale_path = cc.SCALE_MASTER
    crop_path = cc.PMAX["113-sharp"]
    pmax_path = cc.PMAX["113"]
    scale_log = (
        "alignment       : ON, 63 placed / 0 refused\n"
        "coverage        : field of view scaled to 0.9970 so that EVERY frame covers"
    )
    crop_log = (
        "alignment       : ON, 63 placed / 0 refused\n"
        "coverage        : CROPPED to the region EVERY frame covers -- "
        "3490 x 2320 plane px at (13, 12) of 3516 x 2344, "
        "emitted at UNITY SCALE. dropped and NOT upsampled (k=0.9926)"
    )
    manifest_digest = "A" * 64
    provenance = {
        "schema": cc.PROVENANCE_SCHEMA,
        "executable": {
            "path": str(cc.EXE),
            "sha256": cc.HASHES[cc.EXE],
        },
        "source": {
            "path": str(cc.SOURCE),
            "pre": {
                "digest": manifest_digest,
                "counts": {".arw": 63, ".xmp": 63},
            },
            "post": {
                "digest": manifest_digest,
                "counts": {".arw": 63, ".xmp": 63},
            },
        },
        "comparators": {
            name: cc.HASHES[path] for name, path in cc.PMAX.items()
        },
        "environment": {
            "effective_strehl": {
                "STREHL_CACHE_DIR": str(
                    (Path(__file__).resolve().parent / "out" / "cache").resolve()
                )
            },
            "rayon_num_threads": 8,
            "numeric_thread_caps": {
                "OMP_NUM_THREADS": 8,
                "OPENBLAS_NUM_THREADS": 8,
                "MKL_NUM_THREADS": 8,
                "NUMEXPR_NUM_THREADS": 8,
            },
        },
        "arms": {
            "scale": {
                "path": str(scale_path.resolve()),
                "argv": cc.render_argv("scale", scale_path),
                "exit_code": 0,
                "sha256": cc.HASHES[scale_path],
                "facts": cc.parse_render_log(scale_log, "scale"),
                "log": scale_log,
            },
            "crop": {
                "path": str(crop_path.resolve()),
                "argv": cc.render_argv("crop", crop_path),
                "exit_code": 0,
                "sha256": cc.HASHES[crop_path],
                "facts": cc.parse_render_log(crop_log, "crop"),
                "log": crop_log,
            },
        },
    }

    def accepted(
        document: dict,
        frozen_hash: str = cc.HASHES[pmax_path],
        frozen_scale_hash: str = cc.HASHES[scale_path],
        frozen_subject: str = "113",
    ) -> bool:
        try:
            cc.validate_provenance(
                document,
                crop_path,
                scale_path,
                pmax_path,
                frozen_hash,
                frozen_scale_hash,
                frozen_subject,
                verify_live_source=False,
            )
            return True
        except ValueError:
            return False

    r.control(
        "live-file-bound provenance null",
        accepted(provenance),
        "frozen executable/scale/comparator files accepted",
    )

    def provenance_mutant(change: object) -> bool:
        document = json.loads(json.dumps(provenance))
        change(document)
        return not accepted(document)

    provenance_mutations = (
        (
            "changed executable hash",
            lambda d: d["executable"].__setitem__("sha256", "0" * 64),
        ),
        (
            "changed comparator hash",
            lambda d: d["comparators"].__setitem__("113", "0" * 64),
        ),
        (
            "swapped comparator labels",
            lambda d: d.__setitem__(
                "comparators",
                {
                    "113": d["comparators"]["113-sharp"],
                    "113-sharp": d["comparators"]["113"],
                },
            ),
        ),
        (
            "extra render flag",
            lambda d: d["arms"]["crop"]["argv"].append("--auto-exposure"),
        ),
        (
            "inherited STREHL environment",
            lambda d: d["environment"]["effective_strehl"].__setitem__(
                "STREHL_COVER", "scale"
            ),
        ),
        (
            "excess numerical threads",
            lambda d: d["environment"]["numeric_thread_caps"].__setitem__(
                "OMP_NUM_THREADS", 99
            ),
        ),
        (
            "changed source post-manifest",
            lambda d: d["source"]["post"].__setitem__("digest", "B" * 64),
        ),
        (
            "non-identical scale control",
            lambda d: d["arms"]["scale"].__setitem__("sha256", "0" * 64),
        ),
        (
            "placement refusal",
            lambda d: d["arms"]["crop"].__setitem__(
                "log", d["arms"]["crop"]["log"].replace(
                    "63 placed / 0 refused", "62 placed / 1 refused"
                )
            ),
        ),
        (
            "no crop intervention",
            lambda d: d["arms"]["crop"].__setitem__(
                "sha256", d["arms"]["scale"]["sha256"]
            ),
        ),
    )
    for name, change in provenance_mutations:
        r.plant(
            name,
            provenance_mutant(change),
            "production provenance gate rejected mutant",
        )
    r.plant(
        "swapped frozen comparator",
        not accepted(provenance, cc.HASHES[crop_path]),
        "live PMax rejected against incompatible frozen identity",
    )
    r.plant(
        "changed frozen scale identity",
        not accepted(provenance, frozen_scale_hash="0" * 64),
        "frozen scale identity is bound to the live scale control",
    )

    verdict_fixtures = (
        (
            "RECOVERED_BY_CROP",
            ("TRAILS", "UNRESOLVED", 1.03, 1.08, [1.01] * 4, False),
        ),
        (
            "PARTIAL_RECOVERY",
            ("TRAILS", "TRAILS", 1.03, 1.08, [1.01] * 4, False),
        ),
        (
            "COVER_NOT_CAUSE",
            ("TRAILS", "TRAILS", 0.99, 1.01, [0.99] * 4, True),
        ),
        (
            "CROP_DEGRADES",
            ("UNRESOLVED", "TRAILS", 0.90, 0.97, [0.95] * 4, False),
        ),
        (
            "UNRESOLVED",
            ("TRAILS", "UNRESOLVED", 1.03, 1.08, [1.01, 0.99], False),
        ),
    )
    for expected, arguments in verdict_fixtures:
        actual = cc.cover_verdict(*arguments)
        r.control(
            f"literal verdict {expected}",
            actual == expected,
            f"actual={actual}",
        )
    return r.finish()


if __name__ == "__main__":
    sys.exit(main())

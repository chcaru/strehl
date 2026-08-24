"""M81 unit arm: estimate one response-noise scalar from M70-textured tiles.

The response-noise measurement is M69 B3's frozen-latent synthetic-replicate
instrument. The only new construction is the sampling rule: every 512x512 raw
tile must be one of M70's fixed 511-sensor-pixel patches and must pass M70's
low-band texture test. Flat patches are absent, not zero-valued observations.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
M69_SRC = REPO / "experiments" / "M69-focus-noise-sd" / "src"
M69_OUT = REPO / "experiments" / "M69-focus-noise-sd" / "out"
M70_SRC = REPO / "experiments" / "M70-through-focus-spectrum" / "src"
M70_OUT = REPO / "experiments" / "M70-through-focus-spectrum" / "out"
sys.path.insert(0, str(M69_SRC))
sys.path.insert(0, str(M70_SRC))

import m69  # noqa: E402
import m70lib as m70  # noqa: E402

a2 = importlib.import_module("20-a2-m66-replication")
b3 = importlib.import_module("97-b-fine-field")

STACKS = (
    "wrapped-text-1",
    "wrapped-text-2",
    "109MSDCF",
    "coffee-bean",
    "foam",
    "bee-1",
)
PATCH_GQ = 256
WELCH_TILE = 128
RAW_TILE = 512
NREP = 32
TEXTURE_GATE = 10.0
SEED_BASE = 0x4D81_0000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def texture_record(stack: str) -> dict:
    path = M70_OUT / f"tfs-{stack}.npz"
    z = np.load(path, allow_pickle=False)
    patch = int(z["patch"])
    tile = int(z["tile"])
    if patch != PATCH_GQ or tile != WELCH_TILE:
        raise RuntimeError(f"{stack}: M70 patch/tile is {patch}/{tile}, expected 256/128")
    power = z["power"]
    level = z["level"]
    bands = [str(v) for v in z["bands"]]
    iso = float(z["iso"])
    nvar = m70.noise_var_dn2(level, iso)
    signal = power - nvar[:, :, None]
    low = bands.index("b1_low")
    snr = signal[:, :, low].max(axis=0) / np.median(nvar, axis=0)
    mask = snr >= TEXTURE_GATE
    frames = [str(v) for v in z["frames"]]
    return {
        "path": path,
        "iso": iso,
        "centres": z["centres"].astype(int),
        "snr": snr,
        "mask": mask,
        "frames": frames,
        "n_frames": len(frames),
    }


def measure_patch(job: tuple[int, int, np.ndarray, float, float]) -> dict:
    stack_ordinal, patch_index, latent, iso, texture_snr = job
    seed = SEED_BASE + 256 * stack_ordinal + patch_index
    rng = np.random.default_rng(seed)
    raw_sd = a2.raw_noise_sd(latent, iso)
    acc = None
    for _ in range(NREP):
        frame = latent + raw_sd * rng.standard_normal(latent.shape)
        luma = m69.luma_from_raw(frame)
        field = b3.field(
            luma,
            m69.WINDOW_RADIUS,
            m69.REGULARISER_RADIUS,
            iso=iso,
        )
        if acc is None:
            acc = m69.Welford(field.shape)
        acc.push(field)

    assert acc is not None
    inset = b3.inset_for(m69.WINDOW_RADIUS, m69.REGULARISER_RADIUS)
    sd = m69.interior(acc.sd(), inset)
    clean = m69.luma_from_raw(latent)
    sigma = m69.green_luma_sigma(clean, iso)
    gx, gy = m69.sobel_components(clean)
    z_obs = np.hypot(gx, gy) / (b3.a3mod.S_SOBEL * sigma)
    z_true = np.sqrt(np.maximum(z_obs**2 - 2.0, 0.0))
    support_obs = m69.interior(
        b3.p1_support(z_obs, m69.WINDOW_RADIUS, m69.REGULARISER_RADIUS),
        inset,
    )
    support_true = m69.interior(
        b3.p1_support(z_true, m69.WINDOW_RADIUS, m69.REGULARISER_RADIUS),
        inset,
    )
    debias = float(support_true.mean() / support_obs.mean())
    scaled = sd / m69.FOCUS_NOISE_SD
    rho_obs = float(scaled.mean())
    return {
        "patch_index": patch_index,
        "seed": seed,
        "texture_snr": float(texture_snr),
        "pixels": int(sd.size),
        "rho_obs": rho_obs,
        "debias": debias,
        "rho_true": rho_obs * debias,
        "rho_p05": float(np.percentile(scaled, 5)),
        "rho_p95": float(np.percentile(scaled, 95)),
    }


def calibrate_stack(stack: str, ordinal: int, workers: int) -> dict:
    tex = texture_record(stack)
    if int(tex["mask"].sum()) < 3:
        raise RuntimeError(f"{stack}: only {int(tex['mask'].sum())} textured patches")
    paths = m69.stack_files(stack)
    if len(paths) != tex["n_frames"]:
        raise RuntimeError(
            f"{stack}: M70 has {tex['n_frames']} frames but corpus has {len(paths)}"
        )
    middle = Path(paths[len(paths) // 2])
    if middle.name != tex["frames"][len(tex["frames"]) // 2]:
        raise RuntimeError(f"{stack}: middle-frame identity differs from M70")
    iso = m69.iso_of(str(middle))
    if iso != tex["iso"]:
        raise RuntimeError(f"{stack}: EXIF ISO {iso} differs from M70 ISO {tex['iso']}")

    raw = m69.raw_visible(str(middle))
    jobs = []
    selected = []
    for index, ((row, col), snr, keep) in enumerate(
        zip(tex["centres"], tex["snr"], tex["mask"], strict=True)
    ):
        if not keep:
            continue
        y0, x0 = int(row) - RAW_TILE // 2, int(col) - RAW_TILE // 2
        latent = raw[y0 : y0 + RAW_TILE, x0 : x0 + RAW_TILE].copy()
        if latent.shape != (RAW_TILE, RAW_TILE) or y0 % 2 or x0 % 2:
            raise RuntimeError(f"{stack} patch {index}: invalid raw tile {latent.shape}")
        jobs.append((ordinal, index, latent, iso, float(snr)))
        selected.append({"patch_index": index, "centre": [int(row), int(col)]})
    del raw

    with multiprocessing.Pool(processes=workers) as pool:
        rows = pool.map(measure_patch, jobs, chunksize=1)
    by_index = {row["patch_index"]: row for row in rows}
    for rec in selected:
        rec.update(by_index[rec["patch_index"]])

    values = np.array([row["rho_true"] for row in selected], dtype=np.float64)
    span = float(values.max() / values.min())
    return {
        "frames": len(paths),
        "iso": iso,
        "middle_frame": middle.name,
        "m70_artifact": str(tex["path"].relative_to(REPO)),
        "m70_sha256": sha256(tex["path"]),
        "patch_gq_samples": PATCH_GQ,
        "patch_sensor_pixels": 2 * PATCH_GQ - 1,
        "welch_tile": WELCH_TILE,
        "texture_gate": TEXTURE_GATE,
        "textured_patches": len(selected),
        "flat_patches": int((~tex["mask"]).sum()),
        "replicates_per_patch": NREP,
        "rho": float(np.median(values)),
        "patch_rho_min": float(values.min()),
        "patch_rho_max": float(values.max()),
        "patch_rho_span": span,
        "scalar_span_pass": span <= 2.0,
        "patches": selected,
    }


def main() -> None:
    workers = min(6, os.cpu_count() or 1)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, encoding="utf-8"
    ).strip()
    print(f"M81_UNIT_COMMIT={commit}")
    print(
        f"M81_UNIT_CONFIG patch_gq={PATCH_GQ} sensor_px={2 * PATCH_GQ - 1} "
        f"welch_tile={WELCH_TILE} texture_gate={TEXTURE_GATE} nrep={NREP} "
        f"workers={workers}",
        flush=True,
    )
    flat = a2.k1b()
    if not flat["met"]:
        raise RuntimeError("K1b flat temporal control failed")

    rows = {}
    for ordinal, stack in enumerate(STACKS):
        row = calibrate_stack(stack, ordinal, workers)
        rows[stack] = row
        print(
            f"M81_UNIT stack={stack} N={row['frames']} textured={row['textured_patches']} "
            f"flat={row['flat_patches']} rho={row['rho']:.9f} "
            f"patch_span={row['patch_rho_span']:.6f} "
            f"scalar_pass={int(row['scalar_span_pass'])}",
            flush=True,
        )

    result = {
        "commit": commit,
        "configuration": {
            "patch_gq_samples": PATCH_GQ,
            "patch_sensor_pixels": 2 * PATCH_GQ - 1,
            "raw_tile": RAW_TILE,
            "welch_tile": WELCH_TILE,
            "texture_gate": TEXTURE_GATE,
            "replicates_per_patch": NREP,
            "seed_base": SEED_BASE,
            "workers": workers,
            "focus_noise_sd": m69.FOCUS_NOISE_SD,
        },
        "controls": {
            "K1b": flat,
            "minimum_textured_patches": 3,
            "maximum_patch_rho_span": 2.0,
        },
        "source_hashes": {
            "m69_b3": sha256(M69_OUT / "97-b-fine-field.json"),
            "m69_p2": sha256(M69_OUT / "80-corpus-rho.json"),
        },
        "stacks": rows,
    }
    (HERE / "unit-calibration.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("M81_UNIT_WROTE=unit-calibration.json")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

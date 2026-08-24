"""Fresh M70 spectral reference for M81's five locked stacks."""

from __future__ import annotations

import json
import multiprocessing
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
M70_SRC = REPO / "experiments" / "M70-through-focus-spectrum" / "src"
M70_OUT = REPO / "experiments" / "M70-through-focus-spectrum" / "out"
sys.path.insert(0, str(M70_SRC))

import m70lib as M  # noqa: E402
import s04_through_focus as S04  # noqa: E402
import s05_analyse as S05  # noqa: E402

ROOT = Path(r"D:\personal\macro")
STACKS = {
    "wrapped-text-1": 130,
    "109MSDCF": 22,
    "coffee-bean": 105,
    "foam": 100,
    "bee-1": 299,
}
SCALES = (0.950, 1.000, 1.093)


def target(power: np.ndarray, level: np.ndarray, iso: float, scale: float) -> dict:
    nvar = M.noise_var_dn2(level, iso) * scale
    signal = power - nvar[:, :, None]
    low = S04.BAND_NAMES.index("b1_low")
    textured = signal[:, :, low].max(axis=0) / np.median(nvar, axis=0) >= S05.DYN_GATE
    per_band = []
    for name in M.MID_BANDS:
        band = S04.BAND_NAMES.index(name)
        values = []
        for patch in np.flatnonzero(textured):
            s = signal[:, patch, band]
            values.append(float(s.sum() / max(float(s.max()), 1e-30)))
        per_band.append(float(np.median(values)))
    return {
        "scale": scale,
        "n_eff": float(np.mean(per_band)),
        "per_band_n_eff": per_band,
        "textured_patches": int(textured.sum()),
    }


def main() -> None:
    census = json.loads((M70_OUT / "exif-census.json").read_text(encoding="utf-8"))
    by_stack = {row["stack"]: row for row in census}
    result = {
        "instrument": "fresh M70 corrected unclipped Python reference",
        "active": [M.L.ACTIVE_W, M.L.ACTIVE_H],
        "patch": S04.PATCH,
        "tile": S04.TILE,
        "workers": 6,
        "stacks": {},
    }
    started = time.perf_counter()
    with multiprocessing.Pool(6) as pool:
        for stack, expected_n in STACKS.items():
            paths = sorted(
                path for path in (ROOT / stack).iterdir() if path.suffix.lower() == ".arw"
            )
            if len(paths) != expected_n:
                raise RuntimeError(f"{stack}: found {len(paths)} ARWs, expected {expected_n}")
            iso_hist = by_stack[stack]["iso"]
            if len(iso_hist) != 1:
                raise RuntimeError(f"{stack}: ISO is not constant: {iso_hist}")
            iso = float(next(iter(iso_hist)))
            t0 = time.perf_counter()
            rows = pool.map(
                S04.measure_frame,
                [(str(path), S04.PATCH, S04.TILE) for path in paths],
                chunksize=1,
            )
            power = np.stack([row[0] for row in rows])
            level = np.stack([row[1] for row in rows])
            result["stacks"][stack] = {
                "frames": len(paths),
                "iso": iso,
                "targets": [target(power, level, iso, scale) for scale in SCALES],
                "seconds": time.perf_counter() - t0,
            }
            print(
                f"{stack}: N={len(paths)} nominal="
                f"{result['stacks'][stack]['targets'][1]['n_eff']:.9f}",
                flush=True,
            )
    result["seconds"] = time.perf_counter() - started
    (HERE / "reference.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

"""M84 step 04 - RECONNAISSANCE 4. Focus-index map from the q4 cache.

Last reconnaissance step before PREREGISTRATION.md is frozen. Declared in its
section 0. Purpose: see the SHAPE of the depth ramp on the angled stack and the
residual tilt on the flat-on control, so the pre-registered method is designed
against the real subject rather than against an assumed one (AGENTS rule 13).

Uses only the decode-once cache. Reads nothing from D:.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
OUT = ROOT / "out"


def load(stack: str) -> tuple[np.ndarray, dict]:
    arr = np.load(CACHE / f"{stack}-q4.npy").astype(np.float32)
    meta = json.loads((CACHE / f"{stack}-meta.json").read_text(encoding="utf-8"))
    return arr - meta["black_level"], meta


def response(cube: np.ndarray, r: int = 3) -> np.ndarray:
    """Normalised squared-gradient response per frame, box-smoothed, on q4 pixels."""
    gy = np.zeros_like(cube)
    gx = np.zeros_like(cube)
    gy[:, 1:-1, :] = cube[:, 2:, :] - cube[:, :-2, :]
    gx[:, :, 1:-1] = cube[:, :, 2:] - cube[:, :, :-2]
    e = gy * gy + gx * gx
    k = 2 * r + 1
    ker = np.ones(k, dtype=np.float32) / k
    sm = np.apply_along_axis(lambda v: np.convolve(v, ker, mode="same"), 1, e)
    sm = np.apply_along_axis(lambda v: np.convolve(v, ker, mode="same"), 2, sm)
    lvl = np.apply_along_axis(lambda v: np.convolve(v, ker, mode="same"), 1, cube)
    lvl = np.apply_along_axis(lambda v: np.convolve(v, ker, mode="same"), 2, lvl)
    return sm / np.maximum(lvl * lvl, 1.0)


def save_index(idx: np.ndarray, conf: np.ndarray, path: pathlib.Path, n: int) -> None:
    img = np.zeros(idx.shape + (3,), dtype=np.uint8)
    v = np.clip(idx / max(n - 1, 1), 0, 1)
    good = conf > np.percentile(conf, 60)
    img[..., 0] = (v * 255).astype(np.uint8)
    img[..., 1] = (v * 255).astype(np.uint8)
    img[..., 2] = (v * 255).astype(np.uint8)
    img[~good] = [40, 0, 0]
    Image.fromarray(img).save(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {}
    for stack in ("flat-on-ruler-cpl", "highly-angled-ruler-mm-cpl"):
        cube, meta = load(stack)
        n = cube.shape[0]
        r = response(cube)
        idx = np.argmax(r, axis=0).astype(np.float32)
        peak = np.max(r, axis=0)
        med = np.median(r, axis=0)
        conf = peak / np.maximum(med, 1e-12)
        save_index(idx, conf, OUT / f"idx-{stack}.png", n)
        sel = conf > 3.0
        rep[stack] = {
            "n_frames": n,
            "shape": list(idx.shape),
            "frac_conf_gt3": float(sel.mean()),
            "idx_p05": float(np.percentile(idx[sel], 5)) if sel.any() else None,
            "idx_p50": float(np.percentile(idx[sel], 50)) if sel.any() else None,
            "idx_p95": float(np.percentile(idx[sel], 95)) if sel.any() else None,
        }
        print(
            f"{stack}: n={n} conf>3 on {sel.mean() * 100:.1f}% of q4 px; "
            f"index p05/p50/p95 = {rep[stack]['idx_p05']}/{rep[stack]['idx_p50']}/{rep[stack]['idx_p95']}"
        )
        np.save(OUT / f"idx-{stack}.npy", idx)
        np.save(OUT / f"conf-{stack}.npy", conf)
    (OUT / "04-recon.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""M84 step 01 - RECONNAISSANCE 2. Where is the ruler, where is it sharp, what is the tick period?

Still pre-registration reconnaissance (declared in PREREGISTRATION.md section 0).
Answers three design questions and nothing else:

  R1  Where in the frame does each stack carry the graduation comb?
  R2  How does the sharp band move across the angled stack?
  R3  What is the dominant tick period, in quad pixels, in a sharp region?

Reads READ-ONLY from D:\\personal\\macro. Rule 32 idiom: copy inside the `with`.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import rawpy
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")


def green_luma(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = float(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black


def tile_sharpness(plane: np.ndarray, tile: int = 128) -> np.ndarray:
    """Normalised gradient energy per tile: mean(|grad|^2) / mean(level)^2."""
    h, w = plane.shape
    ny, nx = h // tile, w // tile
    out = np.zeros((ny, nx), dtype=np.float64)
    for j in range(ny):
        for i in range(nx):
            t = plane[j * tile : (j + 1) * tile, i * tile : (i + 1) * tile]
            gy = np.diff(t, axis=0)
            gx = np.diff(t, axis=1)
            e = float(np.mean(gy * gy) + np.mean(gx * gx))
            lvl = max(float(np.mean(t)), 1.0)
            out[j, i] = e / (lvl * lvl)
    return out


def save_map(m: np.ndarray, path: pathlib.Path) -> None:
    v = np.log10(np.maximum(m, 1e-12))
    lo, hi = np.percentile(v, [2, 98])
    img = np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)
    big = np.kron((img * 255).astype(np.uint8), np.ones((6, 6), dtype=np.uint8))
    Image.fromarray(big).save(path)


def dominant_period(profile: np.ndarray) -> tuple[float, float]:
    """Peak of the periodogram of a detrended 1-D profile -> (period_px, rel_power)."""
    p = profile - np.mean(profile)
    n = len(p)
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(p * win)) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    lo = np.searchsorted(freqs, 1.0 / (n / 3.0))
    hi = np.searchsorted(freqs, 0.45)
    k = lo + int(np.argmax(spec[lo:hi]))
    total = float(np.sum(spec[lo:hi]))
    return float(1.0 / freqs[k]), float(spec[k] / max(total, 1e-30))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {}

    # R1/R3 on the flat-on control.
    flat = sorted((CORPUS / "flat-on-ruler-cpl").glob("*.ARW"))
    picks = [0, 19, 39, 59, 78]
    flat_rows = []
    for i in picks:
        plane = green_luma(flat[i])
        sm = tile_sharpness(plane)
        save_map(sm, OUT / f"sharp-flat-f{i:03d}.png")
        j, k = np.unravel_index(int(np.argmax(sm)), sm.shape)
        flat_rows.append(
            {"frame": i, "map_shape": list(sm.shape), "argmax_tile_yx": [int(j), int(k)],
             "max": float(sm.max()), "median": float(np.median(sm))}
        )
        print(f"flat f{i:03d}: sharpest tile (row {j}, col {k}) of {sm.shape}, max={sm.max():.3e}")
    report["flat_sharpness"] = flat_rows

    # R3: tick period on the flat-on comb. Use the sharpest frame's lower band.
    best = max(flat_rows, key=lambda r: r["max"])["frame"]
    plane = green_luma(flat[best])
    h, w = plane.shape
    periods = []
    for frac in (0.80, 0.85, 0.90, 0.95):
        y = int(h * frac)
        band = plane[y - 20 : y + 20, :]
        prof = band.mean(axis=0)
        per, rel = dominant_period(prof)
        periods.append({"y_frac": frac, "y": y, "period_quad_px": per, "rel_power": rel})
        print(f"flat f{best:03d} y={y}: dominant period {per:.3f} quad px, rel power {rel:.3f}")
    report["flat_periods"] = {"frame": best, "rows": periods}

    # R2: where is the sharp band on the angled stack, per frame?
    ang = sorted((CORPUS / "highly-angled-ruler-mm-cpl").glob("*.ARW"))
    ang_rows = []
    for i in [0, 40, 80, 120, 160, 200, 240, 298]:
        plane = green_luma(ang[i])
        sm = tile_sharpness(plane)
        save_map(sm, OUT / f"sharp-ang-f{i:03d}.png")
        j, k = np.unravel_index(int(np.argmax(sm)), sm.shape)
        colprof = sm.max(axis=0)
        ang_rows.append(
            {"frame": i, "map_shape": list(sm.shape), "argmax_tile_yx": [int(j), int(k)],
             "max": float(sm.max()), "median": float(np.median(sm)),
             "col_argmax": int(np.argmax(colprof))}
        )
        print(
            f"ang f{i:03d}: sharpest tile (row {j}, col {k}) of {sm.shape}, "
            f"max={sm.max():.3e}, col_argmax={int(np.argmax(colprof))}"
        )
    report["angled_sharpness"] = ang_rows

    (OUT / "01-recon.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

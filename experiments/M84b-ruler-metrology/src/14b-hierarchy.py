"""M84b step 14b - the tick-height hierarchy by band profiles.

Replaces step 14's upward column scan, which returned 0 for two of the three
long marks and is therefore not trusted. This version is direct: average rows
inside a horizontal band that lies WHOLLY above the ruler's datum line, and
detect which graduations still carry a dark mark there. A mark that reaches a
higher band is a longer mark.

Bands, chosen from the measured mark tops in out/14-tall-band.png:
  high  quad y [850, 1050]   above the middle-height marks' tops
  mid   quad y [1150, 1350]  above the minor marks, below the mid marks' tops
  low   quad y [1400, 1500]  just above the datum: every mark that crosses it

Pre-registration section 3.2: the minor pitch is 10 mm / Q_long, accepted only
if Q_long is an integer within 0.15 and Q_mid is Q_long/2 within 0.15.

Reads READ-ONLY from D:\\personal\\macro.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACK = "flat-on-ruler-cpl"

BANDS = {"high": (850, 1050), "mid": (1150, 1350), "low": (1400, 1500)}
FRAMES = [40, 48, 52, 56, 64]


def quad_green(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black


def mark_darkness(plane: np.ndarray, xs: np.ndarray, y0: int, y1: int) -> np.ndarray:
    prof = plane[y0:y1, :].mean(axis=0)
    bg = ndimage.median_filter(prof, size=601, mode="nearest")
    dark = np.maximum(bg - prof, 0.0)
    out = np.zeros(len(xs))
    for i, x in enumerate(xs):
        xi = int(round(x))
        lo, hi = max(xi - 12, 0), min(xi + 13, len(prof))
        out[i] = float(np.max(dark[lo:hi]))
    return out


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    fit = json.loads((OUT / "13-flat.json").read_text())
    xs = np.array(fit["tick_x"])
    frames = sorted((CORPUS / STACK).glob("*.ARW"))
    planes = [quad_green(frames[i]) for i in FRAMES]

    res = {
        "stack": STACK,
        "frames_used": [frames[i].name for i in FRAMES],
        "tick_x": xs.tolist(),
        "bands": {},
    }
    flags = {}
    for name, (y0, y1) in BANDS.items():
        d = np.median(np.array([mark_darkness(p, xs, y0, y1) for p in planes]), axis=0)
        scatter = np.std(
            np.array([mark_darkness(p, xs, y0, y1) for p in planes]), axis=0
        )
        # A graduation carries a mark in this band if its darkness is above
        # halfway between the population's low and high modes.
        thr = 0.5 * (np.min(d) + np.max(d))
        f = d > thr
        flags[name] = f
        idx = np.flatnonzero(f)
        g = np.diff(idx) if len(idx) > 1 else np.array([])
        res["bands"][name] = {
            "band": [y0, y1],
            "darkness": np.round(d, 1).tolist(),
            "frame_scatter": np.round(scatter, 1).tolist(),
            "threshold": float(thr),
            "flagged_indices": idx.tolist(),
            "gaps": g.tolist(),
            "period": float(np.median(g)) if len(g) else None,
            "period_spread": float(np.max(g) - np.min(g)) if len(g) else None,
            "contrast_ratio": float(np.max(d) / max(np.min(d), 1e-9)),
        }
        print(f"[{name}] y {y0}-{y1}")
        print(f"  darkness   {np.round(d, 0)}")
        print(f"  thr {thr:.0f} -> flagged {idx.tolist()}  gaps {g.tolist()}")

    q_long = res["bands"]["high"]["period"]
    q_mid = res["bands"]["mid"]["period"]
    q_low = res["bands"]["low"]["period"]
    decision = {
        "Q_long": q_long,
        "Q_mid": q_mid,
        "Q_low": q_low,
        "Q_long_is_integer": (
            bool(abs(q_long - round(q_long)) <= 0.15) if q_long else False
        ),
        "Q_mid_is_half_Q_long": (
            bool(abs(q_mid - q_long / 2.0) <= 0.15) if (q_long and q_mid) else False
        ),
        "every_graduation_crosses_datum": (
            bool(q_low == 1.0) if q_low else False
        ),
    }
    if decision["Q_long_is_integer"] and decision["Q_mid_is_half_Q_long"]:
        decision["P_mm"] = 10.0 / round(q_long)
        decision["verdict"] = "DECIDED"
    else:
        decision["P_mm"] = None
        decision["verdict"] = "UNDECIDED"
    res["decision"] = decision
    print(f"\nQ_long {q_long}  Q_mid {q_mid}  Q_low {q_low}")
    print(f"decision: {decision['verdict']}  P = {decision['P_mm']} mm")
    (OUT / "14b-hierarchy.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

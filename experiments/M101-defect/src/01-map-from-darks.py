"""M101 script 01 - build the defect map from the 242 darks.

Decodes every dark once, saves per-ISO-group temporal means (full 20 and two
random halves of 10) to scratch, then thresholds the same-plane 8-neighbour
excess by two independently-derived cuts and folds by recurrence.

Reads  : D:\\macro-dark-frames  (READ ONLY)
Writes : C:\\dev\\strehl-out\\M101\\means\\*.npy, masks\\*.npz, 01-map.json

Both thresholds are stated in sigma and neither is chosen by eye:
  T-model  K=6 on sigma_pred(S=0, ISO)/sqrt(n) * c_med, from profile.rs
  T-robust K=6 on 1.4826*MAD of the observed excess, per plane per group
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import rawpy

DARK_ROOT = Path(r"D:\macro-dark-frames")
OUT = Path(r"C:\dev\strehl-out\M101")
MEANS = OUT / "means"
MASKS = OUT / "masks"

BLACK = 512.0
# profile.rs A7C2, read at 6a8ac30
GAIN_DIVISOR = 436.8
BASE_ISO = 100
SECOND_BASE_ISO = 400
RN_E_LOW = 4.20
RN_E_HIGH = 1.2392

K_SIGMA = 6.0
C_MED = float(np.sqrt(1.0 + 1.5707963267948966 / 8.0))  # median-of-8 var inflation
RECUR_MIN = 6  # of 11 groups, adopted from M22/M48c
SEED = 101

# RGGB: raw_pattern [[0,1],[3,2]], color_desc RGBG -> (0,0)=R (0,1)=G1 (1,0)=G2 (1,1)=B
PLANES = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}


def gain_dn_per_e(iso: int) -> float:
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def read_noise_e(iso: int) -> float:
    return RN_E_HIGH if iso >= SECOND_BASE_ISO else RN_E_LOW


def sigma_pred_zero(iso: int) -> float:
    """sigma of a single dark sample at S=0 DN, in DN."""
    return read_noise_e(iso) * gain_dn_per_e(iso)


def med8(plane: np.ndarray) -> np.ndarray:
    """Median of the eight same-plane neighbours, centre excluded."""
    p = np.pad(plane, 1, mode="edge")
    h, w = plane.shape
    stack = np.empty((8, h, w), dtype=np.float32)
    i = 0
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            stack[i] = p[dy:dy + h, dx:dx + w]
            i += 1
    part = np.partition(stack, (3, 4), axis=0)
    return 0.5 * (part[3] + part[4])


def excess_of(mean_frame: np.ndarray, plane_key: str) -> np.ndarray:
    oy, ox = PLANES[plane_key]
    plane = mean_frame[oy::2, ox::2] - BLACK
    return plane - med8(plane)


def interior(a: np.ndarray) -> np.ndarray:
    return a[1:-1, 1:-1]


def robust_sigma(x: np.ndarray) -> float:
    med = float(np.median(x))
    return float(1.4826 * np.median(np.abs(x - med)))


def decode_group(args):
    gdir, iso = args
    files = sorted(Path(gdir).glob("*.ARW"))
    assert len(files) == 22, f"{gdir}: expected 22, got {len(files)}"
    kept = files[2:]  # owner: "first 2 shots for stablization"
    rng = np.random.default_rng(SEED + iso)
    order = rng.permutation(len(kept))
    half_a = set(int(i) for i in order[:10])

    sum_a = None
    sum_b = None
    t0 = time.time()
    for i, f in enumerate(kept):
        with rawpy.imread(str(f)) as raw:
            v = raw.raw_image_visible.astype(np.float32)  # rule 32: copy inside `with`
        if sum_a is None:
            sum_a = np.zeros_like(v)
            sum_b = np.zeros_like(v)
        (sum_a if i in half_a else sum_b)[:] += v

    name = Path(gdir).name
    np.save(MEANS / f"mean-{name}-full.npy", (sum_a + sum_b) / 20.0)
    np.save(MEANS / f"mean-{name}-A.npy", sum_a / 10.0)
    np.save(MEANS / f"mean-{name}-B.npy", sum_b / 10.0)
    return {
        "dir": name,
        "iso": iso,
        "n_files": len(files),
        "n_kept": len(kept),
        "half_a": sorted(int(i) for i in half_a),
        "decode_s": round(time.time() - t0, 1),
    }


def threshold_group(name: str, iso: int, split: str, n: int):
    """Threshold one group/split, return per-plane packed masks and stats."""
    mean_frame = np.load(MEANS / f"mean-{name}-{split}.npy")
    sig_model = sigma_pred_zero(iso) / np.sqrt(n) * C_MED
    out = {}
    stats = {}
    for pk in PLANES:
        exc = excess_of(mean_frame, pk)
        inner = interior(exc)
        sig_rob = robust_sigma(inner)
        hot_m = np.zeros(exc.shape, dtype=bool)
        hot_r = np.zeros(exc.shape, dtype=bool)
        cold_r = np.zeros(exc.shape, dtype=bool)
        interior(hot_m)[:] = inner > K_SIGMA * sig_model
        interior(hot_r)[:] = inner > K_SIGMA * sig_rob
        interior(cold_r)[:] = inner < -K_SIGMA * sig_rob
        out[f"{pk}-hot-model"] = np.packbits(hot_m)
        out[f"{pk}-hot-robust"] = np.packbits(hot_r)
        out[f"{pk}-cold-robust"] = np.packbits(cold_r)
        stats[pk] = {
            "shape": list(exc.shape),
            "sigma_model_dn": round(float(sig_model), 6),
            "sigma_robust_dn": round(sig_rob, 6),
            "ratio_robust_over_model": round(sig_rob / sig_model, 4),
            "n_hot_model": int(hot_m.sum()),
            "n_hot_robust": int(hot_r.sum()),
            "n_cold_robust": int(cold_r.sum()),
            "excess_p50": round(float(np.median(inner)), 5),
            "excess_p99999": round(float(np.percentile(inner, 99.999)), 4),
            "excess_max": round(float(inner.max()), 3),
        }
    shape = out["R-hot-model"].shape
    np.savez_compressed(MASKS / f"mask-{name}-{split}.npz", **out)
    return name, split, stats, shape


def main():
    MEANS.mkdir(parents=True, exist_ok=True)
    MASKS.mkdir(parents=True, exist_ok=True)
    with open(OUT / "00-probe.json", "r", encoding="utf-8") as fh:
        probe = json.load(fh)
    groups = [(str(DARK_ROOT / g["dir"]), int(g["iso"])) for g in probe["dark_groups"]]
    groups.sort(key=lambda t: t[0])

    force = "--redecode" in sys.argv
    todo = [g for g in groups
            if force or not (MEANS / f"mean-{Path(g[0]).name}-B.npy").exists()]
    print(f"decoding {len(todo)} of {len(groups)} groups", flush=True)
    decode_meta = []
    if todo:
        with ProcessPoolExecutor(max_workers=min(11, len(todo))) as ex:
            for r in ex.map(decode_group, todo):
                decode_meta.append(r)
                print(f"  decoded {r['dir']} ISO {r['iso']} in {r['decode_s']}s", flush=True)

    result = {"groups": [], "decode": decode_meta, "config": {
        "k_sigma": K_SIGMA, "c_med": round(C_MED, 6), "recur_min": RECUR_MIN,
        "black": BLACK, "seed": SEED, "n_full": 20, "n_half": 10,
        "gain_divisor": GAIN_DIVISOR, "rn_e_low": RN_E_LOW, "rn_e_high": RN_E_HIGH,
    }}

    jobs = []
    for gdir, iso in groups:
        name = Path(gdir).name
        for split, n in (("full", 20), ("A", 10), ("B", 10)):
            jobs.append((name, iso, split, n))
    with ProcessPoolExecutor(max_workers=8) as ex:
        for name, split, stats, shape in ex.map(threshold_group, *zip(*jobs)):
            result["groups"].append({"dir": name, "split": split, "planes": stats})
            print(f"  thresholded {name}/{split}", flush=True)

    with open(OUT / "01-map.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    print("wrote 01-map.json", flush=True)


if __name__ == "__main__":
    main()

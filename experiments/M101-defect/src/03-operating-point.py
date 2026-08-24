"""M101 script 03 - where does the map's reproducibility actually live?

B1 failed at the >= 6/11 recurrence criterion inherited from M22/M48c. This
script does not move the bar; it sweeps the recurrence threshold r = 1..11 and
finds the operating point at which the pre-registered J >= 0.80 is met, with the
random-coordinate placebo recomputed at matched set sizes for every r.

Also settles two side questions:
  - the owner's "first 2 shots for stablization": do frames 1-2 differ from 3-22?
  - P-A: the measured sigma_robust / sigma_model ratio, i.e. the size of the
    DSNU term the shipped noise model does not carry.

Reads  : C:\\dev\\strehl-out\\M101\\masks\\*.npz, means\\*.npy, 01-map.json
Writes : C:\\dev\\strehl-out\\M101\\03-operating-point.json, defectmap-final.npz
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import rawpy

OUT = Path(r"C:\dev\strehl-out\M101")
MASKS = OUT / "masks"
MEANS = OUT / "means"
DARK_ROOT = Path(r"D:\macro-dark-frames")

PLANES = ["R", "G1", "G2", "B"]
PLANE_OFF = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
ALL_DIRS = [f"{i}MSDCF" for i in range(118, 129)]
BLACK = 512.0
SEED = 101
J_BAR = 0.80


def load_mask(name, split, key, shape):
    z = np.load(MASKS / f"mask-{name}-{split}.npz")
    return np.unpackbits(z[key], count=shape[0] * shape[1]).astype(bool).reshape(shape)


def jaccard(a, b):
    u = int(np.count_nonzero(a | b))
    return int(np.count_nonzero(a & b)) / u if u else float("nan")


def recur(dirs, split, key, shape):
    acc = np.zeros(shape, dtype=np.uint8)
    for d in dirs:
        acc += load_mask(d, split, key, shape)
    return acc


def sweep_plane(pk, shape):
    kh = f"{pk}-hot-robust"
    ra = recur(ALL_DIRS, "A", kh, shape)
    rb = recur(ALL_DIRS, "B", kh, shape)
    rf = recur(ALL_DIRS, "full", kh, shape)
    rng = np.random.default_rng(SEED + hash(pk) % 1000)
    rows = []
    for r in range(1, 12):
        a, b = ra >= r, rb >= r
        na, nb = int(a.sum()), int(b.sum())
        pa = np.zeros(a.size, dtype=bool)
        pb = np.zeros(b.size, dtype=bool)
        if na:
            pa[rng.choice(a.size, na, replace=False)] = True
        if nb:
            pb[rng.choice(b.size, nb, replace=False)] = True
        rows.append({
            "r": r, "n_A": na, "n_B": nb, "n_full": int((rf >= r).sum()),
            "jaccard": round(jaccard(a, b), 5),
            "jaccard_placebo": round(jaccard(pa.reshape(shape), pb.reshape(shape)), 8),
        })
    return pk, rows, rf


def first_two_group(d):
    files = sorted((DARK_ROOT / d).glob("*.ARW"))
    acc = None
    for f in files[:2]:
        with rawpy.imread(str(f)) as raw:
            v = raw.raw_image_visible.astype(np.float32)
        acc = v if acc is None else acc + v
    return d, acc / 2.0


def main():
    with open(OUT / "01-map.json", "r", encoding="utf-8") as fh:
        m1 = json.load(fh)
    shapes = {}
    for g in m1["groups"]:
        for pk, st in g["planes"].items():
            shapes[pk] = tuple(st["shape"])

    res = {"sweep": {}, "operating_point": {}, "sigma_ratio": {}, "first_two": {}}

    # ---- P-A: sigma_robust / sigma_model, per plane per ISO, full split
    for g in m1["groups"]:
        if g["split"] != "full":
            continue
        res["sigma_ratio"][g["dir"]] = {
            pk: {"sigma_model_dn": st["sigma_model_dn"],
                 "sigma_robust_dn": st["sigma_robust_dn"],
                 "ratio": st["ratio_robust_over_model"]}
            for pk, st in g["planes"].items()}

    # ---- recurrence sweep
    recur_full = {}
    with ProcessPoolExecutor(max_workers=4) as ex:
        for pk, rows, rf in ex.map(sweep_plane, PLANES, [shapes[p] for p in PLANES]):
            res["sweep"][pk] = rows
            recur_full[pk] = rf
            ok = [x["r"] for x in rows if x["jaccard"] >= J_BAR]
            res["operating_point"][pk] = {
                "min_r_meeting_bar": min(ok) if ok else None,
                "bar": J_BAR,
            }
            print(f"  {pk}: " + " ".join(f"r{x['r']}={x['jaccard']:.3f}" for x in rows), flush=True)

    rs = [res["operating_point"][p]["min_r_meeting_bar"] for p in PLANES]
    r_star = max([r for r in rs if r is not None], default=None)
    res["r_star"] = r_star
    print(f"  r* (meets J>={J_BAR} on every plane) = {r_star}", flush=True)

    # ---- final map at r*
    final = {}
    counts = {}
    for pk in PLANES:
        m = recur_full[pk] >= r_star
        final[f"{pk}-defect"] = np.packbits(m)
        final[f"{pk}-recur"] = recur_full[pk]
        counts[pk] = int(m.sum())
    counts["TOTAL"] = sum(counts[p] for p in PLANES)
    res["final_map_counts"] = counts
    np.savez_compressed(OUT / "defectmap-final.npz", **final,
                        **{f"shape_{p}": np.array(shapes[p]) for p in PLANES},
                        r_star=np.array([r_star]))
    print(f"  final map at r>={r_star}: {counts}", flush=True)

    # ---- the owner's "first 2 shots for stablization"
    with ProcessPoolExecutor(max_workers=6) as ex:
        first2 = dict(ex.map(first_two_group, ALL_DIRS))
    for d in ALL_DIRS:
        rest = np.load(MEANS / f"mean-{d}-full.npy")
        f2 = first2[d]
        diff = f2 - rest
        res["first_two"][d] = {
            "mean_first2_dn": round(float(f2.mean() - BLACK), 4),
            "mean_rest20_dn": round(float(rest.mean() - BLACK), 4),
            "delta_mean_dn": round(float(diff.mean()), 5),
            "delta_p50_dn": round(float(np.median(diff)), 5),
            "delta_p99_9_dn": round(float(np.percentile(diff, 99.9)), 4),
            "delta_max_dn": round(float(diff.max()), 2),
        }
        print(f"  first2 {d}: dmean={res['first_two'][d]['delta_mean_dn']:+.5f} DN", flush=True)

    with open(OUT / "03-operating-point.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print("wrote 03-operating-point.json", flush=True)


if __name__ == "__main__":
    main()

"""M101 script 02 - fold per-group masks into a defect map and score the bars.

Reads  : C:\\dev\\strehl-out\\M101\\masks\\*.npz  (from script 01)
         experiments/m48c-defect-layer/data/hotmask-*.npy  (external control)
Writes : C:\\dev\\strehl-out\\M101\\defectmap.npz, 02-bars.json

Scores, in order:
  B1 split-half Jaccard >= 0.80
  B2 random-coordinate placebo <= 0.01, reported beside B1
  B3 external replication within +/-25% of M48c 13,650 and M22 11,393
  B4 low-mode map >= 90% contained in high-mode map
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

OUT = Path(r"C:\dev\strehl-out\M101")
MASKS = OUT / "masks"
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
M48C = REPO / "experiments" / "m48c-defect-layer" / "data"

PLANES = ["R", "G1", "G2", "B"]
RECUR_MIN = 6
SEED = 101

# ISO gain mode: profile.rs second_base_iso = 400
LOW_DIRS = ["122MSDCF", "118MSDCF", "123MSDCF", "126MSDCF"]          # 50 100 200 250
HIGH_DIRS = ["119MSDCF", "125MSDCF", "124MSDCF", "120MSDCF",
             "127MSDCF", "121MSDCF", "128MSDCF"]                      # 400..2000
ALL_DIRS = sorted(LOW_DIRS + HIGH_DIRS)


def load_mask(name: str, split: str, key: str, shape) -> np.ndarray:
    z = np.load(MASKS / f"mask-{name}-{split}.npz")
    return np.unpackbits(z[key], count=shape[0] * shape[1]).astype(bool).reshape(shape)


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.count_nonzero(a & b))
    union = int(np.count_nonzero(a | b))
    return inter / union if union else float("nan")


def random_mask(shape, k: int, rng) -> np.ndarray:
    m = np.zeros(shape[0] * shape[1], dtype=bool)
    m[rng.choice(m.size, size=k, replace=False)] = True
    return m.reshape(shape)


def recur_fold(dirs, split, key, shape):
    acc = np.zeros(shape, dtype=np.uint8)
    for d in dirs:
        acc += load_mask(d, split, key, shape)
    return acc


def main():
    with open(OUT / "01-map.json", "r", encoding="utf-8") as fh:
        m1 = json.load(fh)
    shapes = {}
    for g in m1["groups"]:
        for pk, st in g["planes"].items():
            shapes[pk] = tuple(st["shape"])
    rng = np.random.default_rng(SEED)
    res = {"shapes": {k: list(v) for k, v in shapes.items()}, "planes": {}}
    final = {}

    for crit in ("robust", "model"):
        key_hot = f"{{p}}-hot-{crit}"
        for pk in PLANES:
            shape = shapes[pk]
            kh = key_hot.format(p=pk)
            full = recur_fold(ALL_DIRS, "full", kh, shape)
            defect = full >= RECUR_MIN
            always = full == 11

            ha = recur_fold(ALL_DIRS, "A", kh, shape) >= RECUR_MIN
            hb = recur_fold(ALL_DIRS, "B", kh, shape) >= RECUR_MIN
            j_split = jaccard(ha, hb)
            pa = random_mask(shape, int(ha.sum()), rng)
            pb = random_mask(shape, int(hb.sum()), rng)
            j_placebo = jaccard(pa, pb)
            j_chance = int(ha.sum()) / (int(ha.sum()) + int(hb.sum())) if ha.sum() else 0.0

            lo = recur_fold(LOW_DIRS, "full", kh, shape) >= 3
            hi = recur_fold(HIGH_DIRS, "full", kh, shape) >= 4
            contain = float((lo & hi).sum() / lo.sum()) if lo.sum() else float("nan")
            contain_rev = float((lo & hi).sum() / hi.sum()) if hi.sum() else float("nan")

            entry = {
                "n_defect": int(defect.sum()),
                "n_always_11of11": int(always.sum()),
                "n_half_A": int(ha.sum()),
                "n_half_B": int(hb.sum()),
                "jaccard_split_half": round(j_split, 5),
                "jaccard_placebo": round(j_placebo, 8),
                "jaccard_chance_analytic": round(j_chance, 8),
                "n_low_mode": int(lo.sum()),
                "n_high_mode": int(hi.sum()),
                "low_contained_in_high": round(contain, 5),
                "high_contained_in_low": round(contain_rev, 5),
            }
            if crit == "robust":
                # cold sites, same recurrence rule
                kc = f"{pk}-cold-robust"
                cold = recur_fold(ALL_DIRS, "full", kc, shape) >= RECUR_MIN
                entry["n_cold"] = int(cold.sum())
                final[f"{pk}-defect"] = np.packbits(defect)
                final[f"{pk}-always"] = np.packbits(always)
                final[f"{pk}-cold"] = np.packbits(cold)
                final[f"{pk}-recur"] = full
            res["planes"].setdefault(crit, {})[pk] = entry
            print(f"  {crit:7s} {pk:2s} n={entry['n_defect']:7d} "
                  f"J_split={j_split:.4f} J_placebo={j_placebo:.2e} "
                  f"low_in_high={contain:.4f}", flush=True)

    for crit in ("robust", "model"):
        tot = sum(res["planes"][crit][p]["n_defect"] for p in PLANES)
        res["planes"][crit]["TOTAL"] = {
            "n_defect": tot,
            "frac_of_sensor": tot / sum(shapes[p][0] * shapes[p][1] for p in PLANES),
        }

    # B3 external replication against M48c's committed masks
    ext = {}
    for pk in PLANES:
        f = M48C / f"hotmask-{pk}.npy"
        if not f.exists():
            continue
        bm = np.load(f)
        pop = np.zeros(bm.shape, dtype=np.uint8)
        for bit in range(11):
            pop += ((bm >> bit) & np.uint16(1)).astype(np.uint8)
        m48 = pop >= RECUR_MIN
        mine = np.unpackbits(final[f"{pk}-defect"],
                             count=shapes[pk][0] * shapes[pk][1]).astype(bool).reshape(shapes[pk])
        h = min(m48.shape[0], mine.shape[0])
        w = min(m48.shape[1], mine.shape[1])
        a, b = m48[:h, :w], mine[:h, :w]
        ext[pk] = {
            "m48c_shape": list(m48.shape), "mine_shape": list(mine.shape),
            "m48c_n": int(m48.sum()), "mine_n": int(mine.sum()),
            "overlap_shape": [h, w],
            "jaccard": round(jaccard(a, b), 5),
            "mine_recovered_frac": round(float((a & b).sum() / b.sum()), 5) if b.sum() else None,
            "m48c_recovered_frac": round(float((a & b).sum() / a.sum()), 5) if a.sum() else None,
        }
        print(f"  ext {pk:2s} m48c={ext[pk]['m48c_n']:7d} mine={ext[pk]['mine_n']:7d} "
              f"J={ext[pk]['jaccard']:.4f}", flush=True)
    ext["TOTAL_m48c"] = sum(v["m48c_n"] for k, v in ext.items() if k in PLANES)
    ext["TOTAL_mine"] = sum(v["mine_n"] for k, v in ext.items() if k in PLANES)
    res["external"] = ext

    np.savez_compressed(OUT / "defectmap.npz",
                        **final,
                        shape_R=np.array(shapes["R"]), shape_G1=np.array(shapes["G1"]),
                        shape_G2=np.array(shapes["G2"]), shape_B=np.array(shapes["B"]))
    with open(OUT / "02-bars.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print("wrote 02-bars.json + defectmap.npz", flush=True)


if __name__ == "__main__":
    main()

"""M101 script 04 - split-half at MATCHED SENSITIVITY.

Script 03 showed B1's failure was partly an artefact of my own split design:
thresholding each half at K*sigma_robust(n=10) makes A and B maps of a *different
sensitivity* than the full map, so their disagreement mixes genuine
irreproducibility with a threshold shift. This re-runs the identical bar with the
cut held fixed in DN at K*sigma_robust(full, n=20) for every split, which is the
apples-to-apples form of the same test. The bar itself is unchanged at 0.80.

Also reports strength-stratified reproducibility: of the full-map sites in each
excess-amplitude bin, what fraction is recovered in BOTH halves. That localises
which part of the map is trustworthy instead of scoring it with one number.

Reads  : C:\\dev\\strehl-out\\M101\\means\\*.npy, 01-map.json
Writes : C:\\dev\\strehl-out\\M101\\04-splithalf.json, defectmap-final.npz
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

OUT = Path(r"C:\dev\strehl-out\M101")
MEANS = OUT / "means"

PLANES = ["R", "G1", "G2", "B"]
PLANE_OFF = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
ALL_DIRS = [f"{i}MSDCF" for i in range(118, 129)]
LOW_DIRS = ["122MSDCF", "118MSDCF", "123MSDCF", "126MSDCF"]
HIGH_DIRS = ["119MSDCF", "125MSDCF", "124MSDCF", "120MSDCF",
             "127MSDCF", "121MSDCF", "128MSDCF"]
BLACK = 512.0
K_SIGMA = 6.0
SEED = 101
J_BAR = 0.80
RECUR_MIN = 6


def med8(plane):
    p = np.pad(plane, 1, mode="edge")
    h, w = plane.shape
    st = np.empty((8, h, w), dtype=np.float32)
    i = 0
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            st[i] = p[dy:dy + h, dx:dx + w]
            i += 1
    part = np.partition(st, (3, 4), axis=0)
    return 0.5 * (part[3] + part[4])


def excess(mean_frame, pk):
    oy, ox = PLANE_OFF[pk]
    pl = mean_frame[oy::2, ox::2] - BLACK
    return pl - med8(pl)


def job(args):
    """Return packed masks for one group at the FIXED full-map DN cut."""
    d, cuts = args
    out = {}
    for split in ("full", "A", "B"):
        mf = np.load(MEANS / f"mean-{d}-{split}.npy")
        for pk in PLANES:
            e = excess(mf, pk)
            m = np.zeros(e.shape, dtype=bool)
            m[1:-1, 1:-1] = e[1:-1, 1:-1] > cuts[pk]
            out[f"{split}-{pk}"] = np.packbits(m)
            if split == "full":
                out[f"exc-{pk}"] = e[1:-1, 1:-1].astype(np.float16)
    return d, out


def unpack(p, shape):
    return np.unpackbits(p, count=shape[0] * shape[1]).astype(bool).reshape(shape)


def jac(a, b):
    u = int(np.count_nonzero(a | b))
    return int(np.count_nonzero(a & b)) / u if u else float("nan")


def main():
    with open(OUT / "01-map.json", "r", encoding="utf-8") as fh:
        m1 = json.load(fh)
    shapes, cuts = {}, {}
    for g in m1["groups"]:
        if g["split"] != "full":
            continue
        cuts[g["dir"]] = {}
        for pk, st in g["planes"].items():
            shapes[pk] = tuple(st["shape"])
            cuts[g["dir"]][pk] = K_SIGMA * st["sigma_robust_dn"]

    print("re-thresholding at fixed full-map DN cut ...", flush=True)
    packed = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for d, out in ex.map(job, [(d, cuts[d]) for d in ALL_DIRS]):
            packed[d] = out
            print(f"  {d}", flush=True)

    res = {"cut_dn": cuts, "bar": J_BAR, "planes": {}, "sweep": {}, "strength": {}}
    rng = np.random.default_rng(SEED)
    recur_full, amp_full = {}, {}

    for pk in PLANES:
        shape = shapes[pk]
        rf = np.zeros(shape, dtype=np.uint8)
        ra = np.zeros(shape, dtype=np.uint8)
        rb = np.zeros(shape, dtype=np.uint8)
        for d in ALL_DIRS:
            rf += unpack(packed[d][f"full-{pk}"], shape)
            ra += unpack(packed[d][f"A-{pk}"], shape)
            rb += unpack(packed[d][f"B-{pk}"], shape)
        recur_full[pk] = rf

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
            rows.append({"r": r, "n_A": na, "n_B": nb, "n_full": int((rf >= r).sum()),
                         "jaccard": round(jac(a, b), 5),
                         "jaccard_placebo": round(jac(pa.reshape(shape), pb.reshape(shape)), 8)})
        res["sweep"][pk] = rows
        print(f"  {pk}: " + " ".join(f"r{x['r']}={x['jaccard']:.3f}" for x in rows), flush=True)

        # headline bar at the inherited r>=6
        i6 = rows[RECUR_MIN - 1]
        res["planes"][pk] = {
            "n_defect_r6": i6["n_full"], "jaccard_r6": i6["jaccard"],
            "jaccard_placebo_r6": i6["jaccard_placebo"],
            "n_always": int((rf == 11).sum()),
        }

        # strength stratification, on the ISO-100 group (gain-matched to bee-3-cpl)
        e100 = packed["118MSDCF"][f"exc-{pk}"].astype(np.float32)
        amp = np.zeros(shape, dtype=np.float32)
        amp[1:-1, 1:-1] = e100
        amp_full[pk] = amp
        a6, b6 = ra >= RECUR_MIN, rb >= RECUR_MIN
        full6 = rf >= RECUR_MIN
        bins = [(0, .5), (.5, 1), (1, 2), (2, 4), (4, 8), (8, 16), (16, 1e9)]
        strat = []
        for lo, hi in bins:
            sel = full6 & (amp >= lo) & (amp < hi)
            n = int(sel.sum())
            strat.append({"amp_dn": [lo, hi if hi < 1e8 else None], "n": n,
                          "recovered_both_halves": round(float((sel & a6 & b6).sum() / n), 4) if n else None})
        res["strength"][pk] = strat

    # low/high ISO mode containment at fixed cut
    for pk in PLANES:
        shape = shapes[pk]
        lo = np.zeros(shape, dtype=np.uint8)
        hi = np.zeros(shape, dtype=np.uint8)
        for d in LOW_DIRS:
            lo += unpack(packed[d][f"full-{pk}"], shape)
        for d in HIGH_DIRS:
            hi += unpack(packed[d][f"full-{pk}"], shape)
        lom, him = lo >= 3, hi >= 4
        res["planes"][pk].update({
            "n_low_mode": int(lom.sum()), "n_high_mode": int(him.sum()),
            "low_in_high": round(float((lom & him).sum() / lom.sum()), 5) if lom.sum() else None,
            "high_in_low": round(float((lom & him).sum() / him.sum()), 5) if him.sum() else None})

    tot = sum(res["planes"][p]["n_defect_r6"] for p in PLANES)
    res["TOTAL_r6"] = tot
    res["frac_of_sensor"] = tot / sum(shapes[p][0] * shapes[p][1] for p in PLANES)

    final = {}
    for pk in PLANES:
        final[f"{pk}-defect"] = np.packbits(recur_full[pk] >= RECUR_MIN)
        final[f"{pk}-always"] = np.packbits(recur_full[pk] == 11)
        final[f"{pk}-recur"] = recur_full[pk]
        final[f"{pk}-amp100"] = amp_full[pk]
        final[f"shape_{pk}"] = np.array(shapes[pk])
    np.savez_compressed(OUT / "defectmap-final.npz", **final)

    with open(OUT / "04-splithalf.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"TOTAL r>=6 at fixed cut: {tot} ({res['frac_of_sensor']*100:.4f}%)", flush=True)
    print("wrote 04-splithalf.json + defectmap-final.npz", flush=True)


if __name__ == "__main__":
    main()

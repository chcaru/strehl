"""M101 script 05 - an amplitude estimator, and the operating point that meets B1.

Recurrence >= 6/11 (M22's and M48c's criterion) fails the pre-registered
split-half bar at 0.40 (G2) / 0.38 (B), and on R/G1 it reads 0.077 / 0.074, which
is noise. Script 04's strength table shows why: recovery rises monotonically with
amplitude, so the >= 6/11 set is dominated by sites near the detection cut.

This replaces the count-based statistic with a physical one. M48c fact 14
established excess_DN = e * gain(ISO), so the gain-normalised excess is an
ISO-invariant amplitude in electrons; the median across the 11 ISO groups is a
robust estimator of it that uses all 242 frames at once and needs no recurrence
count. The bar is unchanged at J >= 0.80; the amplitude cut that meets it is
measured, not chosen.

Selection is computed independently within each half (A's cut uses A's own
amplitudes) so the split-half score is not inflated by shared information.

Reads  : C:\\dev\\strehl-out\\M101\\means\\*.npy, 00-probe.json
Writes : C:\\dev\\strehl-out\\M101\\05-amplitude.json, defectmap-amp.npz
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
BLACK = 512.0
GAIN_DIVISOR = 436.8
SEED = 101
J_BAR = 0.80
CUTS_E = [0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 40, 60, 100]


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


def amp_plane(args):
    """Median across the 11 ISO groups of the gain-normalised neighbour excess."""
    pk, split, isos = args
    stack = None
    for i, d in enumerate(ALL_DIRS):
        mf = np.load(MEANS / f"mean-{d}-{split}.npy")
        oy, ox = PLANE_OFF[pk]
        pl = mf[oy::2, ox::2] - BLACK
        e = (pl - med8(pl)) / (max(isos[d], 100) / GAIN_DIVISOR)  # DN -> electrons
        if stack is None:
            stack = np.empty((11,) + e.shape, dtype=np.float32)
        stack[i] = e
    med = np.median(stack, axis=0)
    med[0, :] = med[-1, :] = med[:, 0] = med[:, -1] = 0.0  # drop padded border
    return pk, split, med


def jac(a, b):
    u = int(np.count_nonzero(a | b))
    return int(np.count_nonzero(a & b)) / u if u else float("nan")


def main():
    with open(OUT / "00-probe.json", "r", encoding="utf-8") as fh:
        probe = json.load(fh)
    isos = {g["dir"]: int(g["iso"]) for g in probe["dark_groups"]}

    jobs = [(pk, sp, isos) for pk in PLANES for sp in ("full", "A", "B")]
    amps = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for pk, sp, med in ex.map(amp_plane, jobs):
            amps[(pk, sp)] = med
            print(f"  amplitude {pk}/{sp}: p50={np.median(med):+.4f} "
                  f"max={med.max():.1f} e-", flush=True)

    rng = np.random.default_rng(SEED)
    res = {"cuts_e": CUTS_E, "bar": J_BAR, "sweep": {}, "noise_floor": {}}
    for pk in PLANES:
        af, aa, ab = amps[(pk, "full")], amps[(pk, "A")], amps[(pk, "B")]
        # noise floor of the amplitude statistic itself, from its negative half
        neg = af[af < 0]
        sig = float(1.4826 * np.median(np.abs(neg - np.median(neg))))
        res["noise_floor"][pk] = {"robust_sigma_e": round(sig, 4),
                                  "p50_e": round(float(np.median(af)), 4)}
        rows = []
        for c in CUTS_E:
            a, b, f = aa >= c, ab >= c, af >= c
            na, nb = int(a.sum()), int(b.sum())
            pa = np.zeros(a.size, dtype=bool)
            pb = np.zeros(b.size, dtype=bool)
            if na:
                pa[rng.choice(a.size, na, replace=False)] = True
            if nb:
                pb[rng.choice(b.size, nb, replace=False)] = True
            rows.append({"cut_e": c, "cut_sigma": round(c / sig, 2),
                         "n_full": int(f.sum()), "n_A": na, "n_B": nb,
                         "jaccard": round(jac(a, b), 5),
                         "jaccard_placebo": round(jac(pa.reshape(a.shape),
                                                      pb.reshape(b.shape)), 8)})
        res["sweep"][pk] = rows
        ok = [r["cut_e"] for r in rows if r["jaccard"] >= J_BAR]
        res.setdefault("cut_meeting_bar", {})[pk] = min(ok) if ok else None
        print(f"  {pk} sigma={sig:.3f} e-  " +
              " ".join(f"{r['cut_e']:g}:{r['jaccard']:.3f}" for r in rows), flush=True)

    cuts = [res["cut_meeting_bar"][p] for p in PLANES]
    c_star = max([c for c in cuts if c is not None], default=None)
    res["c_star_e"] = c_star
    print(f"  c* = {c_star} e-  (meets J >= {J_BAR} on every plane)", flush=True)

    final, counts = {}, {}
    for pk in PLANES:
        af = amps[(pk, "full")]
        m = af >= c_star
        final[f"{pk}-defect"] = np.packbits(m)
        final[f"{pk}-amp_e"] = af.astype(np.float32)
        final[f"shape_{pk}"] = np.array(af.shape)
        counts[pk] = int(m.sum())
    counts["TOTAL"] = sum(counts[p] for p in PLANES)
    res["final_counts"] = counts
    res["frac_of_sensor"] = counts["TOTAL"] / sum(
        int(np.prod(final[f"shape_{p}"])) for p in PLANES)
    np.savez_compressed(OUT / "defectmap-amp.npz", **final,
                        c_star=np.array([c_star]))
    with open(OUT / "05-amplitude.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"  final: {counts}  ({res['frac_of_sensor']*100:.4f}% of sensor)", flush=True)
    print("wrote 05-amplitude.json + defectmap-amp.npz", flush=True)


if __name__ == "__main__":
    main()

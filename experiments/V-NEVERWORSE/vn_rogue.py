"""One frame out of 287 holds 62% of a band. Measure it four ways.

Section 9.25.5 found the `bee-2-cpl` coarse-band selection cost to be BIMODAL
in N -- ~0.003 at N=144, ~0.81 at N=170-230, ~0.003 again at N=260, ~0.82 at
N=273-287. A quantity that flips between two values as N rises is not a
function of N, so the N reading was withdrawn before it was reported. This
script finds what the switch actually is.

FOUR MEASUREMENTS, each answering a different objection to the one before:

  dense   The N ladder at matched focus range, sampled by linspace so N is not
          restricted to power-of-two strides. Establishes that the jump is a
          switch and not a curve.
  conc    Per half, at L5: which source frame carries the most weight, what
          share it holds, and the effective frame count. Answers "what is
          different about the rungs that read high".
  f46     What that frame IS -- mean level, noise, and per-band energy against
          the stack median. Answers "is it a focus winner or a broken frame".
  rogue   The share it receives under the shipping absolute-gate law and under
          ORCH's proposed `r_max`-relative law at three thetas. Answers "does
          the fix in flight contain this or amplify it".

The image-space reading lives in `vn_rogue_img.py`, because a weight share is
a property of the estimator and only a DN difference between two renders is a
property of the picture.

Reads cached bundles only. Never writes to D:.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_pyr as VP  # noqa: E402
import vn_subgate as SG  # noqa: E402

OUT = SG.OUT
SUBJ = "bee-2-cpl"
RULE = "registered"
ROGUE = 46
K = 5
DENSE_N = (144, 170, 200, 230, 260, 273, 280, 287)
CONC_N = (144, 170, 260, 287)
BANDS = (0, 3, 4, 5, 6)
THETAS = (0.25, 0.5, 0.75)


def rungs(n, m):
    """Matched-range subsample of size m. `linspace` rather than a stride so
    N is a free parameter; a stride ladder can only take N in factors of the
    total and cannot resolve a switch from a curve."""
    return sorted(set(np.linspace(0, n - 1, m).round().astype(int).tolist()))


def band_r(frames, varp, k):
    """`r = excess / floor / SNR_REF` per frame at band k, exactly as
    `pyramid.rs` forms it, including the `max(floor, 1.0)` clamp that matters
    at the coarse bands because BETA collapses there."""
    floor = np.maximum(SG.GATE * SG.BETA[k] * np.maximum(varp[k], 0.0), 1.0)
    out = []
    for f in frames:
        lap, _ = VP.lap_pyr(f, SG.NB)
        ex = VP.smooth5(lap[k] ** 2) - floor
        out.append(np.where(ex > 0.0, ex / floor / VP.SNR_REF, 0.0))
    return out


def main():
    import vn_gbundle as GB
    frames, kept, meta = GB.load(SUBJ, rule=RULE)
    n = len(frames)
    var0 = VP.fit_variance(frames[0])[0]
    varp = VP.gauss_pyr(var0, SG.NB)
    res = dict(subject=SUBJ, rule=RULE, n=n, rogue_source_index=ROGUE,
               span=[int(kept[0]), int(kept[-1])])
    jr = [j for j in range(n) if int(kept[j]) == ROGUE]
    if not jr:
        print("REFUSED: source frame %d is not in the admitted set" % ROGUE)
        return 1
    jr = jr[0]

    # --- dense: is the jump a cliff or a curve? -------------------------
    dense = []
    for m in DENSE_N:
        idx = rungs(n, m)
        rows, _ = SG.subgate([frames[i] for i in idx])
        d = {x["band"]: x for x in rows}
        dense.append(dict(n=len(idx), span=[int(kept[idx[0]]),
                                            int(kept[idx[-1]])],
                          rogue_present=bool(jr in idx),
                          sel_cost={str(k): float(d[k]["sel_cost"])
                                    for k in (3, 4, 5, 6)}))
        print("dense N=%-4d rogue %s  " % (len(idx),
                                           "IN " if jr in idx else "out")
              + "  ".join("L%d %+0.4f" % (k, d[k]["sel_cost"])
                          for k in (3, 4, 5, 6)))
    res["dense"] = dense
    # Every rung must span the same focus range or the ladder measures depth
    # and frame count at once.
    res["dense_matched_range"] = bool(
        all(x["span"] == dense[0]["span"] for x in dense))

    # --- conc: where does the weight go? --------------------------------
    conc = []
    for m in CONC_N:
        idx = rungs(n, m)
        A, _ = SG.halfsplit(len(idx))
        sa = set(A)
        per = {0: [], 1: []}
        who = {0: [], 1: []}
        for j, i in enumerate(idx):
            lap, _ = VP.lap_pyr(frames[i], SG.NB)
            fl = np.maximum(SG.GATE * SG.BETA[K]
                            * np.maximum(varp[K], 0.0), 1.0)
            ex = VP.smooth5(lap[K] ** 2) - fl
            r = np.where(ex > 0.0, ex / fl / VP.SNR_REF, 0.0)
            w = r ** SG.EXPO[K]
            h = 0 if j in sa else 1
            per[h].append(float(w.sum()))
            who[h].append(int(kept[i]))
        row = dict(n=len(idx), rogue_present=bool(jr in idx))
        for h, tag in ((0, "A"), (1, "B")):
            v = np.array(per[h])
            s = v.sum()
            t = int(v.argmax())
            row[tag + "_top"] = who[h][t]
            row[tag + "_share"] = float(v[t] / s) if s > 0 else float("nan")
            row[tag + "_neff"] = (float((s * s) / (v * v).sum())
                                  if s > 0 else float("nan"))
        conc.append(row)
        print("conc  N=%-4d A top %4d share %.4f neff %6.2f | "
              "B top %4d share %.4f neff %6.2f"
              % (row["n"], row["A_top"], row["A_share"], row["A_neff"],
                 row["B_top"], row["B_share"], row["B_neff"]))
    res["conc"] = conc

    # --- f46: what is that frame? ---------------------------------------
    per = []
    for j, f in enumerate(frames):
        lap, _ = VP.lap_pyr(f, SG.NB)
        per.append((int(kept[j]), float(f.mean()), float(f.std()),
                    [float(np.mean(lap[k] ** 2)) for k in range(SG.NB)]))
    mu = np.array([p[1] for p in per])
    sd = np.array([p[2] for p in per])
    f46 = dict(source_index=ROGUE, mean_dn=per[jr][1], std_dn=per[jr][2],
               stack_median_mean_dn=float(np.median(mu)),
               stack_median_std_dn=float(np.median(sd)),
               mean_dn_ratio=float(per[jr][1] / np.median(mu)),
               std_dn_ratio=float(per[jr][2] / np.median(sd)), bands=[])
    for k in range(SG.NB):
        v = np.array([p[3][k] for p in per])
        med = float(np.median(v))
        f46["bands"].append(dict(band=k, median_energy=med,
                                 rogue_energy=float(v[jr]),
                                 ratio=float(v[jr] / med) if med else None,
                                 rank=int((v > v[jr]).sum()) + 1))
    res["f46"] = f46
    print("f46   mean %.1f DN (%.3fx stack median), std %.1f DN (%.3fx)"
          % (f46["mean_dn"], f46["mean_dn_ratio"], f46["std_dn"],
             f46["std_dn_ratio"]))

    # --- rogue: does the proposed fix contain it or amplify it? ---------
    rog = []
    for k in BANDS:
        st = np.stack(band_r(frames, varp, k))
        rmax = st.max(axis=0)
        row = dict(band=k, entitlement=1.0 / n)
        w = st ** SG.EXPO[k]
        s = w.sum(axis=0)
        row["shipping"] = float(np.mean(
            np.where(s > 0, w[jr] / np.where(s > 0, s, 1.0), 0.0)))
        for th in THETAS:
            w2 = np.maximum(st - th * rmax, 0.0) ** SG.EXPO[k]
            s2 = w2.sum(axis=0)
            row["rmax%.2f" % th] = float(np.mean(
                np.where(s2 > 0, w2[jr] / np.where(s2 > 0, s2, 1.0), 0.0)))
        rog.append(row)
        print("rogue L%d ship %.5f  " % (k, row["shipping"])
              + "  ".join("rmax%.2f %.5f" % (t, row["rmax%.2f" % t])
                          for t in THETAS))
        del st, w, s
    res["rogue"] = rog

    p = os.path.join(OUT, "rogue.json")
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

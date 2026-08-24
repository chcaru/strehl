"""Score an edge dump against the independent truth ladder.

Every edge (i, j) is compared with truth(i, j) = L(j) - L(i), where L is the
log-scale curve `truth.py` measured directly from RAW with no strehl code in
the path. The drift is *not* linear in frame index (M84b fact 1155 measured the
focus step drifting 1.53x across a stack), so an edge must be scored against
truth at its own baseline, never against a uniform-rate extrapolation.

usage: python score.py <edges.csv> <truth.json> [label]
"""

import csv
import json
import math
import sys

import numpy as np


def load_truth(path):
    with open(path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    rows = sorted((int(k), float(v["ln"])) for k, v in d["ladder"].items())
    rows = [r for r in rows if r[0] != 0]
    rows.insert(0, (0, 0.0))
    js = np.array([r[0] for r in rows], dtype=float)
    ls = np.array([r[1] for r in rows], dtype=float)
    return js, ls


def main():
    edges_path, truth_path = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else edges_path

    js, ls = load_truth(truth_path)

    def L(x):
        return float(np.interp(x, js, ls))

    with open(edges_path, "r", encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    rows = list(csv.DictReader(lines))

    by_span = {}
    ok = 0
    for r in rows:
        if r["status"].strip().lower() != "ok":
            by_span.setdefault(int(r["span"]), {"ref": 0, "e": []})["ref"] += 1
            continue
        ok += 1
        i, j = int(r["i"]), int(r["j"])
        s = int(r["span"])
        m = 0.5 * math.log(float(r["a_re"]) ** 2 + float(r["a_im"]) ** 2)
        t = L(j) - L(i)
        b = by_span.setdefault(s, {"ref": 0, "e": []})
        b["e"].append(
            {
                "i": i,
                "j": j,
                "m": m,
                "t": t,
                "rec": (m / t) if abs(t) > 1e-9 else float("nan"),
                "used": int(r["used"]),
                "peak": float(r["peak"]),
                "border": int(r["border"]),
                "lowpk": int(r["low_peak"]),
                "lever": float(r["lever"]),
                "rms": float(r["rms"]),
            }
        )

    print(f"=== {label} ===")
    print(f"edges ok {ok} / {len(rows)}")
    print(
        f"{'span':>5} {'ok':>4} {'ref':>4} {'used':>6} {'peak':>6} {'bord':>5} "
        f"{'lowpk':>5} {'lever':>6} {'rms':>6} {'recov':>7} {'chain':>8}"
    )
    for s in sorted(by_span):
        b = by_span[s]
        e = b["e"]
        if not e:
            print(f"{s:>5} {0:>4} {b['ref']:>4}")
            continue
        recs = [x["rec"] for x in e if not math.isnan(x["rec"])]
        med = float(np.median(recs)) if recs else float("nan")
        # B1: telescope this span's edges from 0 to the far end and compare
        # with the truth total over the same interval.
        chain = walk(e, s)
        print(
            f"{s:>5} {len(e):>4} {b['ref']:>4} {np.mean([x['used'] for x in e]):>6.1f} "
            f"{np.mean([x['peak'] for x in e]):>6.4f} "
            f"{np.mean([x['border'] for x in e]):>5.1f} "
            f"{np.mean([x['lowpk'] for x in e]):>5.1f} "
            f"{np.mean([x['lever'] for x in e]):>6.0f} "
            f"{np.mean([x['rms'] for x in e]):>6.3f} "
            f"{med:>7.3f} {chain:>8}"
        )

    direct = [
        x
        for s in by_span
        for x in by_span[s]["e"]
        if x["i"] == 0 and x["j"] == max(js.astype(int))
    ]
    if direct:
        d = direct[0]
        print(
            f"\nDIRECT (0,{d['j']}): measured {d['m']:.6f}  truth {d['t']:.6f}  "
            f"recovery {d['rec']:.4f}  used {d['used']}  peak {d['peak']:.4f}"
        )
    else:
        print(f"\nDIRECT (0,{int(max(js))}): REFUSED or absent")


def walk(edges, span):
    """Sum a chain of same-span edges from frame 0 as far as it reaches."""
    idx = {(x["i"], x["j"]): x for x in edges}
    tot_m, tot_t, k, n = 0.0, 0.0, 0, 0
    while (k, k + span) in idx:
        e = idx[(k, k + span)]
        tot_m += e["m"]
        tot_t += e["t"]
        k += span
        n += 1
    if n == 0 or abs(tot_t) < 1e-9:
        return "-"
    return f"{tot_m / tot_t:.3f}@{k}"


if __name__ == "__main__":
    main()

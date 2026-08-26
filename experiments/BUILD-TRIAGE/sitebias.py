"""Did the level bias actually touch the sites the MERGE-LIMITED verdict rests on?

levelbias.py showed that 19 of 26 subjects contain at least one block whose
argmax moves under level correction.  Most of that is meaningless: a block with
a flat through-focus curve has an argmax made of noise, and it will jump the
whole bracket under any perturbation at all.  The same trap as raw boundary %,
and it must not be over-read in either direction.

What matters is narrower and answerable: for the four sites compare.py actually
measured on each subject, does the best-frame pick move once the level trace is
divided out, AND does that site have a peak prominent enough for its argmax to
mean anything?  Only sites that fail BOTH tests need re-measuring against a
corrected source frame.

Prominence is (peak - median) / (peak - min) on the corrected curve: it asks
whether the peak stands out from the body of the curve, not merely from its
minimum, so a monotonic ramp does not masquerade as a peak.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

PROM = 0.55        # peak must clear the body of its own curve
MOVE = 5           # frames; below this the source arm is effectively unchanged


def main() -> int:
    out_rows = []
    need: dict[str, list] = {}
    for p in sorted(glob.glob(os.path.join(tri.OUT, "compare", "*.json"))):
        name = os.path.basename(p)[:-5]
        if "." in name:                     # skip tagged regional/control runs
            continue
        with open(p, encoding="utf-8") as fh:
            cmp_ = json.load(fh)
        fp = os.path.join(tri.OUT, "focus", name + ".json")
        if not os.path.exists(fp):
            continue
        with open(fp, encoding="utf-8") as fh:
            foc = json.load(fh)
        lv = np.array(foc["level_dn"], np.float64)
        sampled = foc["sampled"]
        by_rc = {(b["r"], b["c"]): b for b in foc["blocks"]}

        for label, s in cmp_["sites"].items():
            blk = s.get("block")
            if not blk:
                continue
            b = by_rc.get(tuple(blk))
            if b is None:
                continue
            c = np.array(b["curve"], np.float64)
            if c.size != lv.size or c.max() <= 0:
                continue
            cc = c / lv
            a_cor = int(np.argmax(cc))
            f_cor = sampled[a_cor]
            f_used = int(s["best_frame"])
            move = abs(f_cor - f_used)
            rng = float(cc.max() - cc.min())
            prom = ((float(cc.max()) - float(np.median(cc))) / rng) if rng > 0 else 0.0
            row = {
                "subject": name, "site": label, "block": blk,
                "frame_used": f_used, "frame_corrected": int(f_cor),
                "move": int(move), "prominence": round(prom, 3),
                "drift": round(float(lv[-1] / max(lv[0], 1e-9)), 3),
                "matters": bool(move > MOVE and prom >= PROM),
            }
            out_rows.append(row)
            if row["matters"]:
                need.setdefault(name, []).append(row)

    out_rows.sort(key=lambda r: (-int(r["matters"]), -r["move"]))
    print(f"{'subject':36s} {'site':12s} {'used':>5s} {'corr':>5s} "
          f"{'move':>5s} {'prom':>5s}  matters")
    for r in out_rows[:28]:
        print(f"{r['subject']:36s} {r['site']:12s} {r['frame_used']:5d} "
              f"{r['frame_corrected']:5d} {r['move']:5d} {r['prominence']:5.2f}"
              f"  {'YES' if r['matters'] else ''}")

    n_sites = len(out_rows)
    n_matter = sum(1 for r in out_rows if r["matters"])
    print(f"\nsites examined                : {n_sites}")
    print(f"sites whose source frame moves >{MOVE} frames "
          f"AND have a prominent peak : {n_matter}")
    print(f"subjects needing re-measurement: {len(need)}"
          + (("  -> " + ", ".join(sorted(need))) if need else ""))

    outp = os.path.join(tri.OUT, "sitebias.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump({"prominence_gate": PROM, "move_gate": MOVE,
                   "rows": out_rows, "need": sorted(need)}, fh, indent=1)
    print(f"-> {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Decompose the gatefloor verdict into absolute structure and absolute noise.

WHY THIS EXISTS

`headscore.py`'s `sharp` axis is p99.5 / MAD within a band -- a contrast-to-NOISE
ratio. It is scale-invariant, which is why it survives strehl's per-image tone
normalisation, but it has a specific blind spot that matters here: an arm that
merely gets QUIETER scores higher on it without resolving anything more. On
`leaf-2-cpl` the default (measured floor) beat `STREHL_GATE_FLOOR=white` by
sharp 1.3420 while grain said the default was 2.30x quieter, so the entire
sharpness margin could in principle be the denominator moving.

That distinction decides ORCH's question. His chain is:

    measured floor is stricter -> the gate averages more -> the print softens

and BUILD-PLUGIN independently measured -9.9% to -39.9% sharpness attributed to
the floor fix. If the default's sharpness win here is purely a quieter
denominator, both are consistent with my data and the fix really does soften.
If the default also carries MORE ABSOLUTE STRUCTURE, the chain's last link is
false and the fix is a strict improvement.

`recertlib.band_stats` already separates these: `floor` is the MAD, `peak` is
the absolute p99.5, and `structure` is the peak with the band's own noise
contribution removed (`_structure(peak, floor, band)`), i.e. an ABSOLUTE
amplitude that does not fall merely because the image got noisier.

ORIENTATION, stated once so it cannot be misread downstream:
  base = DEF  (measured floor: the LANDED FIX, and the shipping default)
  cand = WHITE (STREHL_GATE_FLOOR=white: the OLD behaviour the fix replaced)
  a ratio BELOW 1 therefore means the old behaviour has LESS of that quantity.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flatexp as F  # noqa: E402
import recertlib as R  # noqa: E402

DEF = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\arms\DEF-2f858c62")
WHITE = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\gatefloor")
OUT = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\logs\gatefloor-decomp.json")

SUBJECTS = ["leaf-2-cpl", "coffee-bubbles"]

out = []
print("base = DEF (measured floor, the landed fix)   "
      "cand = WHITE (old behaviour)\n")
hdr = (f"{'subject':<16}{'band':<8}{'n':>3}"
       f"{'struct base':>12}{'struct cand':>12}{'struct x':>10}"
       f"{'floor base':>12}{'floor cand':>12}{'floor x':>9}")
print(hdr)
print("-" * len(hdr))
for s in SUBJECTS:
    r = F.score_subject(s, paths=(DEF / f"{s}--DEF-2f858c62.tiff",
                                  WHITE / f"{s}--WHITE.tiff"))
    if r["state"] != "SCORED":
        print(f"{s:<16}{r['state']}")
        out.append({"subject": s, "state": r["state"]})
        continue
    rec = {"subject": s, "state": "SCORED", "bands": {}}
    for band in R.BANDS:
        cells = [c for c in r["cells"] if c["band"] == band]
        # Structure and floor refuse INDEPENDENTLY, so they are pooled over
        # different cell sets. Pooling both over the intersection would discard
        # a valid floor because the sharpness half of the same cell refused --
        # the exact defect flatexp records at its `floor_ok` / `struct_ok` split.
        sc = [c for c in cells if c["struct_ok"]
              and c["base_struct"] and c["cand_struct"]]
        fc = [c for c in cells if c["floor_ok"] and c["base_floor"] > 0]
        if not sc and not fc:
            continue
        sb = float(np.median([c["base_struct"] for c in sc])) if sc else float("nan")
        scd = float(np.median([c["cand_struct"] for c in sc])) if sc else float("nan")
        fb = float(np.median([c["base_floor"] for c in fc])) if fc else float("nan")
        fcd = float(np.median([c["cand_floor"] for c in fc])) if fc else float("nan")
        sx = scd / sb if sc and sb > 0 else float("nan")
        fx = fcd / fb if fc and fb > 0 else float("nan")
        rec["bands"][band] = {"n_struct": len(sc), "n_floor": len(fc),
                              "base_struct": sb, "cand_struct": scd, "struct_x": sx,
                              "base_floor": fb, "cand_floor": fcd, "floor_x": fx}
        print(f"{s:<16}{band:<8}{len(sc):>3}"
              f"{sb:12.4f}{scd:12.4f}{sx:10.4f}"
              f"{fb:12.4f}{fcd:12.4f}{fx:9.4f}")
    out.append(rec)

print("\n\nADJUDICATION -- is the default's sharpness win real resolution,")
print("or only a quieter denominator?\n")
verdicts = []
for rec in out:
    if rec.get("state") != "SCORED":
        continue
    for band, b in rec["bands"].items():
        sx, fx = b["struct_x"], b["floor_x"]
        # Two-sided and NaN-guarded: `NaN > x` is False, so an unguarded
        # comparison silently reads a failed measurement as a pass.
        if not (np.isfinite(sx) and np.isfinite(fx)):
            v = "NOT MEASURABLE"
        elif sx < 0.99 and fx > 1.01:
            v = "DEFAULT WINS ON BOTH -- more structure AND less noise"
        elif sx > 1.01 and fx > 1.01:
            v = "TRADE -- old arm resolves more but is noisier"
        elif abs(sx - 1) <= 0.01 and fx > 1.01:
            v = "DENOMINATOR ONLY -- equal structure, default merely quieter"
        elif abs(sx - 1) <= 0.01 and abs(fx - 1) <= 0.01:
            v = "NO DIFFERENCE"
        else:
            v = f"struct x{sx:.4f}  floor x{fx:.4f}"
        verdicts.append((rec["subject"], band, v))
        print(f"  {rec['subject']:<16}{band:<8}{v}")

OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"\nwrote {OUT}")

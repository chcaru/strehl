"""M126-default-audit — mask-source sensitivity of the merge-vs-single-frame contrast.

WHY. PREREG section 4 requires the single-sharpest-frame baseline because
SYNTHESIS fact 1701 (V-M116) reports that on `tweezers-cpl` the single frame
BEATS the unaligned merge on `Q`: `B1u` 0.37376 vs `B0` 0.84177.

Scoring the same two renders with masks from `M0u` (the gate-0 unaligned merge)
I get the opposite sign: `B1u` 0.91804 vs `B0` 0.72043, the merge ahead by
+0.198 dex. The `D` contrast, by contrast, reproduces V-M116's published
+0.15207 / +0.33319 to five decimal places -- so the arithmetic agrees and only
the mask population differs.

Fact 1700 states V-M116 took masks "from `B0` so that neither merge chose
them". That is the one free parameter between us. This script scores the pair
BOTH ways and reports the swing, so the report can say which choice produces
which sign instead of asserting one of them.

Nothing here is a new metric: `score_plane`, `structure` and the quantile cuts
are imported unchanged from score.py.

    python experiments\\M126-default-audit\\masksource.py
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from score import (  # noqa: E402
    DET_FRAC, FLAT_FRAC, MEASURE, ROOT, SUBJECTS, green, score_plane, structure,
)

DRIFT = {
    "bee-3-cpl": 1.629, "lead-1-cpl": 2.026, "leaf-2-cpl": 5.315,
    "coffee-bean": 12.065, "tweezers-cpl": 13.765,
}


def masks_from(tag: str, subject: str):
    p = MEASURE / f"{subject}__{tag}.tif"
    if not p.exists():
        return None
    st = structure(green(p))
    return st <= np.quantile(st, FLAT_FRAC), st >= np.quantile(st, 1.0 - DET_FRAC)


def main() -> int:
    out = {}
    print("## Mask-source sensitivity of the degenerate-baseline contrast\n")
    print("Same two renders (`B1u-noalign`, `B0-single`), same metric, "
          "only the arm the masks come from changes.\n")
    print("| subject | drift | mask source | Q(B1u) | Q(B0) | Q(B1u)-Q(B0) | "
          "D(B1u)-D(B0) | winner on Q |")
    print("|---|---|---|---|---|---|---|---|")
    for s in SUBJECTS:
        row = {}
        for mask_tag in ("M0u", "B0"):
            m = masks_from(mask_tag, s)
            if m is None:
                continue
            mflat, mdet = m
            vals = {}
            for tag in ("B1u", "B0"):
                p = MEASURE / f"{s}__{tag}.tif"
                if not p.exists():
                    break
                g = green(p)
                if g.shape != mflat.shape:
                    print(f"| `{s}` | | {mask_tag} | shape mismatch | | | | |")
                    break
                vals[tag] = score_plane(g, mflat, mdet)
            if len(vals) != 2:
                continue
            dq = vals["B1u"]["Q"] - vals["B0"]["Q"]
            dd = vals["B1u"]["D"] - vals["B0"]["D"]
            row[mask_tag] = {"B1u": vals["B1u"], "B0": vals["B0"], "dQ": dq, "dD": dd}
            print(f"| `{s}` | {DRIFT[s]:.3f} | `{mask_tag}` | {vals['B1u']['Q']:.5f} | "
                  f"{vals['B0']['Q']:.5f} | {dq:+.5f} | {dd:+.5f} | "
                  f"{'merge' if dq > 0 else '**single frame**'} |")
        if "M0u" in row and "B0" in row:
            row["swing_dQ"] = row["M0u"]["dQ"] - row["B0"]["dQ"]
        out[s] = row

    print("\n### Swing attributable to the mask source alone\n")
    print("| subject | dQ with M0u masks | dQ with B0 masks | swing | sign flips? |")
    print("|---|---|---|---|---|")
    for s in SUBJECTS:
        r = out.get(s, {})
        if "swing_dQ" not in r:
            continue
        a, b = r["M0u"]["dQ"], r["B0"]["dQ"]
        print(f"| `{s}` | {a:+.5f} | {b:+.5f} | {r['swing_dQ']:+.5f} | "
              f"{'**YES**' if (a > 0) != (b > 0) else 'no'} |")

    (ROOT / "masksource.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'masksource.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

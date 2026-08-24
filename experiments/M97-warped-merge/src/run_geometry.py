"""Run the geometry metrics over every M97 arm and tabulate.

Usage: run_geometry.py <out.json> <label>=<path> ...
"""

import json
import sys

from geometry import luma, spacing, straightness


def main() -> None:
    dst = sys.argv[1]
    rows = []
    for spec in sys.argv[2:]:
        label, path = spec.split("=", 1)
        img = luma(path)
        rec = {"label": label, "path": path}
        rec.update(straightness(img))
        rec.update(spacing(img))
        rows.append(rec)
        print(
            f"{label:10s} S_raw {rec['S_rms_raw_px']:7.3f}  S_block {rec['S_rms_block_px']:7.3f}  "
            f"bow {rec['S_bow_px']:+8.3f}  ptp {rec['S_block_ptp_px']:7.3f}  "
            f"ticks {rec['G_ticks']:3d}  G_rms {rec.get('G_rms_px', float('nan')):7.3f}  "
            f"G/space {rec.get('G_rms_frac_of_spacing', float('nan')):7.4f}",
            flush=True,
        )
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()

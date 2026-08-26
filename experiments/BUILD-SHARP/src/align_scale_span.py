"""Item 4: does the aligner already absorb the magnification ramp?

ORCH relayed a lead claiming the EXIF implies ~13% magnification drift across a
205-frame bracket while the aligner's "scale ladder" spans only 1.000233, i.e.
that the aligner models essentially none of it and every frame is misregistered
in a radius-dependent way.

`align.rs:235-241` says the fitted per-frame transform is a Similarity whose
`SimilarityParams::g` is "Scale minus one. `+0.01` is a 1% magnification". So
magnification is a FITTED PARAMETER OF THE WARP, not something a separate ladder
has to contain. This reads it straight off the sidecar the merge actually used.

Note the phrase "scale ladder" is overloaded in this repository: `photometric.rs`
uses it for a per-frame GAIN ladder and `align.rs:556` for the coarse DECIMATION
ladder of the search pyramid. Neither is the magnification model.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\dev\strehl-out\BUILD-SHARP\warpcache\flower-bud-alone-cpl-4c58ad95fe89ce86.warpmap.txt"
)


def f64(tok: str) -> float:
    """Sidecar f64s are hex bit patterns; trailing decimals are a comment."""
    return struct.unpack(">d", bytes.fromhex(tok.zfill(16)))[0]


def main() -> int:
    plane = None
    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("plane "):
            w, h = s.split()[1].split("x")
            plane = (int(w), int(h))
        if not s or s.startswith("#") or not s[0].isdigit():
            continue
        tok = s.split("#")[0].split()
        # idx state a_re a_im b_re b_im
        if len(tok) >= 6 and tok[1] == "placed":
            try:
                rows.append((int(tok[0]), f64(tok[2]), f64(tok[3]), f64(tok[4]), f64(tok[5])))
            except (ValueError, struct.error):
                continue
    if not rows:
        print("no placements parsed")
        return 2

    idx = np.array([r[0] for r in rows])
    a_re = np.array([r[1] for r in rows])
    a_im = np.array([r[2] for r in rows])
    scale = np.hypot(a_re, a_im)

    # Half-diagonal of the plane: the largest radius a real pixel sits at.
    r_max = float(np.hypot(plane[0] / 2, plane[1] / 2)) if plane else 3500.0

    print(f"sidecar   : {SRC.name}")
    print(f"plane     : {plane}, half-diagonal {r_max:.0f} px")
    print(f"placements: {len(rows)}  (frame index {idx.min()}..{idx.max()})")
    print()
    print("FITTED PER-FRAME SCALE |a|, straight off the sidecar the merge used:")
    print(f"  min      {scale.min():.8f}")
    print(f"  max      {scale.max():.8f}")
    print(f"  span     {scale.max() - scale.min():.8f}   "
          f"({100 * (scale.max() - scale.min()):.4f} % magnification)")
    print(f"  p1..p99  {np.percentile(scale, 1):.8f} .. {np.percentile(scale, 99):.8f}")
    print()
    print("What that span is worth as a displacement at the plane corner:")
    print(f"  (max-min) * r_max = {(scale.max() - scale.min()) * r_max:.2f} px")
    print()
    print("The claim under test predicted ~13 % here, and a ~450 px corner error.")
    print("The null that makes this measurement meaningful: if the aligner did")
    print("NOT fit scale, every |a| would be exactly 1.0 and the span would be 0.")
    print(f"  frames with |a| exactly 1.0 : {int((scale == 1.0).sum())} of {len(scale)}")
    print(f"  distinct |a| values         : {len(np.unique(scale))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

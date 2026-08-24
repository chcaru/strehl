"""s01: contact-sheet previews of candidate stacks, green plane, downsampled.

Structure only.  No frequency-domain quantity is computed here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m88lib import load_active, green_sites  # noqa: E402

CORPUS = Path(r"D:\personal\macro")
OUT = Path(__file__).resolve().parents[1] / "out" / "previews"


def preview(stack, frac_list=(0.0, 0.25, 0.5, 0.75, 1.0), down=6):
    files = sorted(CORPUS.joinpath(stack).glob("*.ARW"))
    if not files:
        print(f"  {stack}: no ARW")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    n = len(files)
    for fr in frac_list:
        i = min(n - 1, int(round(fr * (n - 1))))
        a = load_active(files[i])
        sub, _, _ = green_sites(a, "G1")
        s = sub[::down, ::down]
        lo, hi = np.percentile(s, [0.5, 99.5])
        img = np.clip((s - lo) / max(hi - lo, 1e-6), 0, 1)
        img = np.sqrt(img)  # gamma for visibility
        Image.fromarray((img * 255).astype(np.uint8)).save(
            OUT / f"{stack}_f{i:03d}.png")
        print(f"  {stack} frame {i}/{n-1} -> {sub.shape} down{down} "
              f"p0.5={lo:.0f} p99.5={hi:.0f}")


if __name__ == "__main__":
    for st in sys.argv[1:]:
        print(st)
        preview(st)

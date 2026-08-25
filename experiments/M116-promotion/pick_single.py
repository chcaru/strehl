"""M116-promotion — pick the sharpest single source frame, per prereg section 6.

"Sharpest" is defined as the frame index that wins the most pixels in the A0
election map, which `--index-map` writes and which the CLI documents as byte
inert. That is a frame CHOICE made by the pipeline. It is not a metric and it
enters no score.

Copies the chosen ARW out of the read-only capture library into
C:\\dev\\strehl-out\\M116\\single\\<subject>\\ so that it can be rendered alone.
D:\\ is never written.
"""

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M116")
LIB = Path(r"D:\personal\macro")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
LIMIT = 100


def main() -> int:
    picks = {}
    for s in SUBJECTS:
        imap = ROOT / "maps" / f"{s}__A0-index.tif"
        if not imap.exists():
            print(f"{s}: {imap.name} missing")
            continue
        idx = tifffile.imread(imap)
        assert idx.ndim == 2, f"election map is {idx.shape}"
        counts = np.bincount(idx.ravel(), minlength=LIMIT)
        winner = int(np.argmax(counts))
        share = float(counts[winner]) / float(idx.size)

        frames = sorted(LIB.joinpath(s).glob("*.ARW"))[:LIMIT]
        src = frames[winner]
        dst_dir = ROOT / "single" / s
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)

        picks[s] = {
            "frame_index_0based": winner,
            "file": src.name,
            "pixel_share": share,
            "copied_to": str(dst),
        }
        print(f"{s:16s} frame {winner:3d} ({src.name}) wins "
              f"{100.0 * share:6.2f}% of pixels")

    (ROOT / "single-frame-picks.json").write_text(json.dumps(picks, indent=2))
    print(f"wrote {ROOT / 'single-frame-picks.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

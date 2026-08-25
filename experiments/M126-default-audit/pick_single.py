"""M126-default-audit — pick the sharpest single source frame (PREREG section 2, baseline B0).

"Sharpest" is the frame index that wins the most pixels in the A0 election map,
which `--index-map` writes and which the CLI documents as byte inert ("It does
not change the merged image by a byte"). That is a frame CHOICE made by the
pipeline. It is not a metric and it enters no score.

This baseline exists because V-M116 measured that on a drifting stack the single
frame BEATS the merge (tweezers-cpl: single 0.84177 vs merge 0.37376, SYNTHESIS
facts 1701/1702). "Better than the current default" is not the same as "good".

Copies the chosen ARW out of the read-only capture library into
C:\\dev\\strehl-out\\M126\\single\\<subject>\\. D:\\ is never written.

HAZARD (registered): bee-3-cpl has 299 frames and a uint8 index map would wrap
at 256. This asserts the dtype rather than trusting it.

    python experiments\\M126-default-audit\\pick_single.py
"""

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M126")
LIB = Path(r"D:\personal\macro")
SUBJECTS = ["bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl"]
LIMIT = 100
NO_FRAME = 65535  # robust::NO_FRAME, the unresolved sentinel.


def main() -> int:
    picks = {}
    for s in SUBJECTS:
        imap = ROOT / "maps" / f"{s}__A0-index.tif"
        if not imap.exists():
            print(f"{s}: {imap.name} missing")
            continue
        idx = tifffile.imread(imap)
        assert idx.ndim == 2, f"{s}: election map is {idx.shape}"
        # The wrap hazard, checked rather than assumed.
        assert idx.dtype == np.uint16, (
            f"{s}: election map is {idx.dtype}; a uint8 map wraps at 256 and "
            f"this subject may have more frames than that")
        resolved = idx[idx != NO_FRAME]
        assert resolved.max() < LIMIT, (
            f"{s}: election map holds index {resolved.max()} with --limit {LIMIT}")

        counts = np.bincount(resolved.ravel(), minlength=LIMIT)
        winner = int(np.argmax(counts))
        share = float(counts[winner]) / float(resolved.size)

        frames = sorted(LIB.joinpath(s).glob("*.ARW"))[:LIMIT]
        assert len(frames) == LIMIT, f"{s}: only {len(frames)} frames"
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
            "unresolved_px": int((idx == NO_FRAME).sum()),
            "copied_to": str(dst),
        }
        print(f"{s:16s} frame {winner:3d} ({src.name}) wins "
              f"{100.0 * share:6.2f}% of resolved pixels "
              f"({picks[s]['unresolved_px']} unresolved)")

    (ROOT / "single-frame-picks.json").write_text(json.dumps(picks, indent=2))
    print(f"wrote {ROOT / 'single-frame-picks.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

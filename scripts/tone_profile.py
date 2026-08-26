"""Where the tone rendering actually puts each subject.

A curve validated on mid-key subjects keeps shipping the extremes. This reports
the whole library sorted by median luma, so both tails are obvious at a glance:

  * crushed   -- a large fraction of the frame pinned near black. Detail that is
                 below the black point is not dark, it is GONE, and no amount of
                 lifting in print brings it back.
  * washed    -- everything compressed into a narrow band just below white. Not
                 clipped, so a clipping check reports it as fine, and it still
                 reads flat and chalky because there is no tonal separation left.

Both are failures of the same mechanism -- black/white placement -- in opposite
directions, which is why they have to be watched together rather than one at a
time.

Measured in DISPLAY space on the deliverable JPEG, deliberately. Every metric
this project recorded for months was taken on 16-bit linear crops, and that is
precisely why an entirely absent tone rendering went unnoticed through 1786
facts. This file is the counterweight: it asks what the picture looks like, not
what the data contains. It is never a substitute for linear measurement of the
merge -- it is the question linear measurement structurally cannot ask.

usage: python tone_profile.py <dir-of-jpegs> [--json out.json]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Below this, an 8-bit display value is 5/255 or less: not "dark", but without
# recoverable separation. ORCH's threshold, kept as-is so the numbers compare.
CRUSHED = 0.02
# A high median is legitimate on a white-sweep subject. What is not legitimate
# is a high median with nothing above it: the backdrop and the highlights
# occupying the same few percent.
WASHED_MEDIAN = 0.85
WASHED_SPAN = 0.10


def profile(path: Path) -> dict:
    # 8-bit JPEG here, so PIL is safe. The 16-bit-TIFF prohibition is about
    # PIL silently dropping RGB16 to 8 bits; this file is 8-bit by definition.
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    a = np.asarray(im, dtype=np.float32) / 255.0
    assert a.ndim == 3 and a.shape[2] == 3, f"{path.name}: not RGB"
    # Rec.709 luma on the DISPLAY-ENCODED values. Not linearised: the question
    # is where the tones sit for a viewer, not what the scene radiance was.
    luma = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    f = luma.ravel()
    p = np.percentile(f, [0.1, 1, 25, 50, 75, 99, 99.9])
    crushed = float((f < CRUSHED).mean() * 100.0)
    # Span of the top half of the image. This is what separates "bright subject"
    # from "washed out": a clean white sweep still has structure above its
    # median, a washed one does not.
    upper = float(p[6] - p[3])
    flags = []
    if crushed >= 5.0:
        flags.append(f"CRUSHED {crushed:.1f}%")
    if p[3] >= WASHED_MEDIAN and upper <= WASHED_SPAN:
        flags.append(f"WASHED span {upper:.3f}")
    return {
        "subject": path.stem,
        "p0_1": float(p[0]), "p1": float(p[1]), "p25": float(p[2]),
        "median": float(p[3]), "p75": float(p[4]),
        "p99": float(p[5]), "p99_9": float(p[6]),
        "upper_span": upper,
        "crushed_pct": crushed,
        "flags": flags,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    d = Path(sys.argv[1])
    jpegs = sorted(d.glob("*.jpg"))
    if not jpegs:
        print(f"no JPEGs in {d}")
        return 2
    rows = [profile(p) for p in jpegs]
    rows.sort(key=lambda r: r["median"])

    print(f"{'subject':38} {'med':>6} {'p1':>6} {'p99':>6} {'p99.9':>6} "
          f"{'span':>6} {'<0.02':>7}  flags")
    print("-" * 100)
    for r in rows:
        print(f"{r['subject'][:38]:38} {r['median']:6.3f} {r['p1']:6.3f} "
              f"{r['p99']:6.3f} {r['p99_9']:6.3f} {r['upper_span']:6.3f} "
              f"{r['crushed_pct']:6.2f}%  {' '.join(r['flags'])}")

    bad = [r for r in rows if r["flags"]]
    print()
    print(f"{len(rows)} subjects, {len(bad)} flagged")
    for r in bad:
        print(f"  {r['subject']}: {', '.join(r['flags'])}")

    if "--json" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--json") + 1])
        out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    # Deliberately exit 0 even when flagged. This reports; it does not gate.
    # A tonal extreme can be the right answer for a subject, and a harness that
    # fails the build on a legitimate white sweep gets switched off.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

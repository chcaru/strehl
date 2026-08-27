"""Record the reference arm's frame hashes, so the pre-registered hazard is testable.

THE HAZARD, from pin_instrument.py. The reference frames are developed by the
SAME binary as the master -- that is what makes the demosaic common-mode and lets
it cancel out of the ratio. If the merge fix also changes single-frame develops,
the CEILING moves too, and a change in the ratio is no longer attributable to the
master alone. A convex-combination merge over one frame should be an identity,
but "should" is not a measurement and this project does not accept "should".

Rather than retain ~50 GB of TIFFs to compare against later, hash them now. The
after-run re-develops its frames with the new binary, runs this again, and diffs.
Identical hashes => the ceiling is fixed and the ratio delta is the merge.
Different hashes => the reading must be DECOMPOSED before it is interpreted, and
the decomposition stated rather than averaged over.

PARTITION IS STATED, because a baseline that silently covers two subjects and is
read as covering five is exactly the failure this lane has been documenting. Only
subjects whose renders are still cached can be hashed; the rest are recorded as
not-covered, not as passed.

Usage:
  python frame_hashes.py <out.tsv>
"""

import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from corpus_softness import SCRATCH  # noqa: E402

# The five subjects with an exact (n == N) ceiling in the before-reading.
PINNED = ["coffee-bubbles", "109MSDCF", "119MSDCF", "flower-bud-alone-cpl",
          "bee-1-cpl"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    out = pathlib.Path(sys.argv[1])
    rows = ["subject\tfile\tsha256"]
    covered, absent = [], []
    for s in PINNED:
        d = SCRATCH / s
        frames = sorted(d.glob("frame-*.tiff")) if d.exists() else []
        if not frames:
            absent.append(s)
            rows.append(f"{s}\tNOT-COVERED\tno cached renders")
            continue
        covered.append((s, len(frames)))
        for f in frames:
            rows.append(f"{s}\t{f.name}\t{sha(f)}")
        m = d / "MASTER.tiff"
        if m.exists():
            rows.append(f"{s}\tMASTER.tiff\t{sha(m)}")
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")

    print(f"wrote {out}")
    print("\n  COVERED (frame hashes recorded, hazard testable):")
    for s, n in covered:
        print(f"    {s:<24}{n} frames")
    print("\n  NOT COVERED (renders already freed; hazard NOT testable here):")
    for s in absent:
        print(f"    {s}")
    print(f"\n  partition: {len(covered)} covered + {len(absent)} not-covered "
          f"= {len(PINNED)} of {len(PINNED)} pinned subjects")
    print("\n  A not-covered subject is NOT a subject that passed. If the "
          "after-run needs the hazard checked on those, they must be "
          "re-developed with the OLD binary first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

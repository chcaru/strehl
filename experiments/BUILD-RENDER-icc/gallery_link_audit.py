"""Audit which master a viewer actually receives from the gallery's download link.

The gallery (experiments/ORCH-drift-check/build_gallery.py, ORCH's file) hardcodes
SHIP-V1 as its master root at line 27 and links <SHIP-V1>/<stem>.tiff at line 514.
SHIP-V1 predates the ICC embedding, so the question is whether a viewer clicking
"open the 16-bit master" receives a colour-managed file or an unprofiled one.

This measures it rather than asserting it, and partitions every subject into a
counted outcome so a skipped file cannot read as a passed one.

Never PIL for 16-bit RGB: it silently downconverts to 8 bits. tifffile only.
"""

from __future__ import annotations

import pathlib
import sys

import tifffile

LINKED = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")  # what the gallery hands out
CURRENT = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2-ICC")  # what now exists

ICC_TAG = 34675


def icc_len(path: pathlib.Path) -> int | None:
    """Bytes of embedded ICC profile, or None if the tag is absent."""
    with tifffile.TiffFile(str(path)) as tf:
        tag = tf.pages[0].tags.get(ICC_TAG)
        if tag is None:
            return None
        return len(bytes(tag.value))


def main() -> int:
    if not LINKED.is_dir():
        print(f"linked master root missing: {LINKED}")
        return 2

    linked_profiled = 0
    linked_bare = 0
    no_current = 0
    current_profiled = 0

    stems = sorted(p.stem for p in LINKED.glob("*.tiff"))
    if not stems:
        print(f"no masters under {LINKED}")
        return 2

    for stem in stems:
        if icc_len(LINKED / f"{stem}.tiff") is None:
            linked_bare += 1
        else:
            linked_profiled += 1

        cur = list(CURRENT.glob(f"{stem}*.tiff"))
        if not cur:
            no_current += 1
        else:
            m = icc_len(cur[0])
            if m is not None:
                current_profiled += 1

    total = len(stems)
    print(f"gallery master root (linked): {LINKED}")
    print(f"subjects linked: {total}")
    print(f"  linked file carries ICC   {linked_profiled}")
    print(f"  linked file has NO ICC    {linked_bare}")
    print(f"  (sums to {linked_profiled + linked_bare} of {total})")
    print()
    print(f"same subject under {CURRENT.name}:")
    print(f"  profiled master exists    {current_profiled}")
    print(f"  no counterpart found      {no_current}")
    print(f"  (sums to {current_profiled + no_current} of {total})")
    print()

    if linked_bare and current_profiled:
        print(
            f"GAP: {linked_bare}/{total} masters the gallery hands out carry no ICC "
            f"profile, while {current_profiled}/{total} profiled counterparts exist. "
            "The gallery's master root is in ORCH's file; routing required."
        )
    elif linked_bare:
        print(f"GAP: {linked_bare}/{total} linked masters unprofiled, no profiled counterpart.")
    else:
        print("OK: every master the gallery hands out carries an ICC profile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

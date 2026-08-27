#!/usr/bin/env python3
"""
V-EYES: run the FROZEN instrument on both STREHL_RESTORE arms.

WHY THIS FILE EXISTS RATHER THAN AN EDIT TO corpus_softness.py
--------------------------------------------------------------
The instrument is byte-frozen (PIN-MANIFEST.tsv, verified by pin_instrument.py)
precisely so that a before/after can be attributed to the change under test and
to nothing else. Editing it to add an A/B mode would destroy the pin and with
it the comparison. So this driver imports the pinned module and rebinds one
module-level constant, `SCRATCH`. The pinned FILE is untouched and still
verifies; only where it looks for its cache changes.

HOW THE TWO ARMS ARE MADE IDENTICAL EXCEPT FOR THE ONE THING
------------------------------------------------------------
`measure()` caches by existence: if SCRATCH/<subject>/MASTER.tiff and the
frame-*.tiff renders are already there, it uses them. So:

  arm A   SCRATCH_A/<subject>/MASTER.tiff  <- the UNRESTORED master
          frames rendered fresh by the pinned binary
  arm B   SCRATCH_B/<subject>/MASTER.tiff  <- the RESTORED master
          frames HARDLINKED from arm A

Hardlinks, not copies. The two arms' reference frames are then the same inode,
so "byte-identical reference" is not a claim I have to verify, it is a property
of the filesystem. That matters here because coffee-bubbles' original renders
were freed and are NOT in PIN/frame-hashes.tsv, so I cannot prove identity with
the historical run by hash. Making the A/B internally exact removes the need
to: the difference between the arms cannot come from the reference, because
there is only one reference.

WHY THE REFERENCE IS NOT ALSO RESTORED
--------------------------------------
A single-frame develop goes through the same merge path, so setting the switch
on both arms would sharpen the yardstick too and the effect would partly
cancel. The reference is the fixed ceiling the master is being judged against;
restoring it would be changing the ruler and the thing being measured in the
same experiment. Stated as a design decision, not an oversight -- the
both-arms-restored number is a legitimate secondary question and is noted in
the report as unmeasured.

WHAT IS COMMON-MODE AND THEREFORE NOT RE-RUN
--------------------------------------------
The order-statistic null from envelope_null.py depends only on the reference
set and its size. The reference set is one shared set of hardlinks. The null is
therefore identical across the arms by construction and divides out of the A/B;
the raw ratios are directly comparable. The null is still needed to place
either arm on the absolute scale against the frozen 0.9018, and the frozen
value is reused for that with the reasoning stated.

Usage:
    python restore_ab_run.py <subject> [--size N]
"""
import argparse
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import corpus_softness as CS   # noqa: E402  (pinned; imported, never edited)

AB = pathlib.Path(r"C:\dev\strehl-out\V-EYES\restore-ab")
RUN = AB / "run"


def stage(subject, arm, master_src, log_src, link_from=None):
    """Build a SCRATCH tree the pinned measure() will accept as already-cached."""
    root = RUN / arm
    d = root / subject
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "MASTER.tiff").exists():
        shutil.copy2(master_src, d / "MASTER.tiff")
    if not (d / "MASTER.log").exists():
        shutil.copy2(log_src, d / "MASTER.log")
    linked = 0
    if link_from is not None:
        for f in sorted((RUN / link_from / subject).glob("frame-*.tiff")):
            t = d / f.name
            if not t.exists():
                os.link(f, t)      # hardlink: same inode, identity is structural
            linked += 1
    return root, linked


def main():
    p = argparse.ArgumentParser()
    p.add_argument("subject")
    p.add_argument("--size", type=int, default=2048)
    a = p.parse_args()
    s = a.subject

    src = AB / s
    plain, rest = src / "MASTER-plain.tiff", src / "MASTER-restore.tiff"
    for q in (plain, rest):
        if not q.exists():
            print(f"missing {q}; run restore_ab.py {s} first")
            return 1

    # Arm A first: it renders the reference frames that arm B will share.
    rootA, _ = stage(s, "A-plain", plain, src / "MASTER-plain.log")
    print(f"=== ARM A (STREHL_RESTORE unset)   SCRATCH={rootA}", flush=True)
    CS.SCRATCH = rootA
    rowA = CS.measure(s, a.size, None, 10 ** 9, None, True)
    print(f"    {rowA['state']:<9} ratio {rowA['ratio']} "
          f"CI [{rowA['ci_lo']}, {rowA['ci_hi']}]  n={rowA['n_sampled']}/{rowA['n_frames']} "
          f"softer {rowA['softer_pct']}%  {rowA['secs']}s", flush=True)

    nfa = len(list((rootA / s).glob("frame-*.tiff")))
    rootB, linked = stage(s, "B-restore", rest, src / "MASTER-restore.log",
                          link_from="A-plain")
    print(f"\n=== ARM B (STREHL_RESTORE=1.7)     SCRATCH={rootB}")
    print(f"    reference frames hardlinked from arm A: {linked}/{nfa}", flush=True)
    if linked != nfa or linked == 0:
        print("    !! reference sets differ; the A/B is not clean")
        return 2
    CS.SCRATCH = rootB
    rowB = CS.measure(s, a.size, None, 10 ** 9, None, True)
    print(f"    {rowB['state']:<9} ratio {rowB['ratio']} "
          f"CI [{rowB['ci_lo']}, {rowB['ci_hi']}]  n={rowB['n_sampled']}/{rowB['n_frames']} "
          f"softer {rowB['softer_pct']}%  {rowB['secs']}s", flush=True)

    print("\n=== A/B ===")
    if rowA["state"] != "measured" or rowB["state"] != "measured":
        print(f"    not both measured: A={rowA['state']}/{rowA['reason']} "
              f"B={rowB['state']}/{rowB['reason']}")
        return 2
    if (rowA["tile_x"], rowA["tile_y"]) != (rowB["tile_x"], rowB["tile_y"]):
        print(f"    !! tiles differ A=({rowA['tile_x']},{rowA['tile_y']}) "
              f"B=({rowB['tile_x']},{rowB['tile_y']}) -- not comparable")
    print(f"    tile        ({rowA['tile_x']},{rowA['tile_y']}) {a.size}")
    print(f"    ratio       {rowA['ratio']}  ->  {rowB['ratio']}")
    print(f"    move        x{rowB['ratio'] / rowA['ratio']:.4f}")
    print(f"    sites softer {rowA['softer_pct']}%  ->  {rowB['softer_pct']}%")

    out = AB / f"ab-{s}.tsv"
    with out.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(CS.COLS) + "\tarm\n")
        for r, nm in ((rowA, "A-plain"), (rowB, "B-restore")):
            fh.write("\t".join(str(r[c]) for c in CS.COLS) + f"\t{nm}\n")
    print(f"    wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

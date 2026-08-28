"""HEAD (f190a0ea) vs SHIP-V4 (9b05d0b7): the exposure and pixel census.

ORCH's warning, and it is the reason this file exists before any band number is
quoted: `9cb7f5d9` claims to repair `--auto-exposure`, which was proved INERT on
the shipping path this session. If the repair works, the HEAD masters may
legitimately differ from SHIP-V4 in BRIGHTNESS ALONE. A brightness change moves
every noise floor and every structure amplitude together, so an unnormalised
band comparison would report "noisier and sharper everywhere" and that would be
a statement about exposure, not about the fourteen commits.

So the order is: settle exposure first, settle pixel identity second, and only
then let anything measure texture.

Two instructions from ORCH are obeyed literally here:

  - "A file hash is not a pixel gauge. Compare decoded arrays." Identity is
    `np.array_equal` over the decoded arrays. A TIFF carrying a different
    `ImageDescription` is a different file and the same image, and ORCH
    overturned a correct finding tonight by conflating the two.
  - Every subject is counted into exactly one outcome and the outcomes sum to
    the number of subjects found. A count that does not move must not be
    readable as either "nothing was wrong" or "nothing was examined".

Commissioned before it reports (`--commission`): the exposure parser must fail
loudly on an unparseable file rather than return None, and the pixel comparator
must catch a planted 1-count change in one channel of one pixel.

Run: python head_vs_ship.py [--commission]
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import tifffile

BASE_DIR = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
BASE_ARM = "SHIP-V4"
HEAD_DIR = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\arms\HEAD-f190a0ea")
HEAD_ARM = "HEAD-f190a0ea"

EXP_RE = re.compile(r"^exposure\s*:\s*([+-]?[\d.]+)\s*stops\s*\(gain\s*([\d.]+)x\)", re.M)


def exposure_of(tiff_path):
    """Stops and gain the binary CHOSE for this subject, from its provenance.

    Returns a value or raises. It must never return None on a file that exists:
    a parser that yields None for "could not read" and the caller comparing
    None == None would report every subject as agreeing, which is the exact
    shape of a check that certifies by failing.
    """
    p = Path(str(tiff_path) + ".provenance.txt")
    if not p.exists():
        raise FileNotFoundError(f"no provenance beside {tiff_path.name}")
    m = EXP_RE.search(p.read_text(encoding="utf-8", errors="replace"))
    if not m:
        raise ValueError(f"provenance for {tiff_path.name} has no parseable exposure line")
    return float(m.group(1)), float(m.group(2))


def commission():
    """Two arms. Both must pass or nothing below may be believed."""
    ok = []

    # A1: the exposure parser must RAISE on an unparseable provenance, not
    # return a value that compares equal to another failure.
    tmp = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\commission-census")
    tmp.mkdir(parents=True, exist_ok=True)
    fake = tmp / "x.tiff"
    (tmp / "x.tiff.provenance.txt").write_text("no exposure here\n", encoding="utf-8")
    try:
        exposure_of(fake)
        print("  A1 unparseable provenance -> returned a value   FAIL")
        ok.append(False)
    except ValueError:
        print("  A1 unparseable provenance -> raised ValueError  PASS")
        ok.append(True)

    # A2: the pixel comparator must see a planted 1-count change in one channel
    # of one pixel. Without this arm, A1's "26 identical" is unfalsifiable.
    a = np.zeros((64, 64, 3), dtype=np.uint16)
    a[10, 10, 1] = 300
    b = a.copy()
    clean = np.array_equal(a, b)
    b[10, 10, 1] += 1
    caught = not np.array_equal(a, b)
    print(f"  A2 identical copy -> equal {clean};  +1 in one channel -> "
          f"detected {caught}   {'PASS' if (clean and caught) else 'FAIL'}")
    ok.append(clean and caught)
    return all(ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()

    print("=== commissioning the census ===")
    if not commission():
        print("REFUSED: the census is not commissioned; its numbers mean nothing.")
        return 2
    print("  commissioning PASSED\n")
    if a.commission:
        return 0

    subs = sorted(p.name.split("--")[0] for p in BASE_DIR.glob(f"*--{BASE_ARM}.tiff"))
    print(f"=== exposure census: {len(subs)} subject(s) ===")
    same_exp, diff_exp, absent = [], [], []
    for s in subs:
        hb = HEAD_DIR / f"{s}--{HEAD_ARM}.tiff"
        if not hb.exists():
            absent.append(s)
            continue
        be = exposure_of(BASE_DIR / f"{s}--{BASE_ARM}.tiff")
        he = exposure_of(hb)
        (same_exp if be == he else diff_exp).append((s, be, he))
    print(f"  same exposure : {len(same_exp)}")
    print(f"  differing     : {len(diff_exp)}")
    print(f"  not rendered  : {len(absent)}")
    print(f"  partition     : {len(same_exp) + len(diff_exp) + len(absent)} = {len(subs)} found")
    for s, be, he in diff_exp:
        print(f"    {s:32s} SHIP {be[0]:+.2f} st (x{be[1]:.3f})  ->  "
              f"HEAD {he[0]:+.2f} st (x{he[1]:.3f})")

    print(f"\n=== pixel census (decoded arrays, not hashes) ===")
    ident, differ = [], []
    for s in subs:
        hb = HEAD_DIR / f"{s}--{HEAD_ARM}.tiff"
        if not hb.exists():
            continue
        A = tifffile.imread(str(BASE_DIR / f"{s}--{BASE_ARM}.tiff"))
        B = tifffile.imread(str(hb))
        if A.shape != B.shape:
            differ.append((s, None, None, f"shape {A.shape} vs {B.shape}"))
            del A, B
            continue
        if np.array_equal(A, B):
            ident.append(s)
        else:
            d = A.astype(np.int32) - B.astype(np.int32)
            frac = float(np.count_nonzero(d)) / d.size
            mean_ratio = float(B.mean()) / float(A.mean()) if A.mean() else float("nan")
            differ.append((s, frac, mean_ratio, f"max |d| {int(np.abs(d).max())}"))
            del d
        del A, B
    print(f"  pixel-identical : {len(ident)}")
    print(f"  differing       : {len(differ)}")
    print(f"  not rendered    : {len(absent)}")
    print(f"  partition       : {len(ident) + len(differ) + len(absent)} = {len(subs)} found")
    if differ:
        print(f"\n  {'subject':32s} {'%px changed':>12s} {'mean B/A':>10s}  note")
        for s, frac, mr, note in sorted(differ, key=lambda r: -(r[1] or 0)):
            fs = f"{frac * 100:11.4f}%" if frac is not None else "          -"
            ms = f"{mr:10.5f}" if mr is not None else "         -"
            print(f"  {s:32s} {fs} {ms}  {note}")

    # A number printed and not conditioned on is a defect. This is the condition.
    print()
    if absent:
        print(f"INCONCLUSIVE -- {len(absent)} subject(s) not rendered; the census is partial.")
        return 1
    if diff_exp:
        print(f"EXPOSURE MOVED on {len(diff_exp)}/{len(subs)} subjects. Band comparisons "
              f"against SHIP-V4 MUST be gain-normalised or they are measuring brightness.")
        return 1
    print(f"EXPOSURE HELD on all {len(subs)} subjects -- the auto-exposure choice is "
          f"unchanged, so a band comparison against SHIP-V4 is not confounded by it.")
    if not differ:
        print("AND every master is pixel-identical: the fourteen commits changed no "
              "rendered pixel on this corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

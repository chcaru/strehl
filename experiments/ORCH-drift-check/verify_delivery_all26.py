"""ORCH: verify EVERY delivered PNG against its 16-bit master, not a sample of five.

The deliverable's README claims each 8-bit PNG is "bit-exact to the 16-bit master
it came from, reduced to 8 bits per channel and nothing else". That claim was
measured on FIVE of twenty-six subjects. Five is a sample; the claim is universal.
This closes the other twenty-one.

Two things this must not do, both learned the hard way in this project:

  1. It must not hash the files. A TIFF and a PNG carry their own descriptions of
     themselves, and a container hash answers a question about the container. We
     compare DECODED PIXELS.

  2. It must not report a clean run it could not have dirtied. Every run
     commissions itself first on a planted one-count error in a single pixel --
     the smallest defect the claim forbids -- and REFUSES to report on the real
     corpus if the plant is not caught.

Exit 0 only if commissioning passed AND every pair verified.
"""

import sys
import pathlib
import numpy as np
import tifffile

MASTERS = pathlib.Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
DELIVERY = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution")


def read_png(p):
    from PIL import Image
    with Image.open(p) as im:
        return np.asarray(im.convert("RGB"))


def read_master(p):
    a = tifffile.imread(str(p))
    if a.ndim == 3 and a.shape[0] in (3, 4) and a.shape[2] not in (3, 4):
        a = np.moveaxis(a, 0, -1)
    return a[..., :3]


def reduce16to8(a16, mode):
    if mode == "shift":
        return (a16 >> 8).astype(np.uint8)
    if mode == "round":
        return np.clip(np.rint(a16.astype(np.float64) / 257.0), 0, 255).astype(np.uint8)
    raise ValueError(mode)


def compare(m16, png, mode):
    """Return (max_abs_err, mean_abs_err, n_differing) for one reduction mode."""
    got = reduce16to8(m16, mode)
    if got.shape != png.shape:
        return None
    d = np.abs(got.astype(np.int16) - png.astype(np.int16))
    return int(d.max()), float(d.mean()), int((d != 0).sum())


def commission():
    """Plant the smallest error the claim forbids and require the check to catch it.

    A one-count difference in ONE channel of ONE pixel out of ~99 million. If the
    comparator cannot see that, every GREEN below is an artefact of a blind
    instrument rather than evidence about the files.
    """
    rng = np.random.default_rng(11)
    m16 = (rng.integers(0, 65536, size=(64, 64, 3))).astype(np.uint16)
    clean = reduce16to8(m16, "round")

    r = compare(m16, clean, "round")
    if r is None or r[0] != 0 or r[2] != 0:
        print(f"  COMMISSION FAIL: identity arm did not read clean -> {r}")
        return False
    print(f"  identity arm      : max 0, differing 0   (as required)")

    dirty = clean.copy()
    # move one channel of one pixel by exactly one count, avoiding wraparound
    y, x, c = 7, 13, 1
    dirty[y, x, c] = dirty[y, x, c] - 1 if dirty[y, x, c] > 0 else 1
    r = compare(m16, dirty, "round")
    if r is None or r[2] != 1 or r[0] != 1:
        print(f"  COMMISSION FAIL: planted 1-count defect NOT caught -> {r}")
        return False
    print(f"  planted 1 count   : max {r[0]}, differing {r[2]}   (caught)")

    # and a shape mismatch must be refused, not silently passed
    if compare(m16, clean[:32], "round") is not None:
        print("  COMMISSION FAIL: shape mismatch was not refused")
        return False
    print(f"  shape mismatch    : refused   (caught)")
    return True


def main():
    print("=" * 74)
    print("COMMISSIONING -- the check must fail before it may pass")
    print("=" * 74)
    if not commission():
        print("\nREFUSING to report on the corpus: the instrument is not proven.")
        return 2
    print("\ncommissioned OK\n")

    pngs = sorted(DELIVERY.glob("*.png"))
    print("=" * 74)
    print(f"CORPUS -- {len(pngs)} delivered files")
    print("=" * 74)

    exact = 0
    failed = []
    unmatched = []
    modes_used = {}

    for p in pngs:
        stem = p.stem
        cands = list(MASTERS.glob(f"{stem}*.tiff"))
        if not cands:
            unmatched.append(stem)
            print(f"  {stem:34s} NO MASTER FOUND")
            continue
        m16 = read_master(cands[0])
        png = read_png(p)

        best = None
        for mode in ("round", "shift"):
            r = compare(m16, png, mode)
            if r is None:
                continue
            if best is None or r[0] < best[1][0]:
                best = (mode, r)

        if best is None:
            failed.append((stem, "shape", png.shape, m16.shape))
            print(f"  {stem:34s} SHAPE MISMATCH  png{png.shape} vs master{m16.shape}")
            continue

        mode, (mx, mean, ndiff) = best
        modes_used[mode] = modes_used.get(mode, 0) + 1
        if mx == 0:
            exact += 1
            print(f"  {stem:34s} EXACT     ({mode}, {png.shape[1]}x{png.shape[0]})")
        else:
            failed.append((stem, mode, mx, ndiff))
            pct = 100.0 * ndiff / png.size
            print(f"  {stem:34s} DIFFERS   max {mx} DN, mean {mean:.4f}, {ndiff} px ({pct:.3f}%)")

    total = len(pngs)
    print()
    print("=" * 74)
    print("VERDICT")
    print("=" * 74)
    print(f"  exact            : {exact}")
    print(f"  differing        : {len(failed)}")
    print(f"  no master found  : {len(unmatched)}")
    print(f"  ---------------- : {exact + len(failed) + len(unmatched)} == {total} total")
    print(f"  reduction modes  : {modes_used}")
    if unmatched:
        print(f"  unmatched        : {', '.join(unmatched)}")

    ok = (exact == total)
    print()
    print("  GREEN -- every delivered file is bit-exact to its master" if ok
          else "  RED -- see rows above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

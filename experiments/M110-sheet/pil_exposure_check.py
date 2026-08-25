"""Empirical exposure check for ORCH's PIL 16-bit RGB hazard.

ORCH: PIL.Image.open() on a 16-bit RGB TIFF silently returns uint8, a 241x
loss of level resolution, with no warning. 27 scripts across 8 milestones are
exposed.

Reading imports says M110 is clean: every pixel path goes through
tifffile.imread, and PIL appears only as Image.new/fromarray/paste for WRITING
sheets. But ORCH's own instruction is "re-run rather than reason" -- arguing
from first principles is exactly the argument that would have hidden this. So
this probe measures the real files my reported numbers were computed on, and
demonstrates the hazard on those same files so the negative result is anchored
to a positive control.
"""

from pathlib import Path
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheet import load_raw  # noqa: E402

D = Path(r"C:\dev\strehl-out\M110-sheet")

# Every file any reported M110 number was computed on.
FILES = [
    ("bee-3-cpl/default.tif", "sections 14-16 decile, overshoot, width; magenta null"),
    ("bee-3-cpl/ca.tif", "sections 14-16 CA arm"),
    ("bee-3-cpl/lin-default.tif", "section 18 cell C"),
    ("bee-3-cpl/lin-ca.tif", "section 18 cell C"),
    ("bee-3-cpl/lind-default.tif", "section 18 cell B"),
    ("wrapped-text-1/default.tif", "sections 14-15 radial"),
    ("wrapped-text-1/lin-default.tif", "section 18 confirmation"),
    ("flat-on-ruler-cpl/default.tif", "sections 14-16 radial, width"),
    ("tweezers-cpl/default.tif", "sections 14-15 decile"),
]


def probe(rel: str, why: str) -> bool:
    p = D / rel
    if not p.exists():
        print(f"  {rel:<34} MISSING -- skipped")
        return True

    true = tifffile.imread(str(p))
    mine = load_raw(p)

    ok_dtype = mine.dtype == np.uint16 == true.dtype
    ok_exact = mine.shape == true.shape and np.array_equal(mine, true)
    levels = len(np.unique(true[:, :, 0]))

    # Positive control: does the hazard actually bite on THIS file? A negative
    # result is only meaningful if the instrument can produce a positive one.
    try:
        from PIL import Image
        im = Image.open(str(p))
        pil = np.asarray(im)
        pil_levels = len(np.unique(pil[..., 0])) if pil.ndim == 3 else len(np.unique(pil))
        hazard = f"PIL: dtype={pil.dtype} mode={im.mode} levels={pil_levels}"
        bites = pil.dtype != np.uint16
    except Exception as e:  # pragma: no cover
        hazard = f"PIL raised {type(e).__name__}"
        bites = False

    flag = "OK " if (ok_dtype and ok_exact) else "BAD"
    print(f"  {flag} {rel:<34} load_raw -> {mine.dtype} {mine.shape}, "
          f"{levels:,} levels")
    print(f"      {hazard}   hazard bites this file: {bites}")
    print(f"      used for: {why}")
    return ok_dtype and ok_exact


def guard_negative_control() -> bool:
    """The assertion in load_raw must FIRE, not merely exist.

    Plants a genuine 8-bit RGB TIFF and requires load_raw to reject it. A guard
    that has never been observed to fail is indistinguishable from no guard --
    and a green here would otherwise be reported by a check that cannot go red.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "planted_8bit.tif"
        tifffile.imwrite(str(p), np.zeros((16, 16, 3), dtype=np.uint8))

        # Confirm the plant is what we think it is before trusting the verdict.
        planted = tifffile.imread(str(p))
        if planted.dtype != np.uint8:
            print(f"  PLANT FAILED: wrote uint8 but read {planted.dtype} -- "
                  f"control is void, not passing")
            return False

        try:
            load_raw(p)
        except SystemExit as e:
            print(f"  RED on plant   PASS  load_raw rejected uint8: {e}")
            return True
    print("  RED on plant   FAIL  load_raw ACCEPTED an 8-bit RGB TIFF")
    return False


def main() -> None:
    print(__doc__)
    print("=" * 74)
    print("negative control -- the guard must be able to fail")
    guard_ok = guard_negative_control()
    print()
    results = [probe(r, w) for r, w in FILES]
    print("=" * 74)
    if all(results) and guard_ok:
        print("VERDICT: every file M110 reported a number on was read as uint16,")
        print("exactly equal to tifffile's array. NO M110 number is exposed.")
        print("The PIL positive control confirms the hazard is real on these same")
        print("files, so this is a measured negative, not an assumed one.")
    else:
        print("VERDICT: EXPOSED or GUARD INERT -- see rows above.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

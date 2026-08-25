"""M95 x21 - quantify ORCH's PIL 16-bit-RGB hazard against M95's OWN headline files.

ORCH 21:28: PIL.Image.open() on a 16-bit RGB TIFF silently returns uint8, and the
most suspect case of all is "anything measuring a small signal ... will read as
zero, as noise, or -- worst -- as a clean null."

M95's headline IS a clean null on small differences: merged output byte-identical
to the elected frame, 180,697 px, 100.0000 % exact, max 0 DN of 65535. That is
exactly the shape the hazard manufactures. M95's readers use tifffile with an
explicit `assert a.dtype == np.uint16` (m95lib.py:54), so the headline should be
unexposed -- but "should be" is not a measurement.

So: do not argue. Measure what PIL would have reported on the same files.

PRE-REGISTERED BARS
  B1  PIL must actually return uint8/mode=RGB on these files. If it returns uint16,
      the hazard does not reach this data and the rest of this script is moot --
      report that, do not spin it.
  B2  tifffile must return uint16 and match the file's own byte count, so the
      reference read is known good rather than assumed.
  B3  THE ONE THAT MATTERS. Compare the merged render against a frame that did NOT
      win these pixels. Under tifffile the exact-match fraction must be small --
      that is the instrument's discriminating power (report R6a: 0.0519 %).
      Under PIL, if the match fraction inflates materially, then PIL manufactures
      spurious identity and M95's use of tifffile was load-bearing rather than
      lucky. Quantify the inflation; do not merely note it.
  B4  Report the quantisation floor in 16-bit units, so the reader can see how
      large a difference PIL would have swallowed.

INTERPRETATION REGISTERED IN ADVANCE
  - If B1 fails: say the hazard does not reach these files and stop.
  - If B3 shows large inflation: M95 is EXPOSED-BUT-UNAFFECTED, and the reason is
    the tifffile reader plus the dtype assert, which is checkable in the source.
  - If B3 shows NO inflation: then PIL would have given the same answer, M95's
    headline is robust to the reader either way, and I must say so plainly rather
    than claim a save I did not earn.
"""

import pathlib
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

OUT = pathlib.Path(r"C:\dev\strehl-out\M93-out")
MERGED = OUT / "armM-gate0-binlin.tif"
ELECTED = OUT / "armF-f183.tif"
FAR = OUT / "armF-f119.tif"

CROP = (900, 1400, 900, 1400)


def pil_read(p):
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(p)
    return np.asarray(im), im.mode


def tif_read(p):
    import tifffile

    return tifffile.imread(str(p))


def green(a):
    assert a.ndim == 3 and a.shape[2] == 3, a.shape
    r0, r1, c0, c1 = CROP
    return a[r0:r1, c0:c1, 1]


def main():
    for p in (MERGED, ELECTED, FAR):
        if not p.exists():
            print(f"MISSING {p}")
            return 2

    print("=" * 74)
    print("M95 x21 - what PIL would have done to M95's headline")
    print("=" * 74)

    print("\n-- B1/B2: what each reader returns --")
    reads = {}
    for name, p in (("merged", MERGED), ("elected f183", ELECTED), ("far f119", FAR)):
        t = tif_read(p)
        a, mode = pil_read(p)
        reads[name] = (t, a)
        nbytes = p.stat().st_size
        expect16 = t.shape[0] * t.shape[1] * t.shape[2] * 2
        print(f"  {name:14s} tifffile {str(t.dtype):8s} {t.shape}  max={t.max()}")
        print(f"  {'':14s} PIL      {str(a.dtype):8s} mode={mode:6s} max={a.max()}")
        print(f"  {'':14s} file {nbytes:,} bytes, 16-bit payload would be {expect16:,}")

    t_m = reads["merged"][0]
    p_m = reads["merged"][1]
    b1 = p_m.dtype == np.uint8
    b2 = t_m.dtype == np.uint16
    print(f"\n  B1 PIL returns uint8 on 16-bit RGB : {'CONFIRMED' if b1 else 'NOT REPRODUCED'}")
    print(f"  B2 tifffile returns uint16         : {'CONFIRMED' if b2 else 'FAILED'}")
    if not b2:
        print("\n  reference read is not trustworthy; making no claim.")
        return 2
    if not b1:
        print("\n  The hazard does not reach these files. Nothing further to report.")
        return 0

    print("\n-- B4: quantisation floor --")
    lv_t = len(np.unique(t_m[:, :, 1]))
    lv_p = len(np.unique(p_m[:, :, 1]))
    print(f"  distinct green levels, whole frame: tifffile {lv_t}  PIL {lv_p}")
    print(f"  ratio {lv_t / max(lv_p, 1):.1f}x")
    print("  one PIL step = 257 DN in 16-bit units (65535/255)")
    print("  => any real difference below ~128 DN can read as EXACTLY ZERO under PIL")

    print("\n-- B3: does PIL manufacture spurious identity? --")
    print(f"  crop rows {CROP[0]}:{CROP[1]} cols {CROP[2]}:{CROP[3]}"
          f"  ({(CROP[1]-CROP[0])*(CROP[3]-CROP[2]):,} px)")
    print("  NOTE: this is a hazard-magnitude control, NOT the headline test.")
    print("  The headline (100.0000 % exact) is computed by s5b_checks.py on each")
    print("  frame's ELECTED pixel set only. This arbitrary crop is mostly pixels")
    print("  neither frame won, so a low match here is expected and is not a")
    print("  counter-example to the headline. What matters is the PIL/tifffile RATIO.")
    for label, key in (("peak frame f183, arbitrary crop (NOT its elected set)", "elected f183"),
                       ("distant frame f119 (genuinely different content)", "far f119")):
        t_o, p_o = reads[key]
        gt_m, gt_o = green(t_m).astype(np.int32), green(t_o).astype(np.int32)
        gp_m, gp_o = green(p_m).astype(np.int32), green(p_o).astype(np.int32)
        ft = float(np.mean(gt_m == gt_o)) * 100.0
        fp = float(np.mean(gp_m == gp_o)) * 100.0
        dt = int(np.abs(gt_m - gt_o).max())
        dp = int(np.abs(gp_m - gp_o).max())
        print(f"\n  {label}")
        print(f"    tifffile(uint16): exact {ft:8.4f} %   max abs diff {dt:6d} DN")
        print(f"    PIL     (uint8) : exact {fp:8.4f} %   max abs diff {dp:6d} (8-bit steps)")
        if ft > 0:
            print(f"    inflation factor PIL/tifffile: {fp / ft:.2f}x")
        else:
            print(f"    inflation: tifffile says 0.0000 %, PIL says {fp:.4f} %")

    print("\n" + "=" * 74)
    print("Read m95lib.py:48-55 for the reader every M95 measurement actually used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

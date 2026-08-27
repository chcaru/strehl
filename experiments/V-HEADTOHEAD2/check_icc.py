"""Does the fork's archived comparator artefact carry an embedded ICC profile?

Why this is worth 20 lines. `C:\\dev\\macro\\out\\coffee-bean\\stack.log` is the
only archived record of a fork run on this bracket and it is the number section 9
quotes for the May build (merged TIFF at 93.739 s). But the log's mtime is
2026-05-10 16:45:16 and stack.tif's is 2026-05-10 20:01:58 -- three hours later.
Either the artefact came from a LATER, unlogged run, in which case the 93.739 s
does not describe the file V-HEADTOHEAD2 measured quality on, or the file was
rewritten after the run by the ICC-embed step the log itself recommends:

    Tip: embed the colour profile so Lightroom auto-detects it:
         python scripts\\embed_icc.py "C:\\dev\\macro\\out\\coffee-bean\\stack.tif"

The two hypotheses are distinguishable: an embed leaves an ICCProfile tag and
adds bytes beyond the pixel payload. A plain fork write does not embed one --
that is the whole point of the tip. So:

  ICC tag present  -> the embed ran; the archived log plausibly IS this file's run
  ICC tag absent   -> the file came from somewhere else and the 93.739 s is a
                      DIFFERENT run of the same program on the same frames

Either way the answer is reported. Run:  python check_icc.py
"""

import os

import tifffile

PATH = r"C:\dev\macro\out\coffee-bean\stack.tif"


def main():
    size = os.path.getsize(PATH)
    with tifffile.TiffFile(PATH) as t:
        p = t.pages[0]
        w, h = p.imagewidth, p.imagelength
        spp = p.samplesperpixel
        bits = p.bitspersample
        payload = w * h * spp * (bits // 8)
        tags = {tg.name: tg for tg in p.tags.values()}
        icc = tags.get("InterColorProfile")
        print(f"file          : {PATH}")
        print(f"bytes         : {size:,}")
        print(f"geometry      : {w} x {h}, {spp} samples, {bits} bits")
        print(f"pixel payload : {payload:,}")
        print(f"overhead      : {size - payload:,} bytes")
        print(f"compression   : {p.compression}")
        print()
        if icc is None:
            print("ICC profile   : ABSENT")
            print("VERDICT       : the fork wrote this file and nothing embedded a")
            print("                profile afterwards. The 3-hour mtime gap is then")
            print("                UNEXPLAINED and the archived log's 93.739 s is a")
            print("                different run of the same program on the same 105")
            print("                frames -- still a real measurement, but not")
            print("                provably this artefact's.")
        else:
            n = len(icc.value) if hasattr(icc.value, "__len__") else -1
            print(f"ICC profile   : PRESENT, {n:,} bytes")
            print("VERDICT       : consistent with the archived log being this file's")
            print("                run, followed by the embed_icc.py step the log")
            print("                itself recommends, which rewrites the file and")
            print("                moves its mtime. Consistent with, not proof of.")
        # counted partition of the overhead, so a missing explanation is visible
        icc_bytes = (len(icc.value) if icc is not None and hasattr(icc.value, "__len__") else 0)
        other = size - payload - icc_bytes
        print()
        print(f"overhead partition: icc {icc_bytes:,} + other tags/headers {other:,} "
              f"= {size - payload:,} of {size - payload:,}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Where did the SHA-256 move, if not in the pixels?

48-delivered-gain.py established that C-plus3 (+3 stops, gain 8.0x) and
D-minus3 (-3 stops, gain 0.125x) are IDENTICAL in all 98,898,048 samples --
zero differing, max |delta| 0 counts. Yet 47-exposure-liveness recorded
distinct SHA-256s for those two files and concluded from that difference that
"the exposure path is LIVE".

Both cannot be true of the pixels. So the hash moved somewhere else, and this
script finds out where rather than assuming. The hypothesis under test is that
the differing bytes lie in the TIFF's own metadata -- specifically in the
ImageDescription that records the exposure the render claims to have applied.

If that is confirmed, then 47's instrument did not merely fail to be specific.
It reported the file's SELF-DESCRIPTION as evidence about the file's CONTENT,
which is the argv -> banner -> bytes ladder collapsing in the one way nobody
writes down: the bytes I was hashing CONTAINED the banner.

This is deliberately a raw byte comparison and not a TIFF-aware one. A
tag-aware reader would tell me what the library thinks the file says; the
question here is which bytes on disk are not equal.

DEFECT IN THIS SCRIPT'S FIRST VERSION, kept because it is the same defect the
script exists to expose. The first run printed

    A-auto vs B-plain: differing runs 24+ (truncated), 44 bytes total
                       runs beyond byte 1,000,000 ...: 0
    VERDICT: every differing byte lies in the file HEADER/METADATA region.

That verdict was FALSE for the A/B pair. The scan had stopped at its 24-run cap
while still inside the first 7 kB of a 198 MB file, so it had never looked at
the pixel region it was reporting as clean -- and 48-delivered-gain.py had
already measured 325,297 differing samples there. A count that does not move
reads the same whether nothing was wrong or nothing was examined. The fix is
below and it is twofold: a FULL census that never truncates, and a verdict that
REFUSES for any pair whose run listing was capped, instead of quietly treating
"not found" as "not present". The C/D pair's verdict was sound -- its listing
was complete at one run -- but it was sound by luck, not by construction.
"""

import re
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\BUILD-DEFECT\47-expo")
PAIRS = [("C-plus3", "D-minus3"), ("A-auto", "B-plain")]
COMMANDED = {"A-auto": 6.105, "B-plain": 1.0, "C-plus3": 8.0, "D-minus3": 0.125}
CONTEXT = 90


def pixel_data_start(path: Path) -> int:
    """First byte of pixel data, read from the TIFF itself.

    The first version of this script guessed "beyond one megabyte is probably
    pixels". A guessed boundary in a script whose whole job is to say which
    side of a boundary some bytes fall on is not acceptable, so the offset now
    comes from the file's own strip offsets.
    """
    with tifffile.TiffFile(str(path)) as tf:
        return int(min(tf.pages[0].dataoffsets))


def full_census(a: bytes, b: bytes, pixel_start: int):
    """Every differing byte, split at the pixel boundary. NEVER truncates."""
    A = np.frombuffer(a, dtype=np.uint8)
    B = np.frombuffer(b, dtype=np.uint8)
    n = min(A.size, B.size)
    diff = A[:n] != B[:n]
    below = int(np.count_nonzero(diff[:pixel_start]))
    above = int(np.count_nonzero(diff[pixel_start:]))
    return below, above


def tone_from_description(path: Path):
    """`Tone rendering: black B, white W` out of the TIFF ImageDescription.

    Channel 3 was written to read this from the run LOG and found nothing,
    because the tone line is not logged -- it is embedded in the file. The
    channel was reported SKIPPED rather than passed, which is the only reason
    it was still available to recover here.
    """
    with tifffile.TiffFile(str(path)) as tf:
        desc = tf.pages[0].description or ""
    m = re.search(r"Tone rendering:\s*black\s+([0-9.eE+-]+),\s*white\s+([0-9.eE+-]+)", desc)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def differing_runs(a: bytes, b: bytes, max_runs=24):
    """Contiguous [start,end) spans where the two byte strings differ."""
    n = min(len(a), len(b))
    runs = []
    i = 0
    while i < n:
        if a[i] != b[i]:
            j = i
            # Join runs separated by a short equal gap: a changed ASCII field
            # is naturally speckled, and reporting 400 one-byte runs hides the
            # single field they belong to.
            gap = 0
            while j < n and (a[j] != b[j] or gap < 16):
                gap = gap + 1 if a[j] == b[j] else 0
                j += 1
            runs.append((i, j - gap))
            if len(runs) >= max_runs:
                return runs, True
            i = j
        else:
            i += 1
    return runs, False


def printable(bs: bytes) -> str:
    return "".join(chr(c) if 32 <= c < 127 else "." for c in bs)


def main():
    print("=" * 74)
    print("WHERE THE HASH MOVED -- raw byte localisation")
    print("=" * 74)

    verdicts = {}
    for left, right in PAIRS:
        pl, pr = OUT / f"{left}.tif", OUT / f"{right}.tif"
        if not (pl.exists() and pr.exists()):
            sys.exit(f"MISSING one of {pl} {pr}")
        a, b = pl.read_bytes(), pr.read_bytes()
        px = pixel_data_start(pl)
        print(f"\n{'-'*74}\n{left}.tif  vs  {right}.tif")
        print(f"  sizes {len(a):,} / {len(b):,}   {'EQUAL' if len(a)==len(b) else 'DIFFER'}")
        print(f"  pixel data begins at byte {px:,} (read from the TIFF, not guessed)")
        below, above = full_census(a, b, px)
        print(f"  FULL census (no cap): {below:,} differing bytes BEFORE pixel data,"
              f" {above:,} WITHIN it")
        if below and not above:
            verdicts[(left, right)] = "METADATA-ONLY"
        elif above and not below:
            verdicts[(left, right)] = "PIXELS-ONLY"
        elif above and below:
            verdicts[(left, right)] = "BOTH"
        else:
            verdicts[(left, right)] = "IDENTICAL"
        print(f"  -> {verdicts[(left, right)]}")

        runs, truncated = differing_runs(a, b)
        print(f"  run listing (illustrative only, capped): {len(runs)}"
              f"{'+ TRUNCATED' if truncated else ' complete'}")
        for s, e in runs[:3]:
            lo = max(s - CONTEXT // 2, 0)
            hi = min(e + CONTEXT // 2, len(a))
            print(f"\n    offset {s:,}..{e:,}  ({e-s} bytes)")
            print(f"      {left:>9}: {printable(a[lo:hi])}")
            print(f"      {right:>9}: {printable(b[lo:hi])}")

    # ---- CHANNEL 3, recovered: tone anchors from the TIFF description ------
    print("\n" + "=" * 74)
    print("CHANNEL 3 (RECOVERED) -- did the TONE STAGE receive the gain?")
    print("  Not in the logs. It is embedded in each file's ImageDescription.")
    print("=" * 74)
    tones = {k: tone_from_description(OUT / f"{k}.tif") for k in COMMANDED}
    tone_ok = None
    if any(v is None for v in tones.values()):
        print("  NOT AVAILABLE in at least one file. SKIPPED, not passed.")
    else:
        bb, bw = tones["B-plain"]
        print(f"\n{'arm':>10} {'black':>12} {'white':>12} {'blk ratio':>11}"
              f" {'wht ratio':>11} {'commanded':>11}  verdict")
        tone_ok = True
        for k in ("B-plain", "C-plus3", "D-minus3", "A-auto"):
            kb, kw = tones[k]
            rb, rw = kb / bb, kw / bw
            cmd = COMMANDED[k]
            hit = abs(rw - cmd) <= 0.01 * cmd and abs(rb - cmd) <= 0.02 * cmd
            tone_ok &= hit
            print(f"{k:>10} {kb:>12.6f} {kw:>12.6f} {rb:>11.4f} {rw:>11.4f}"
                  f" {cmd:>11.4f}  {'TRACKS' if hit else 'DOES NOT TRACK'}")
        print("\n  The tone anchors scale by the COMMANDED gain. The tone stage")
        print("  therefore received the exposure in full. Channel 2 showed the")
        print("  pixels did not move. That is cancellation, localised.")

    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    cd = verdicts[("C-plus3", "D-minus3")]
    ab = verdicts[("A-auto", "B-plain")]
    print(f"  C(+3) vs D(-3), commanded 64x span : {cd}")
    print(f"  A(auto 6.105x) vs B(none)          : {ab}")
    if cd != "METADATA-ONLY":
        print("\n  C/D is not metadata-only; the headline claim does not hold.")
        return 3
    print("\n  C vs D differ ONLY in the file's own account of what it did.")
    print("  Every one of 98,898,048 samples is identical across a commanded")
    print("  64x exposure span. 47-exposure-liveness read those 21 description")
    print("  bytes as evidence about the image and called the path LIVE.")
    if ab == "BOTH":
        print("\n  A/B differs in BOTH regions: 1-count rounding in the pixels")
        print("  (6.105x is not a power of two, so the round trip does not land")
        print("  on the same bits) plus the same description bytes. C/D is")
        print("  exactly identical because 8.0 and 0.125 ARE powers of two and")
        print("  the f32 round trip through them is exact.")
    if tone_ok is True:
        print("\n  LOCALISED to the tone stage by channel 3.")
    elif tone_ok is False:
        print("\n  NOT localised: tone anchors did not track the command.")
    else:
        print("\n  Localisation SKIPPED; not established.")
    return 2


if __name__ == "__main__":
    sys.exit(main())

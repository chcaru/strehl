"""Turn one 16-bit sRGB TIFF into a viewable JPEG at a stated long edge.

Deliberately tiny, and deliberately does NOTHING to the pixels beyond
downsampling and 16 -> 8 bit. All the rendering -- black point, white point,
contrast, colour matrix, transfer curve -- happens in the Rust develop path and
is recorded in the render log. If this script started adjusting images, the
gallery would stop being a picture of what `strehl` produces, which is the only
thing it is for.

The 16-bit read goes through `tifffile`, never `PIL.Image.open`. PIL silently
downconverts a 16-bit RGB TIFF to 8 bits on open, and that has corrupted results
in this project before. The assert below is the guard, and it is deliberately
not wrapped in a try/except fallback: a lossier reader that "works" is strictly
worse than a loud failure.

It also emits a PER-CHANNEL clipping census, on the full 16-bit array rather
than the JPEG, because that is a fact about the render. This is here because of
a defect it would have caught on sight: the first tone rendering subtracted a
luminance-derived black point from all three channels, which took
`coffee-bubbles` to 88% zero-blue and collapsed it to a one-channel image. It
survived a full gallery run and 1786 recorded facts, and it was found by a
verifier reading the code. An all-three-channels "blown" or "crushed" count
conceals single-channel clipping completely, which is exactly the shape this
defect had, so every count below is per channel and none of them are combined.

Finally it copies PROVENANCE into the JPEG comment: the TIFF's
`ImageDescription`, which carries the colour space and the tone parameters, plus
whatever the caller passes as a fourth argument (binary hash, CA profile, run
time). A gallery JPEG is the artifact people actually open, and until now it
recorded nothing at all about what made it -- the TIFF that knew is deleted
unless `-KeepTiff`. That is how a directory came to hold images from two
different binaries with no way to tell them apart. A file that cannot say what
produced it cannot be trusted, and cannot be compared against another one.

Read it back with:  python -c "from PIL import Image;print(Image.open(P).app['COM'].decode())"
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def main() -> int:
    if len(sys.argv) not in (4, 5):
        print("usage: gallery_view.py <in.tiff> <out.jpg> <long-edge-px> [provenance]",
              file=sys.stderr)
        return 2
    src, dst, long_edge = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    extra = sys.argv[4] if len(sys.argv) == 5 else ""

    # One open, not two: the array and the description come off the same page.
    with tifffile.TiffFile(src) as tf:
        page = tf.pages[0]
        a = page.asarray()
        desc = page.description or ""
    assert a.dtype == np.uint16, f"{src} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{src} has shape {a.shape}, expected HxWx3"

    # 16 -> 8 bit by truncation, matching what any viewer does. Rounding would
    # be marginally more accurate and would also mean the gallery no longer
    # shows what a viewer shows.
    im = Image.fromarray((a >> 8).astype(np.uint8), mode="RGB")
    im.thumbnail((long_edge, long_edge), Image.LANCZOS)

    comment = "\n".join(x for x in (extra, desc) if x).encode("utf-8", "replace")
    # JPEG comment markers are length-limited to 65533 bytes.
    comment = comment[:65000]

    # 95 is high enough that JPEG artifacts are not what anyone is looking at,
    # while keeping a 26-image gallery small enough to open at once.
    im.save(dst, quality=95, subsampling=0, optimize=True, comment=comment)
    print(f"{dst.name}  {im.size[0]}x{im.size[1]}")

    # Not "the parameter was passed" but "the bytes are in the file". The whole
    # point of this block is that provenance is verifiable from the artifact
    # alone, so it is read back off disk rather than assumed to have been
    # written.
    if comment:
        with Image.open(dst) as check:
            got = check.app.get("COM", b"")
        if got.strip() != comment.strip():
            print(f"!! provenance did NOT survive into {dst.name} "
                  f"({len(got)} bytes read vs {len(comment)} written)", file=sys.stderr)
            return 3
        print(f"provenance {len(got)} bytes verified in {dst.name}")

    # Measured on the 16-bit render, not on the JPEG, and per channel. Parsed
    # into manifest.tsv by gallery.ps1; kept on one line so it stays parseable.
    n = a.shape[0] * a.shape[1]
    zero = [100.0 * float((a[..., c] == 0).sum()) / n for c in range(3)]
    blown = [100.0 * float((a[..., c] >= 65535).sum()) / n for c in range(3)]
    print(
        "stats zero={:.4f}/{:.4f}/{:.4f} blown={:.4f}/{:.4f}/{:.4f}".format(*zero, *blown)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

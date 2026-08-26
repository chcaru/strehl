"""Potency control: is the embedded profile actually HONOURED, or is it decoration?

A profile that no reader obeys is a sticker. The only way to know is to embed a
deliberately WRONG one and show that a colour-managed reader visibly changes its
output. If the wrong profile changes nothing, the correct profile is changing
nothing either, and the whole exercise is theatre.

Three arms, all on the SAME pixels, written as real files and read back:

  correct   my sRGB profile on sRGB-encoded pixels   -- must be ~identity to display
  wrong-1   my LINEAR profile on the same pixels     -- the classic "tagged linear
            by mistake" error; must shift hugely
  wrong-2   sRGB profile with red and blue colorants swapped -- must shift hugely

The correct arm doubles as the null: it must NOT move. An arm that moves for
every profile would prove nothing.

The transform is done by LittleCMS through Pillow's ImageCms -- an independent
implementation I did not write -- to a stock sRGB destination profile.

Bit depth note: the 16-bit crop is read with tifffile and asserted uint16. The
LittleCMS leg runs at 8 bits because that is what a display path is, and because
the question here is whether the transform RESPONDS to the profile, not what the
image quality is. No quality claim is made from these numbers.
"""

from __future__ import annotations

import io
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageCms

SRC = Path(r"C:\dev\strehl-out\ICC-AB\out\b-srgb.tiff")
OUT = Path(r"C:\dev\strehl-out\ICC-AB\potency")
ICC_TAG = 34675
CROP = 512


def profile_of(path: Path) -> bytes:
    with tifffile.TiffFile(path) as tf:
        return bytes(tf.pages[0].tags[ICC_TAG].value)


def swap_rb_colorants(p: bytes) -> bytes:
    """Swap the rXYZ and bXYZ tag payloads. Structurally valid, colorimetrically a lie."""
    b = bytearray(p)
    n = struct.unpack(">I", b[128:132])[0]
    where = {}
    for i in range(n):
        e = 132 + 12 * i
        sig = bytes(b[e:e + 4]).decode()
        off, ln = struct.unpack(">II", b[e + 4:e + 12])
        where[sig] = (off, ln)
    (ro, rl), (bo, bl) = where["rXYZ"], where["bXYZ"]
    assert rl == bl == 20, f"unexpected XYZType length {rl}/{bl}"
    r, bl_ = bytes(b[ro:ro + rl]), bytes(b[bo:bo + bl])
    b[ro:ro + rl] = bl_
    b[bo:bo + bl] = r
    return bytes(b)


def retag_desc(p: bytes, text: str) -> bytes:
    """Rewrite the 'desc' ASCII payload in place, so each arm is self-identifying."""
    b = bytearray(p)
    n = struct.unpack(">I", b[128:132])[0]
    for i in range(n):
        e = 132 + 12 * i
        if bytes(b[e:e + 4]) == b"desc":
            off, ln = struct.unpack(">II", b[e + 4:e + 12])
            cur = struct.unpack(">I", b[off + 8:off + 12])[0]
            raw = text.encode("ascii")[: cur - 1]
            payload = raw + b"\0" * (cur - len(raw))
            b[off + 12:off + 12 + cur] = payload
            return bytes(b)
    raise AssertionError("no desc tag")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    a = tifffile.imread(SRC)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    h, w, _ = a.shape
    y, x = h // 2 - CROP // 2, w // 2 - CROP // 2
    crop = np.ascontiguousarray(a[y:y + CROP, x:x + CROP])
    print(f"crop from {SRC.name} at ({x},{y}) {crop.shape} {crop.dtype}, "
          f"mean {crop.mean():.0f} DN")

    good = profile_of(SRC)
    with tifffile.TiffFile(Path(str(SRC).replace("b-srgb", "b-linear"))) as tf:
        linear = bytes(tf.pages[0].tags[ICC_TAG].value)

    arms = {
        "correct": retag_desc(good, "POTENCY correct sRGB"),
        "wrong-linear": retag_desc(linear, "POTENCY wrong: linear TRC"),
        "wrong-rb-swap": retag_desc(swap_rb_colorants(good), "POTENCY wrong: R/B swapped"),
    }

    paths = {}
    for name, prof in arms.items():
        p = OUT / f"{name}.tiff"
        tifffile.imwrite(p, crop, photometric="rgb", iccprofile=prof)
        paths[name] = p
        back = profile_of(p)
        assert back == prof, f"{name}: profile did not survive the write"
    print(f"\nwrote {len(paths)} crops, each with a different embedded profile, "
          f"profiles verified by read-back")

    # Independent confirmation that the three files really are different to a
    # colour-managed tool, before we transform anything.
    print("\n--- exiftool sees three different profiles ---")
    for name, p in paths.items():
        r = subprocess.run(["exiftool", "-s", "-ProfileDescription", "-RedMatrixColumn", str(p)],
                           capture_output=True, text=True)
        print(f"  {name:14} " + " | ".join(ln.split(": ", 1)[1].strip()
                                           for ln in r.stdout.strip().splitlines()))

    # The display leg. Destination is a stock sRGB profile from LittleCMS,
    # i.e. not one of mine.
    dst = ImageCms.createProfile("sRGB")
    disp8 = (crop >> 8).astype(np.uint8)
    base = Image.fromarray(disp8, "RGB")

    print("\n--- LittleCMS transform to a stock sRGB display profile ---")
    results = {}
    for name, p in paths.items():
        src = ImageCms.ImageCmsProfile(io.BytesIO(profile_of(p)))
        tf_ = ImageCms.buildTransform(src, dst, "RGB", "RGB",
                                      renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC)
        got = np.asarray(ImageCms.applyTransform(base, tf_))
        d = np.abs(got.astype(np.int16) - disp8.astype(np.int16))
        results[name] = (got, float(d.mean()), int(d.max()),
                         float((d > 2).mean() * 100))
        Image.fromarray(got, "RGB").save(OUT / f"{name}-through-cms.png")
        print(f"  {name:14} mean |delta| {d.mean():6.2f} DN   max {d.max():3d}   "
              f"pixels moved >2 DN: {(d > 2).mean() * 100:5.1f}%")

    Image.fromarray(disp8, "RGB").save(OUT / "untransformed.png")

    # Side-by-side so the result is a picture, not only a number.
    panel = Image.new("RGB", (CROP * 3 + 24, CROP), "black")
    for i, name in enumerate(["correct", "wrong-linear", "wrong-rb-swap"]):
        panel.paste(Image.fromarray(results[name][0], "RGB"), (i * (CROP + 12), 0))
    panel.save(OUT / "POTENCY-panel.png")

    print("\n--- verdict ---")
    ok = True
    cm, cmax = results["correct"][1], results["correct"][2]
    if cmax > 2:
        print(f"  NULL FAILED: the correct profile moved the image by up to {cmax} DN")
        ok = False
    else:
        print(f"  NULL HELD: correct profile -> display is the identity "
              f"(max {cmax} DN, mean {cm:.3f})")
    for name in ["wrong-linear", "wrong-rb-swap"]:
        _, mean, mx, pct = results[name]
        potent = mx > 20 and pct > 10
        print(f"  {'POTENT' if potent else 'INERT '}: {name} moved the image "
              f"mean {mean:.1f} DN, max {mx} DN, {pct:.1f}% of pixels")
        if not potent:
            ok = False

    print(f"\n  panel: {OUT / 'POTENCY-panel.png'}")
    print("  " + ("PROFILE IS HONOURED" if ok else "PROFILE IS DECORATION -- INVESTIGATE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""ORCH: look at the whole frame, the way the owner does.

Every quality judgement this lane made tonight came from a 1:1 crop chosen by
a statistic. That is the right way to adjudicate sharpening-vs-detail and the
wrong way to notice that a picture is ugly. A defect whose scale is larger
than the crop -- uneven illumination, a tonal gradient, large-scale mottling,
a colour cast that only reads against the rest of the frame -- is invisible to
every instrument in this directory, because every instrument in this directory
looks at a few hundred pixels at a time.

So: no site selection, no stretch, no cleverness. Integer box-average
downsample of the entire master, the master's own encoding taken at face
value, and the resulting picture put in front of a human.

Two rules this tool obeys, both learned the hard way in this project:

  * tifffile, never PIL. Pillow 12.2.0 silently right-shifts 16-bit TIFF to
    8-bit with no exception, and no arithmetic repairs it.
  * A box average of an integer image is a DERIVED array, so
    len(np.unique(...)) cannot audit its provenance -- averaging manufactures
    distinct values out of nothing. The reader is audited at the call site
    instead, by construction.

The downsample is a plain box mean over a k x k block with the remainder
cropped, not resampled. Nothing here is measured; this is a viewing surface,
and its only claim is that what you see is what is in the file.
"""

import pathlib
import sys

import numpy as np
import tifffile

import orch_contact

SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
ARM = "SHIP-V2"
OUT = pathlib.Path(r"C:\dev\strehl-out\ORCH-CONTACT")
TARGET_W = 1400


def load_master(path):
    """Read a 16-bit master. Refuses anything that is not what it claims."""
    a = tifffile.imread(str(path))
    if a.dtype != np.uint16:
        raise SystemExit(
            "%s is %s, expected uint16 -- refusing to guess its encoding"
            % (path.name, a.dtype)
        )
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit("%s has shape %r, expected HxWx>=3" % (path.name, a.shape))
    return a[:, :, :3]


def box_down(a, k):
    """Integer box-average downsample. Crops the remainder; never resamples."""
    h = (a.shape[0] // k) * k
    w = (a.shape[1] // k) * k
    b = a[:h, :w, :].astype(np.float32)
    b = b.reshape(h // k, k, w // k, k, 3).mean(axis=(1, 3))
    return b


def to8(f16):
    """16-bit display-encoded -> 8-bit. No tone mapping: section 102 retracted
    the claim that these masters need one. Scale only, and report the cost."""
    v = f16 / 257.0
    lo = float((v < 0.5).mean())
    hi = float((v > 254.5).mean())
    return np.clip(v, 0, 255).astype(np.uint8), lo, hi


def one(path, target_w=TARGET_W):
    a = load_master(path)
    k = max(1, int(round(a.shape[1] / float(target_w))))
    small = box_down(a, k)
    a8, lo, hi = to8(small)
    name = path.stem.replace("--%s" % ARM, "")
    dst = OUT / ("whole-%s.png" % name)
    orch_contact.png_rgb(a8, str(dst))
    p = np.percentile(small, [1, 50, 99])
    return {
        "name": name,
        "k": k,
        "shape": (a.shape[1], a.shape[0]),
        "out": (a8.shape[1], a8.shape[0]),
        "black": lo,
        "white": hi,
        "p1": p[0] / 257.0,
        "p50": p[1] / 257.0,
        "p99": p[2] / 257.0,
        "path": dst,
    }


def sheet(paths, cols=5, cell_w=460):
    """All masters on one page. Small enough to miss detail, large enough to
    catch the class of defect that a 1:1 crop cannot see by construction."""
    cells = []
    for p in paths:
        a = load_master(p)
        k = max(1, int(round(a.shape[1] / float(cell_w))))
        a8, _, _ = to8(box_down(a, k))
        cells.append((p.stem.replace("--%s" % ARM, ""), a8))
    ch = max(c.shape[0] for _, c in cells)
    cw = max(c.shape[1] for _, c in cells)
    rows = (len(cells) + cols - 1) // cols
    lab = orch_contact.LABEL_H
    canvas = np.zeros((rows * (ch + lab), cols * cw, 3), np.uint8)
    for i, (name, c) in enumerate(cells):
        y = (i // cols) * (ch + lab)
        x = (i % cols) * cw
        canvas[y:y + c.shape[0], x:x + c.shape[1], :] = c
        orch_contact.draw_text(canvas, name.upper()[:34], y + ch + 2, x + 2)
    dst = OUT / "whole-sheet.png"
    orch_contact.png_rgb(canvas, str(dst))
    print("wrote %s  %dx%d  (%d cells, %d columns)"
          % (dst, canvas.shape[1], canvas.shape[0], len(cells), cols))
    return dst


def main():
    # Same hard-coded-arm defect that orch_printready.py carried: the directory
    # and the "--SHIP-V2" suffix were constants, so pointing this at a newer
    # render silently found nothing. Both are now flags, and the suffix is
    # derived from the directory name unless overridden.
    global SHIP
    argv = []
    arm = None
    for a in sys.argv[1:]:
        if a == "--sheet":
            continue
        if a.startswith("--dir="):
            SHIP = pathlib.Path(a[6:])
        elif a.startswith("--arm="):
            arm = a[6:]
        else:
            argv.append(a)
    want_sheet = "--sheet" in sys.argv[1:]
    if not SHIP.is_dir():
        raise SystemExit("no such directory: %s" % SHIP)
    if arm is None:
        arm = SHIP.name
    global ARM
    ARM = arm
    paths = sorted(SHIP.glob("*--%s.tiff" % arm))
    if argv:
        want = set(argv)
        paths = [p for p in paths if p.stem.replace("--%s" % arm, "") in want]
        missing = want - {p.stem.replace("--%s" % arm, "") for p in paths}
        if missing:
            raise SystemExit("no master for: %s" % ", ".join(sorted(missing)))
    if not paths:
        raise SystemExit("no masters in %s" % SHIP)
    OUT.mkdir(parents=True, exist_ok=True)

    if want_sheet:
        sheet(paths)
        print("\nA contact sheet cannot certify anything. It can only show you "
              "that something is wrong, and only if the wrongness is large.")
        return

    print("ORCH whole-frame view of %d master(s)\n" % len(paths))
    print(
        "%-30s %5s %11s %8s %8s %8s %8s %8s"
        % ("subject", "down", "output", "black%", "white%", "p1", "p50", "p99")
    )
    dark = 0
    blown = 0
    for p in paths:
        r = one(p)
        print(
            "%-30s /%-4d %5dx%-5d %7.3f%% %7.3f%% %8.1f %8.1f %8.1f"
            % (
                r["name"],
                r["k"],
                r["out"][0],
                r["out"][1],
                100.0 * r["black"],
                100.0 * r["white"],
                r["p1"],
                r["p50"],
                r["p99"],
            )
        )
        if r["black"] > 0.02:
            dark += 1
        if r["white"] > 0.02:
            blown += 1

    print("\nwrote %d PNG(s) to %s" % (len(paths), OUT))
    print(
        "%d of %d crush >2%% of the frame to black, %d of %d blow >2%% to white "
        "AFTER downsampling -- a box mean cannot create a clipped pixel, so "
        "anything counted here is clipped in the master itself."
        % (dark, len(paths), blown, len(paths))
    )
    print(
        "\nThese numbers describe the ENCODING, not the picture. Nothing here "
        "can tell you an image is ugly. Open the PNGs."
    )


if __name__ == "__main__":
    main()

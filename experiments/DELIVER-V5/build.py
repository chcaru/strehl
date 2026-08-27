"""build.py -- build DELIVER-V5: a gallery a photographer can trust at every zoom.

Two products per master, and nothing in between:

  overview/    the whole frame, reduced by an EXACT integer factor 4 with a box
               (area-average) kernel.  Box has no negative lobes, so by the hull
               theorem it cannot manufacture a rim; commission_rim.py proves the
               statistic that says so can also convict, and crosscheck.py shows
               my implementation of it agrees with another lane's.
               Labelled ON THE IMAGE as reduced, with the kernel named.

  crops-1to1/  380 px integer slices.  No resize, no sharpening, no grade, not
               one resampled pixel.  V-EYES commissioned the viewer these are
               read in: it resolves a 1 px grating at 400 px and is a flat wash
               by 600, so anything larger than this is shown through a reduction
               the viewer chose and nobody measured.

The label bars are appended BELOW the image data.  Not one pixel of a reduced
image or a crop is written by the labeller -- verify.py re-derives both from the
master and would catch it if they were.

Usage:  python build.py [--limit N]
"""
import json
import os
import sys
import time

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

import rimlib
from geom import masters

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "ORCH-drift-check"))
import true11                                        # noqa: E402  (read-only reuse)

DST = r"C:\dev\strehl-out\DELIVER-V5"
K = 4                       # exact for 7032, 7040 and 4688
CROP = true11.CROP          # 380, from the lane that commissioned the viewer
VIEWER_LIMIT = 400          # V-EYES: 1 px grating resolved at 400, wash by 600
BAR_CROP = 18
BAR_OVER = 30
N_SITES = 3

# ---------------------------------------------------------------------------
# COLOUR AND PRINT-SIZE METADATA ON THE DELIVERED PNGs
#
# BUILD-OUTPUT measured the delivered tree and found 0 of 26 full-resolution
# PNGs carried an ICC profile, an sRGB chunk, or a pHYs chunk -- while the
# 16-bit masters they came from carried "strehl sRGB (IEC 61966-2-1)" and
# 300 dpi/inch on 26 of 26.  image_out.rs was making the metadata correctly and
# the delivery was casting to uint8 through PIL and dropping all of it.  An
# untagged PNG is assigned the consumer's working space: Photoshop, a browser
# and a print lab will each guess, usually guess sRGB, and usually be right,
# which is the kind of defect that survives until the once it does not.
#
# WHY RAW CHUNK SPLICING RATHER THAN RE-SAVING THROUGH PIL
#
# The requirement is that PIXELS MUST NOT CHANGE -- ORCH's
# verify_delivery_all26.py compares decoded pixels against the masters and must
# still read 26 exact / 0 differing afterwards.  Re-encoding through PIL would
# re-run the compressor over the samples; the output should be pixel-identical
# but nothing about that is guaranteed by construction, and "should be" is not
# the standard here.  Splicing chunks into the byte stream cannot alter image
# data because it never touches IDAT: the guarantee is structural, not tested.
#
# WHY iCCP AND NOT THE 1-BYTE sRGB CHUNK
#
# The sRGB chunk is a rendering-intent flag that names a space by reference.
# Embedding the master's OWN profile bytes instead makes the two deliverables
# provably the same colour space -- the PNG's profile md5 equals the TIFF's, and
# that is checkable rather than asserted.  The PNG spec says a file should not
# carry both, so any pre-existing sRGB/gAMA/cHRM is removed first, which also
# makes the operation idempotent.
PRINT_DPI = 300
PPM = int(round(PRINT_DPI / 0.0254))     # pHYs is pixels per METRE, unit code 1
PNG_SIG = b"\x89PNG\r\n\x1a\n"
COLOUR_CHUNKS = (b"iCCP", b"sRGB", b"gAMA", b"cHRM", b"pHYs")
_ICC_CACHE = []


def master_icc():
    """The ICC profile bytes taken from a shipped master, read once.

    Taken from the master rather than synthesised here so the two deliverables
    cannot drift apart: whatever image_out.rs embedded is what the preview
    declares, and ship_census.py can compare the two md5s.
    """
    if not _ICC_CACHE:
        import struct as _s
        name, path = masters()[0]
        with open(path, "rb") as fh:
            buf = fh.read()
        (off,) = _s.unpack("<I", buf[4:8])
        (n,) = _s.unpack("<H", buf[off:off + 2])
        prof = None
        for i in range(n):
            p = off + 2 + 12 * i
            tag, typ, cnt = _s.unpack("<HHI", buf[p:p + 8])
            if tag == 34675:
                (vo,) = _s.unpack("<I", buf[p + 8:p + 12])
                prof = buf[vo:vo + cnt]
                break
        if prof is None:
            raise SystemExit("master %s carries no ICC profile to copy" % name)
        _ICC_CACHE.append(prof)
    return _ICC_CACHE[0]


def _chunks(raw):
    """Split a PNG into [(type, data)], verifying every CRC on the way in."""
    import binascii
    import struct as _s
    if raw[:8] != PNG_SIG:
        raise ValueError("not a PNG")
    out, off = [], 8
    while off + 8 <= len(raw):
        (ln,) = _s.unpack(">I", raw[off:off + 4])
        typ = raw[off + 4:off + 8]
        data = raw[off + 8:off + 8 + ln]
        (crc,) = _s.unpack(">I", raw[off + 8 + ln:off + 12 + ln])
        if binascii.crc32(typ + data) & 0xFFFFFFFF != crc:
            raise ValueError("CRC failure in %s chunk" % typ.decode("latin-1"))
        out.append((typ, data))
        off += 12 + ln
        if typ == b"IEND":
            break
    return out


def _assemble(parts):
    import binascii
    import struct as _s
    o = bytearray(PNG_SIG)
    for typ, data in parts:
        o += _s.pack(">I", len(data)) + typ + data
        o += _s.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)
    return bytes(o)


def tag_png(path):
    """Give one PNG the master's ICC profile and a 300 dpi pHYs, in place.

    Returns True if the file was rewritten.  IDAT is copied across untouched, so
    the decoded image cannot change.  Both chunks are inserted immediately after
    IHDR, which satisfies the ordering rules for iCCP (before PLTE and IDAT) and
    pHYs (before IDAT).
    """
    import struct as _s
    import zlib
    with open(path, "rb") as fh:
        raw = fh.read()
    parts = _chunks(raw)
    kept = [(t, d) for t, d in parts if t not in COLOUR_CHUNKS]
    icc = (b"strehl\x00\x00" + zlib.compress(master_icc(), 9))
    phys = _s.pack(">IIB", PPM, PPM, 1)
    i = next(k for k, (t, _) in enumerate(kept) if t == b"IHDR")
    out = kept[:i + 1] + [(b"iCCP", icc), (b"pHYs", phys)] + kept[i + 1:]
    blob = _assemble(out)
    tmp = path + ".tagging"
    with open(tmp, "wb") as fh:
        fh.write(blob)
    os.replace(tmp, path)                       # atomic: never a torn 60 MB file
    return True


def retag_tree(root):
    """Tag every PNG under `root`, including those written by other lanes.

    build.py writes overview/ and crops-1to1/.  full-resolution/,
    crops-worst-case/, known-defects/ and what-stacking-does/ are written by
    scripts under experiments/ORCH-drift-check/, which this lane does not own.
    Tagging the tree here fixes the delivered artefact without editing another
    lane's code; the upstream writers still emit untagged PNGs on a fresh run
    and that is routed to the orchestrator, not silently patched.
    """
    n, failed = 0, []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.lower().endswith(".png"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                tag_png(p)
                n += 1
            except Exception as e:              # noqa: BLE001
                failed.append((p, "%s: %s" % (type(e).__name__, e)))
    return n, failed



def font(size):
    for cand in ("consola.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except Exception:
            pass
    return ImageFont.load_default()


def label_below(a8, text, bar_h, size):
    """Append a label bar UNDER the image. Returns a new array; a8 is untouched."""
    h, w = a8.shape[:2]
    ch = a8.shape[2] if a8.ndim == 3 else 1
    canvas = np.zeros((h + bar_h, w, 3), np.uint8)
    canvas[:h] = a8 if ch == 3 else a8[..., None]
    im = Image.fromarray(canvas)
    d = ImageDraw.Draw(im)
    d.rectangle([0, h, w - 1, h + bar_h - 1], fill=(16, 16, 16))
    d.text((4, h + (bar_h - size) // 2 - 1), text, fill=(215, 215, 215), font=font(size))
    return np.asarray(im)


def sites(y):
    """N_SITES crops, one per horizontal third, each at that third's best site.

    true11.best_site is reused verbatim -- it is the lane that owns crop siting,
    and its selection is deliberately not hand-picked: it lands on the highest
    mean |Laplacian| tile, which is also where a stacking failure shows worst.
    Running it per-third is what guarantees the three crops are separated
    without me choosing any of them.
    """
    h, w = y.shape
    third = w // N_SITES
    out = []
    for i in range(N_SITES):
        x_off = i * third
        sub = y[:, x_off:x_off + third]
        cx, cy = true11.best_site(sub)
        cx += x_off
        x0 = max(0, min(w - CROP, cx - CROP // 2))
        y0 = max(0, min(h - CROP, cy - CROP // 2))
        out.append((x0, y0))
    return out


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None

    if "--retag" in sys.argv:
        # Metadata-only pass over an already-built tree.  Kept separate from the
        # build because rebuilding would re-derive crop sites and rewrite the
        # manifest, and the deliverable's own verifiers assert exact counts
        # against both.  Fixing metadata must not move a count.
        import hashlib
        prof = master_icc()
        print("master ICC: %d bytes  md5 %s"
              % (len(prof), hashlib.md5(prof).hexdigest()[:12]))
        print("tagging every PNG under %s with that profile and %d dpi"
              % (DST, PRINT_DPI))
        t0 = time.time()
        n, failed = retag_tree(DST)
        print("  tagged %d PNG(s) in %.1f s, %d failed" % (n, time.time() - t0,
                                                           len(failed)))
        for p, why in failed:
            print("  FAILED %s  %s" % (p, why))
        return 0 if not failed else 1

    assert CROP + BAR_CROP <= VIEWER_LIMIT, (
        "a labelled crop must stay inside the viewer's measured resolve limit: "
        "%d + %d > %d" % (CROP, BAR_CROP, VIEWER_LIMIT))
    print("crop %d px + %d px label bar = %d px, inside the %d px the viewer was "
          "measured to resolve" % (CROP, BAR_CROP, CROP + BAR_CROP, VIEWER_LIMIT))

    os.makedirs(os.path.join(DST, "overview"), exist_ok=True)
    os.makedirs(os.path.join(DST, "crops-1to1"), exist_ok=True)

    ms = masters()
    if limit:
        ms = ms[:limit]

    rendered, refused, failed = [], [], []
    manifest = []
    t0 = time.time()

    for i, (name, p) in enumerate(ms):
        try:
            a16 = tifffile.imread(p)
            h, w = a16.shape[:2]
            if h % K or w % K:
                refused.append((name, "%dx%d is not divisible by %d, so no exact "
                                      "integer-factor box reduction exists" % (w, h, K)))
                del a16
                continue
            a8 = rimlib.to8(a16)
            del a16

            red = rimlib.box_reduce(a8, K)
            red8 = np.rint(red).astype(np.uint8)
            exc, dfc = rimlib.hull_block(a8, red8.astype(np.float64), K)
            rim = float(np.maximum(exc, dfc).max())
            ae = rimlib.area_err(a8, red8.astype(np.float64), K)

            oh, ow = red8.shape[:2]
            txt = ("REDUCED %dx  kernel: BOX / area average, no negative lobes  "
                   "injected rim %.6f DN   %s   %dx%d -> %dx%d   NOT 1:1 -- if "
                   "your viewer shrinks this further that reduction is the "
                   "VIEWER'S and it may ring; judge halos in crops-1to1/"
                   % (K, rim, name, w, h, ow, oh))
            op = os.path.join(DST, "overview", "%s__reduced-%dx-box.png" % (name, K))
            Image.fromarray(label_below(red8, txt, BAR_OVER, 18)).save(op)
            tag_png(op)

            y = a8[..., 1].astype(np.float32)
            crops = []
            for (x0, y0) in sites(y):
                c = a8[y0:y0 + CROP, x0:x0 + CROP]        # integer slice, nothing else
                ct = "TRUE 1:1  no resampling  %s (%d,%d)" % (name, x0, y0)
                fn = "%s__1to1_%d_%d.png" % (name, x0, y0)
                cp = os.path.join(DST, "crops-1to1", fn)
                Image.fromarray(label_below(c, ct, BAR_CROP, 12)).save(cp)
                tag_png(cp)
                crops.append({"file": fn, "x0": x0, "y0": y0, "n": CROP})
            del y, a8, red, red8

            rendered.append(name)
            manifest.append({"name": name, "master": p, "w": w, "h": h,
                             "k": K, "rim_dn": rim, "area_err_dn": ae,
                             "overview": "%s__reduced-%dx-box.png" % (name, K),
                             "bar_overview": BAR_OVER, "bar_crop": BAR_CROP,
                             "crops": crops})
            print("%2d/%2d %-38s rim %.6f  area_err %.6f  %dx%d  %d crops"
                  % (i + 1, len(ms), name, rim, ae, ow, oh, len(crops)), flush=True)
        except Exception as e:                            # noqa: BLE001
            failed.append((name, "%s: %s" % (type(e).__name__, e)))
            print("%2d/%2d %-38s FAILED %s" % (i + 1, len(ms), name, e), flush=True)

    with open(os.path.join(DST, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"k": K, "crop": CROP, "n_sites": N_SITES,
                   "bar_overview": BAR_OVER, "bar_crop": BAR_CROP,
                   "images": manifest}, f, indent=1)

    dt = time.time() - t0
    print("\n=== counted partition of masters ===")
    print("  rendered %d + refused %d + failed %d = %d of %d   %s"
          % (len(rendered), len(refused), len(failed),
             len(rendered) + len(refused) + len(failed), len(ms),
             "OK" if len(rendered) + len(refused) + len(failed) == len(ms) else "MISMATCH"))
    for n, why in refused:
        print("  REFUSED %-30s %s" % (n, why))
    for n, why in failed:
        print("  FAILED  %-30s %s" % (n, why))
    if manifest:
        rims = [m["rim_dn"] for m in manifest]
        print("\n  injected rim over %d rendered masters: max %.6f  median %.6f DN"
              % (len(rims), max(rims), float(np.median(rims))))
    print("  %.1f s, %d overview + %d crop files"
          % (dt, len(manifest), sum(len(m["crops"]) for m in manifest)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

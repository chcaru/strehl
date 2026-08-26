#!/usr/bin/env python3
"""Turn the 26 full-resolution 16-bit TIFF renders into something a human can look at.

The gallery ships as 7032x4688 16-bit RGB TIFFs, 188 MB each, 4.8 GB total.
That is the right deliverable for printing and the wrong one for answering "where
are some stacks I can view".  This writes three things:

  view/<name>.jpg    long edge 2400 px, quality 92 -- the browse copy
  full/<name>.jpg    full resolution, quality 95 -- the print/pixel-peep copy
  contact.jpg        every subject on one sheet, labelled

Rules this obeys, learned the hard way in this project:

  * 16-bit TIFFs are read with tifffile and asserted uint16.  PIL silently
    mangles them.
  * Downscaling for the browse copy uses PIL LANCZOS on the 8-bit conversion,
    which is a viewing operation.  Nothing here is ever used for measurement --
    the measurement instruments read the TIFFs directly.
  * The 16->8 bit conversion is a plain right shift by 8.  No tone curve, no
    autolevel, no per-image normalisation: the renders already carry
    --auto-exposure, and a second per-image gain here would make the sheet lie
    about what the tool produced.

THE VERDICT OVERLAY (--triage)
------------------------------
A contact sheet that shows 26 subjects with no indication of which is which is
a product failure independent of any algorithm: the owner saw the bad ones and
judged the whole tool.  With --triage pointing at BUILD-TRIAGE's triage.json,
every tile carries its verdict, the number behind it, and -- where one exists --
the remedy, colour-coded by whether the fix belongs to the MERGE or to the
CAMERA.  The header prints the category counts and their arithmetic.

Nothing here grades on a curve.  A subject that is bad is labelled bad, with
the reason, and the sheet says whether it is worth retouching or needs a
reshoot.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


def load8(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return (a >> 8).astype(np.uint8)


def font(sz: int):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            continue
    return ImageFont.load_default()


# Verdict vocabulary, shared with experiments/BUILD-TRIAGE/triage.py.
CAT_ORDER = ["GOOD", "GOOD - localised coverage gap", "MERGE-LIMITED",
             "CAPTURE-LIMITED - coverage gap",
             "CAPTURE-LIMITED - occlusion/geometry",
             "CAPTURE-LIMITED - diffraction/magnification",
             "CAPTURE-LIMITED - motion", "UNRESOLVED"]
SHORT = {
    "GOOD": "GOOD",
    "GOOD - localised coverage gap": "GOOD, one region uncovered",
    "MERGE-LIMITED": "MERGE-LIMITED (fix the software)",
    "CAPTURE-LIMITED - coverage gap": "CAPTURE: coverage gap",
    "CAPTURE-LIMITED - occlusion/geometry": "CAPTURE: occluded geometry",
    "CAPTURE-LIMITED - diffraction/magnification": "CAPTURE: diffraction",
    "CAPTURE-LIMITED - motion": "CAPTURE: subject moved",
    "UNRESOLVED": "UNRESOLVED (not examined)",
}
COLOUR = {
    "GOOD": (110, 205, 120),
    "GOOD - localised coverage gap": (168, 205, 110),
    "MERGE-LIMITED": (226, 86, 74),
    "CAPTURE-LIMITED - coverage gap": (226, 168, 62),
    "CAPTURE-LIMITED - occlusion/geometry": (214, 132, 92),
    "CAPTURE-LIMITED - diffraction/magnification": (96, 158, 226),
    "CAPTURE-LIMITED - motion": (176, 124, 220),
    "UNRESOLVED": (150, 150, 156),
}


def load_triage(path: str | None):
    """Verdicts keyed by subject, or ({}, {}) when running without them."""
    if not path:
        return {}, {}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return {r["subject"]: r for r in doc["rows"]}, doc["counts"]


def load_fill(path: str | None):
    """BUILD-TRIAGE fillfactor.json keyed by subject, or {} if absent.

    Optional by design: the sheet must still build for anyone who has not run
    fillfactor.py.  A missing file drops the detail line and says so, rather
    than failing or -- worse -- printing a blank where a number belongs.
    """
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {r["sub"]: r for r in json.load(fh)["rows"]}


def detail_line(sub: str, fill_rows: dict, n: int) -> str:
    """Absolute detail actually present, and how much of the tile carries it.

    Two numbers, because either alone misleads.  `cond` is sharpness measured
    ONLY over detail-bearing pixels, so it is not diluted by flat area; `fill`
    is how much of the tile that was.  A low `cond` at high `fill` is a subject
    that is genuinely under-resolved; a low mean at low `fill` is merely a
    sparse subject, and the corpus contains both.  Ranked, not thresholded:
    `cond` has no empty band anywhere in this corpus, so any cut placed on it
    would be invented rather than measured.
    """
    r = fill_rows.get(sub)
    if not r:
        return ""
    return (f"detail {r['cond']:.0f} DN at {100.0 * r['fill']:.0f}% fill; "
            f"sharpness rank {r['rk_cond']}/{n}")


def measure_line(row: dict) -> str:
    """One line of the number that produced the verdict -- never a bare label."""
    e = row.get("evidence") or {}
    v = row["verdict"]
    if v == "MERGE-LIMITED":
        return (f"merge {e.get('worst_blur_px')} px softer than best frame "
                f"({e.get('merge_edge_dnpx')} vs {e.get('frame_edge_dnpx')} DN/px)")
    if v == "CAPTURE-LIMITED - coverage gap":
        e0, eN = e.get("end0_pct") or 0.0, e.get("endN_pct") or 0.0
        end = "first" if e0 >= eN else "last"
        return (f"{float(e.get('detail_gap_pct') or 0):.1f}% of detail pixels "
                f"elect the {end} frame "
                f"({float(e.get('detail_enrichment') or 0):.2f}x chance)")
    if v == "GOOD - localised coverage gap":
        e0, eN = e.get("end0_pct") or 0.0, e.get("endN_pct") or 0.0
        end = "first" if e0 >= eN else "last"
        return (f"merge x{float(e.get('orch_site_ratio') or 0):.2f} vs best frame; "
                f"{float(e.get('detail_gap_pct') or 0):.1f}% detail px elect {end} frame")
    if v == "CAPTURE-LIMITED - occlusion/geometry":
        return (f"{float(e.get('detail_gap_pct') or 0):.1f}% of detail pixels "
                f"at a bracket end; occlusion-driven")
    if v == "CAPTURE-LIMITED - motion":
        return (f"adjacent-frame NCC {e.get('motion_med_ncc')}, "
                f"{e.get('motion_blocks')}/24 blocks moving")
    if v == "CAPTURE-LIMITED - diffraction/magnification":
        return (f"best source frame only {e.get('frame_edge_dnpx')} DN/px; "
                f"merge {e.get('merge_edge_dnpx')} DN/px")
    if v == "GOOD":
        # Quoted from the FLAT reference site: a median-residual noise statistic
        # counts resolved detail as noise wherever there is detail to resolve.
        na = e.get("noise_flat")
        if na is None:
            noise = "flat-site noise not measured"
        elif na >= 1.0:
            noise = f"{na:.2f}x cleaner on flats"
        else:
            noise = f"{1.0 / na:.2f}x noisier on flats"
        return (f"merge within {float(e.get('worst_blur_px') or 0.0):.2f} px "
                f"of best frame; {noise}")
    return "; ".join(row.get("why") or []) or "no evidence"


def wrap(s: str, n: int) -> list[str]:
    out, line = [], ""
    for word in s.split():
        if len(line) + len(word) + 1 > n:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


# Caption budgets, in wrapped lines of WRAP_COLS characters.
WRAP_COLS = 62
EVIDENCE_LINES = 1
REMEDY_LINES = 2
DETAIL_LINES = 1


def check_budgets(tri_rows: dict, fill_rows: dict | None = None) -> None:
    """Hard-fail on any caption the sheet would silently truncate.

    The tile draws a fixed number of wrapped lines and discards the rest with a
    slice, so an over-long remedy loses its last clause without any visible
    sign -- an earlier sheet shipped `flowers-cpl` reading "Reshoot at a" with
    the rest of the sentence gone.  A caption that is cut off mid-instruction is
    worse than no caption, because it still looks authoritative.
    """
    bad = []
    fill_rows = fill_rows or {}
    n = len(fill_rows)
    for name, row in sorted(tri_rows.items()):
        for what, text, budget in (
                ("evidence", measure_line(row), EVIDENCE_LINES),
                ("remedy", row.get("remedy") or "", REMEDY_LINES),
                ("detail", detail_line(name, fill_rows, n), DETAIL_LINES)):
            lines = wrap(text, WRAP_COLS)
            if len(lines) > budget:
                bad.append(f"  {name} [{what}] needs {len(lines)} lines, "
                           f"budget {budget}: {text!r}")
    if bad:
        raise SystemExit("caption budget exceeded; these would be truncated:\n"
                         + "\n".join(bad))
    print(f"caption budgets OK: {len(tri_rows)} tiles fit "
          f"{EVIDENCE_LINES}+{REMEDY_LINES}+{DETAIL_LINES} lines at "
          f"{WRAP_COLS} cols"
          + ("" if fill_rows else "  (no fillfactor.json: detail line omitted)"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=r"C:\dev\strehl-out\SHIP-V1")
    ap.add_argument("dst", nargs="?", default=r"C:\dev\strehl-out\SHIP-V1\viewable")
    ap.add_argument("--long-edge", type=int, default=2400)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", type=int, default=560)
    ap.add_argument("--skip-full", action="store_true")
    ap.add_argument("--triage", default=None,
                    help="path to BUILD-TRIAGE triage.json; adds per-tile "
                         "verdicts, evidence and remedies to the sheet")
    ap.add_argument("--fill",
                    default=r"C:\dev\strehl-out\BUILD-TRIAGE\fillfactor.json",
                    help="path to BUILD-TRIAGE fillfactor.json; adds the "
                         "measured detail line. Optional: omitted if absent")
    args = ap.parse_args()

    vdir = os.path.join(args.dst, "view")
    fdir = os.path.join(args.dst, "full")
    os.makedirs(vdir, exist_ok=True)
    os.makedirs(fdir, exist_ok=True)

    names = sorted(n[:-5] for n in os.listdir(args.src) if n.endswith(".tiff"))
    print(f"{len(names)} subjects from {args.src}")

    thumbs: list[tuple[str, Image.Image]] = []
    for i, n in enumerate(names, 1):
        src = os.path.join(args.src, n + ".tiff")
        a = load8(src)
        im = Image.fromarray(a, "RGB")
        h, w = a.shape[:2]

        fp = os.path.join(fdir, n + ".jpg")
        if not args.skip_full and not os.path.exists(fp):
            im.save(fp, "JPEG", quality=95, subsampling=0, optimize=True)

        s = args.long_edge / max(w, h)
        vs = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        vp = os.path.join(vdir, n + ".jpg")
        vs.save(vp, "JPEG", quality=92, optimize=True)

        t = args.cell / max(w, h)
        thumbs.append((n, im.resize((max(1, int(w * t)), max(1, int(h * t))),
                                    Image.LANCZOS)))
        print(f"  [{i:2d}/{len(names)}] {n:<40s} {w}x{h} -> "
              f"{vs.size[0]}x{vs.size[1]}")

    cols = args.cols
    rows = (len(thumbs) + cols - 1) // cols
    cw = max(t.size[0] for _, t in thumbs)
    ch = max(t.size[1] for _, t in thumbs)
    tri_rows, tri_counts = load_triage(args.triage)
    fill_rows = load_fill(args.fill)
    if tri_rows:
        check_budgets(tri_rows, fill_rows)
        # ORDERING.  Alphabetical order is why the owner judged the tool by its
        # worst tiles: `flowers-cpl` and `flower-inner-edge-cpl` land in the
        # middle of the sheet with no indication that they are capture failures,
        # while `bee-3-cpl`, `pencil-steep-angle-cpl` and `flat-on-ruler-cpl`
        # -- genuinely print-worthy work -- are scattered between them.
        #
        # So: category first (CAT_ORDER, which leads with GOOD), then WITHIN
        # each category by the merge's own measured edge slope at its best site,
        # descending.  That is a measured quantity already in the evidence, not
        # an opinion, and it puts the most-resolved images first.
        #
        # Deliberately NOT sorted by how far the merge beats the source: that
        # ranks "how much the stacker added", which is a developer's question.
        # The owner is looking at pictures, so lead with the ones that hold the
        # most resolved detail.
        cat_ix = {c: i for i, c in enumerate(CAT_ORDER)}

        def order_key(item):
            n, _ = item
            row = tri_rows.get(n) or {}
            cat = row.get("verdict", "UNRESOLVED")
            ev = row.get("evidence") or {}
            detail = float(ev.get("merge_edge_dnpx") or 0.0)
            return (cat_ix.get(cat, len(CAT_ORDER)), -detail, n)

        thumbs.sort(key=order_key)
        print("\ntile order (category, then measured detail DN/px, descending):")
        for i, (n, _) in enumerate(thumbs, 1):
            row = tri_rows.get(n) or {}
            ev = row.get("evidence") or {}
            print(f"  {i:2d}. {n:<38} {row.get('verdict','?'):<38} "
                  f"{float(ev.get('merge_edge_dnpx') or 0.0):>8.1f} DN/px")
    lab = 30 if not tri_rows else 114
    pad = 14
    head = 56 if not tri_rows else 148
    W = cols * (cw + pad) + pad
    H = rows * (ch + pad + lab) + pad + head
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16),
           f"strehl SHIP-V1  --  {len(thumbs)} subjects, pyramid merge, "
           f"lateral-CA correction on, full sensor resolution",
           font=font(22), fill=(235, 235, 240))
    if tri_rows:
        d.text((pad, 46),
               "Each tile carries its own verdict.  The question behind every "
               "verdict: did the MERGE lose detail the source frames contain "
               "(retouch), or did NO frame ever contain it (reshoot)?",
               font=font(15), fill=(170, 172, 182))
        cx = pad
        total = 0
        for cat in CAT_ORDER:
            k = tri_counts.get(cat, 0)
            total += k
            # Zero-count categories are drawn too.  A category that is absent
            # from the key and absent from the arithmetic is indistinguishable
            # from a category that was never tested, and "0 MERGE-LIMITED" is
            # the single most consequential number on this sheet: it is the
            # statement that no subject here needs a software fix.
            txt = f"{k}  {SHORT.get(cat, cat)}"
            col = COLOUR.get(cat, (128, 128, 128))
            if not k:
                col = tuple(int(60 + 0.25 * (c - 60)) for c in col)
            d.rectangle([cx, 74, cx + 13, 87], fill=col)
            d.text((cx + 20, 72), txt, font=font(16),
                   fill=(225, 225, 232) if k else (128, 130, 140))
            cx += 26 + int(d.textlength(txt, font=font(16)))
        d.text((pad, 98),
               f"{'  +  '.join(str(tri_counts.get(c, 0)) for c in CAT_ORDER)}"
               f"  =  {total} of {len(thumbs)} subjects."
               f"  Sharpness measured as edge slope in DN/px on camera-linear "
               f"renders of BOTH arms; blur quoted as an equivalent Gaussian "
               f"sigma in pixels (instrument floor 0.3 px).",
               font=font(14), fill=(150, 152, 162))
        d.text((pad, 120),
               "Colour = who fixes it.  Green: nothing to fix.  Red: the merge "
               "lost detail the frames hold -- fix the software.  Amber/blue/"
               "violet: no frame ever held it -- fix the capture.",
               font=font(14), fill=(150, 152, 162))

    for i, (n, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = head + pad + r * (ch + pad + lab)
        sheet.paste(t, (x + (cw - t.size[0]) // 2, y))
        if not tri_rows:
            d.text((x, y + ch + 6), n[:44], font=font(15), fill=(200, 200, 208))
            continue
        row = tri_rows.get(n)
        cat = row["verdict"] if row else "UNRESOLVED"
        col = COLOUR.get(cat, (128, 128, 128))
        # A 3 px rule in the verdict colour along the top of the tile, so the
        # classification is legible at a glance from across the sheet.
        d.rectangle([x + (cw - t.size[0]) // 2, y,
                     x + (cw + t.size[0]) // 2 - 1, y + 3], fill=col)
        d.text((x, y + ch + 5), n[:46], font=font(15), fill=(210, 210, 218))
        # Dimensions on the tile: the masters are not all the same width (7032
        # or 7040 at a common 4688), which matters to anyone printing the set.
        ev = (row or {}).get("evidence") or {}
        if ev.get("master_w"):
            d.text((x + cw - 80, y + ch + 6),
                   f"{ev['master_w']}x{ev['master_h']}", font=font(12),
                   fill=(140, 142, 150))
        d.text((x, y + ch + 23), SHORT.get(cat, cat), font=font(15), fill=col)
        if row:
            for j, line in enumerate(wrap(measure_line(row), 62)[:1]):
                d.text((x, y + ch + 41 + j * 15), line, font=font(12),
                       fill=(185, 187, 196))
            for j, line in enumerate(wrap(row.get("remedy") or "", 62)[:2]):
                d.text((x, y + ch + 57 + j * 15), line, font=font(12),
                       fill=(150, 152, 162))
            dl = detail_line(n, fill_rows, len(fill_rows))
            if dl:
                d.text((x, y + ch + 89), dl, font=font(12),
                       fill=(126, 138, 150))

    cp = os.path.join(args.dst, "contact-triage.jpg" if tri_rows else "contact.jpg")
    sheet.save(cp, "JPEG", quality=93, optimize=True)
    print(f"\ncontact sheet -> {cp}  ({sheet.size[0]}x{sheet.size[1]})")
    print(f"browse copies -> {vdir}")
    if not args.skip_full:
        print(f"full-res copies -> {fdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

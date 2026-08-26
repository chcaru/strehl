"""Contact sheet ordered strongest-first, so the tool's best work opens the set.

WHY THIS FILE EXISTS RATHER THAN AN EDIT TO contactsheet.py
-----------------------------------------------------------
`experiments/ORCH-drift-check/contactsheet.py` is ORCH's and was NOT edited.
It sorts internally on a p95 gradient proxy, so a different order cannot be
supplied to it from outside -- hence a separate sheet rather than a patch.

THE ORDER AND THE PIXELS COME FROM DIFFERENT FILES, ON PURPOSE
---------------------------------------------------------------
  order  <- ranking.tsv, computed by scripts/rank.py from the FAITHFUL MASTERS
            with the sRGB curve inverted, i.e. in linear light.
  pixels <- the GRADED viewable JPEGs, which are on the far side of both a tone
            curve and a per-image percentile normalisation.

That separation is the whole point. A graded file is presentation output and
nothing numeric may ever be derived from it; the standing rule is that no
number crosses a tone curve. Here no number does: the ranking never sees a
graded file, and the graded file never produces a number. If this file is ever
changed to rank on what it displays, that rule is broken.

MISSING TILES ARE DRAWN, NOT DROPPED
------------------------------------
A subject whose image is absent gets a visible MISSING tile carrying its rank
and the reason. Silently omitting it would make a failed render indistinguishable
from one that was never attempted, and both indistinguishable from a pass.

VERDICTS ARE CARRIED, NEVER INVENTED
------------------------------------
The verdict column is BUILD-TRIAGE's (merge-limited vs capture-limited). This
file renders whatever they supply and writes nothing of its own into it. An
empty verdict prints as "-" so an unclassified subject cannot be read as one
that was classified and found clean.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CAPTION_H = 46
PAD = 10
BG = (24, 24, 26)
FG = (238, 238, 238)
DIM = (150, 150, 155)
MISS = (90, 30, 30)


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def read_ranking(p: Path) -> list[dict]:
    with p.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    keep = [r for r in rows if r.get("rank", "-") != "-"]
    if not keep:
        raise SystemExit(f"{p}: no ranked rows")
    return keep


def find_image(d: Path, subject: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png"):
        for cand in (d / f"{subject}{ext}", d / f"{subject}_graded{ext}"):
            if cand.exists():
                return cand
    hits = sorted(d.glob(f"{subject}.*")) or sorted(d.glob(f"{subject}_*"))
    return hits[0] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ranking", type=Path, required=True,
                    help="ranking.tsv from scripts/rank.py (order source)")
    ap.add_argument("--images", type=Path, required=True,
                    help="directory of graded viewable JPEGs (pixel source)")
    ap.add_argument("--out", type=Path, required=True, help="output PNG")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--tile", type=int, default=440)
    ap.add_argument("--title", default="strehl - ordered by resolved detail, strongest first")
    args = ap.parse_args()

    rows = read_ranking(args.ranking)
    f_big, f_small = load_font(19), load_font(15)

    cols = max(1, args.cols)
    nrows = (len(rows) + cols - 1) // cols
    cw = args.tile + PAD
    ch = args.tile + CAPTION_H + PAD
    head = 58
    sheet = Image.new("RGB", (cols * cw + PAD, nrows * ch + PAD + head), BG)
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD + 2, 16), args.title, font=load_font(24), fill=FG)

    placed = missing = 0
    for i, r in enumerate(rows):
        subject = r["subject"]
        x = PAD + (i % cols) * cw
        y = PAD + head + (i // cols) * ch

        src = find_image(args.images, subject)
        if src is None:
            dr.rectangle([x, y, x + args.tile, y + args.tile], fill=MISS)
            dr.text((x + 12, y + args.tile // 2 - 10), "MISSING", font=f_big, fill=FG)
            dr.text((x + 12, y + args.tile // 2 + 12), "no viewable rendered",
                    font=f_small, fill=DIM)
            missing += 1
        else:
            im = Image.open(src).convert("RGB")
            im.thumbnail((args.tile, args.tile), Image.LANCZOS)
            sheet.paste(im, (x + (args.tile - im.width) // 2,
                             y + (args.tile - im.height) // 2))
            placed += 1

        verdict = (r.get("verdict") or "").strip() or "-"
        dr.text((x + 2, y + args.tile + 6),
                f"#{r['rank']}  {subject}", font=f_big, fill=FG)
        dr.text((x + 2, y + args.tile + 27),
                f"resolved {float(r['resolved']):.4f}   triage: {verdict}",
                font=f_small, fill=DIM)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)

    # Counts partition: every ranked row is placed or missing, and they sum.
    total = len(rows)
    print(f"placed {placed}  missing {missing}  ranked_total {total}")
    assert placed + missing == total, "tile counts do not partition the ranking"
    print(f"wrote {args.out}  ({sheet.width}x{sheet.height})")
    if missing:
        print(f"WARNING: {missing} subject(s) drawn as MISSING tiles, not dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

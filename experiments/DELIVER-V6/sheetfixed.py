"""DELIVER-V6: the corpus sheets, cut at ORCH-EYE's EXACT coordinates.

WHY THIS EXISTS ALONGSIDE THE PLAIN SHEETS
------------------------------------------
`orch_corpuseye.py` chooses each subject's two sites by CONTENT -- a boundary
rule and a texture rule scored on that master's own pixels. That is the right
design for its own question ("does this look print-worthy") and its docstring
says outright that it is deliberately NOT an A/B.

But it means the site can MOVE between two renders of the same subject: the new
master's pixels differ, so the argmax of the scoring surface can land somewhere
else. If it does, `DELIVER-V6/corpus/sheet-03.jpg` and
`ORCH-EYE/corpus/sheet-03.jpg` would show different places and would not be
comparable, while LOOKING exactly as if they were. That is a trap, and it is the
kind this project keeps falling into.

So this script freezes the geometry. It runs the committed site picker ONCE, on
the OLD master, and cuts the SAME (y, x) out of the new one. The result is a
sheet set that is tile-for-tile registered against ORCH-EYE: sheet-NN here and
sheet-NN there show the same subject, the same site, the same pixels' worth of
scene. The owner can flip between them.

Verified before use: driving the committed picker over the old masters
reproduces `ORCH-EYE/corpus/sheet-00.jpg` **byte-identically** (sha256
91DD7720...6768, 519 959 bytes both). So the coordinates this script freezes are
demonstrably ORCH-EYE's own, not a re-derivation that happens to look similar.

ONE TRANSFORM PER SUBJECT, TAKEN FROM THE OLD MASTER, APPLIED TO BOTH
--------------------------------------------------------------------
AGENTS rule 48: "convert linear data for viewing with a stated, identical
transform on every arm, because per-arm autoscaling fabricates differences
between images that do not differ." `orch_corpuseye` derives its scale from the
master it is displaying, which is correct when there is only one master and
WRONG for a comparison -- it would silently re-normalise the two arms to each
other and hide, or invent, a global level change.

Here the scale comes from the OLD master and is used for both arms. A real
exposure or level difference between the builds therefore SHOWS, which is the
point. Stated so it can be argued with.

Usage:
    python sheetfixed.py <old-dir> <new-dir> <out-dir> [--size 520] [--per-sheet 6]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ORCH-drift-check"))

import orch_corpuseye as E  # noqa: E402  the committed instrument, imported not copied


def sites_from_old(a: np.ndarray, size: int):
    """The committed picker's two sites, exactly as `crops_for` computes them."""
    luma = E.to_luma(a)
    bnd, tex = E.score_maps(luma)
    b = E.pick(bnd, luma.shape, size, 8)
    t = E.pick(tex, luma.shape, size, 8, avoid=b[2] if b else None)
    out = []
    for tag, site in (("boundary", b), ("texture", t)):
        if site is not None:
            out.append((tag, site[0], site[1]))
    return out, 1.0 / max(float(np.percentile(luma, 99.9)), 1.0)


def cut(a: np.ndarray, y: int, x: int, size: int, scale: float) -> np.ndarray:
    c = a[y : y + size, x : x + size, :3].astype(np.float32) * scale
    return (np.clip(c, 0.0, 1.0) ** (1.0 / 2.2) * 255.0 + 0.5).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old_dir")
    ap.add_argument("new_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--size", type=int, default=E.SIZE_DEFAULT)
    ap.add_argument("--per-sheet", type=int, default=6)
    ap.add_argument("--cols", type=int, default=3)
    args = ap.parse_args()

    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    dst = Path(args.out_dir)
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "tiles").mkdir(exist_ok=True)

    names = sorted(p.stem for p in old_dir.glob("*.tiff"))
    tiles, sheets, coords, skipped = [], [], [], []

    for name in names:
        pn = new_dir / f"{name}.tiff"
        if not pn.exists():
            skipped.append((name, "no new master"))
            print(f"SKIP     {name}: no new master")
            continue
        ao = tifffile.imread(str(old_dir / f"{name}.tiff"))[:, :, :3]
        an = tifffile.imread(str(pn))[:, :, :3]
        if ao.shape != an.shape:
            skipped.append((name, f"geometry {ao.shape} -> {an.shape}"))
            print(f"CONFOUND {name}: geometry moved")
            continue

        got, scale = sites_from_old(ao.astype(np.float32), args.size)
        for tag, y, x in got:
            t = cut(an, y, x, args.size, scale)
            label = f"{name}  [{tag}]  y={y} x={x}"
            tiles.append((label, t))
            coords.append(dict(subject=name, kind=tag, y=y, x=x))
            # Each tile also written standalone, so a verdict can be pronounced
            # on <=520 px of unresampled pixels rather than on a 1592 px sheet.
            from PIL import Image
            Image.fromarray(t).save(str(dst / "tiles" / f"{name}-{tag}-NEW.png"))
            Image.fromarray(cut(ao, y, x, args.size, scale)).save(
                str(dst / "tiles" / f"{name}-{tag}-OLD.png"))
        print(f"ok       {name}: {[g[0] for g in got]}")

        while len(tiles) >= args.per_sheet:
            batch, tiles = tiles[: args.per_sheet], tiles[args.per_sheet :]
            out = dst / f"sheet-{len(sheets):02d}.jpg"
            dims = E.build_sheet(batch, args.size, args.cols, out)
            sheets.append(str(out))
            print(f"  sheet -> {out}  {dims[0]}x{dims[1]}")

    if tiles:
        out = dst / f"sheet-{len(sheets):02d}.jpg"
        dims = E.build_sheet(tiles, args.size, args.cols, out)
        sheets.append(str(out))
        print(f"  sheet -> {out}  {dims[0]}x{dims[1]}")

    (dst / "coords.json").write_text(json.dumps(
        dict(size=args.size, per_sheet=args.per_sheet, cols=args.cols,
             note="coordinates picked on the OLD master by the committed "
                  "orch_corpuseye picker; transform is the OLD master's, "
                  "applied to both arms",
             coords=coords, skipped=skipped), indent=2))
    print()
    print(f"SUMMARY  {len(coords)} tiles, {len(sheets)} sheets, {len(skipped)} skipped")
    for n, why in skipped:
        print(f"         SKIPPED {n}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

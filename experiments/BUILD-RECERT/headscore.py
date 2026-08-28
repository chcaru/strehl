"""HEAD d2193a55 against SHIP-V4 9b05d0b7, per subject, paired on the same pixels.

WHAT THIS ANSWERS. ORCH's 13-commit drift list -- gatefloor, the demosaic chroma
restore, the geometry guard, the plugin surface -- is entirely contained in pin
2f858c62, verified commit by commit with `git merge-base --is-ancestor`. Only
aa40cc78 and 9c11209e separate that pin from HEAD, and headcheck.py proved both
INERT on the shipping render path: 3 subjects, 296,808,192 samples, max|d| = 0.
So the DEF-2f858c62 arm IS the HEAD baseline and this scores it.

THE INSTRUMENT IS NOT MODIFIED. `flatexp.score_subject` is imported and called
on explicit (base, candidate) paths through the `paths=` argument it already
carries. Its constants, its registration guard and its band definitions are the
ones commissioned at 8/8 in commission_flatexp.py. Repointing a commissioned
instrument by editing its constants is how an instrument silently becomes a
different instrument.

ORIENTATION, stated once because sign errors here invert a conclusion:
base = SHIP-V4, candidate = HEAD. Every ratio is HEAD / SHIP-V4.
  blotch < 1  ->  HEAD has a LOWER noise floor  ->  IMPROVED
  grain  < 1  ->  HEAD has a LOWER fine floor   ->  IMPROVED
  sharp  < 1  ->  HEAD has LESS structure       ->  REGRESSED
The axes therefore read in opposite directions and are never averaged.

TWO-SIDED AND NaN-GUARDED THROUGHOUT. A NaN reached a cert.json in this campaign
tonight and would have read as PASS, because `NaN > x` is False. Here every
subject lands in exactly one of IMPROVED / UNCHANGED / REGRESSED / REFUSED, and
the partition is asserted to sum to the number of subjects found.

THE GAIN CORRECTION IS NOT OPTIONAL. `blotch` and `grain` are MAD and scale
linearly with a global gain; `sharp` is p99.5-over-MAD and is scale-invariant.
strehl normalises tone from each image's own p99.9, and eleven commits that
change the merged image change the image that percentile is taken from. The gain
is measured DIRECTLY between the two sets at the scorer's own sites, not inferred
from a third comparison.

THREE AXES, EACH GATED. An earlier run of this script printed the grain column
without classifying it -- and grain turned out to be the axis that moved most, by
a wide margin (corpus median 0.9417, individual subjects to 0.4357, against
blotch 0.9998 and sharp 1.0009 which barely move at all). A value printed but
never conditioned on is a defect, and this one would have buried the finding in
an unread column while the two gated axes said "nothing happened".
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flatexp import CROP, content_sites, ratios, score_subject  # noqa: E402

SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
HEAD = Path(r"C:\dev\strehl-out\BUILD-RECERT\arms\DEF-2f858c62")
OUT = Path(r"C:\dev\strehl-out\BUILD-RECERT\logs")

# A movement smaller than this is called UNCHANGED. It is the largest |ratio-1|
# that regsens2.py measured from a 1 px registration shift alone across three
# real masters (blotch 0.424%, sharp 0.106%, grain 0.088%), rounded up to 1%.
# Below it the gauge cannot separate a real change from a sub-pixel one.
BAND = 0.01


def measure_gain(a, b):
    """Median candidate/base level at the scorer's own content sites."""
    g = []
    for (y, x) in content_sites(a):
        ca = a[y:y + CROP, x:x + CROP, :].astype(np.float64)
        cb = b[y:y + CROP, x:x + CROP, :].astype(np.float64)
        ma, mb = float(np.mean(ca)), float(np.mean(cb))
        if ma > 0:
            g.append(mb / ma)
    return float(np.median(g)) if g else float("nan")


def classify(v, lower_is_better):
    if v is None or not np.isfinite(v):
        return "REFUSED"
    if abs(v - 1.0) <= BAND:
        return "UNCHANGED"
    better = v < 1.0 if lower_is_better else v > 1.0
    return "IMPROVED" if better else "REGRESSED"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(SHIP))
    ap.add_argument("--base-tag", default="SHIP-V4")
    ap.add_argument("--cand", default=str(HEAD))
    ap.add_argument("--cand-tag", default="DEF-2f858c62")
    ap.add_argument("--json", default=str(OUT / "headscore.json"))
    args = ap.parse_args()
    base_dir, cand_dir = Path(args.base), Path(args.cand)

    ship = {p.name.split("--")[0]: p
            for p in base_dir.glob(f"*--{args.base_tag}.tiff")}
    head = {p.name.split("--")[0]: p
            for p in cand_dir.glob(f"*--{args.cand_tag}.tiff")}
    subs = sorted(set(ship) & set(head))
    only_ship, only_head = sorted(set(ship) - set(head)), sorted(set(head) - set(ship))
    print(f"base : {base_dir}  [{len(ship)}]")
    print(f"cand : {cand_dir}  [{len(head)}]")
    print(f"paired : {len(subs)}")
    if only_ship or only_head:
        print(f"  UNPAIRED base-only {only_ship}  cand-only {only_head}")
    print()

    hdr = (f"{'subject':<38}{'gain':>7}{'blotch':>9}{'corr':>9}{'sharp':>9}"
           f"{'grain':>9}  {'blotch':<10}{'sharp':<10}{'grain':<10}reg")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for s in subs:
        r = score_subject(s, paths=(ship[s], head[s]))
        if r["state"] != "SCORED":
            print(f"{s:<38}{r['state']}")
            rows.append({"subject": s, "state": r["state"]})
            continue
        cells = r["cells"]
        blotch, _ = ratios(cells, "mottle", "floor")
        sharp, _ = ratios(cells, "struct", "struct")
        grain, _ = ratios(cells, "grain", "floor")
        a = tifffile.imread(ship[s])
        b = tifffile.imread(head[s])
        gain = measure_gain(a, b)
        del a, b

        bc = blotch / gain if (blotch is not None and np.isfinite(blotch)
                               and np.isfinite(gain) and gain > 0) else None
        gc = grain / gain if (grain is not None and np.isfinite(grain)
                              and np.isfinite(gain) and gain > 0) else None
        vb, vs = classify(bc, True), classify(sharp, False)
        vg = classify(gc, True)
        reg = (r.get("registration") or {}).get("basis", "?")
        print(f"{s:<38}{gain:>7.4f}"
              f"{(blotch if blotch is not None else float('nan')):>9.4f}"
              f"{(bc if bc is not None else float('nan')):>9.4f}"
              f"{(sharp if sharp is not None else float('nan')):>9.4f}"
              f"{(gc if gc is not None else float('nan')):>9.4f}  "
              f"{vb:<10}{vs:<10}{vg:<10}{reg}")
        rows.append({"subject": s, "state": "SCORED", "gain": gain,
                     "blotch": blotch, "blotch_corr": bc, "sharp": sharp,
                     "grain": grain, "grain_corr": gc,
                     "blotch_verdict": vb, "sharp_verdict": vs,
                     "grain_verdict": vg,
                     "registration": r.get("registration")})

    OUT.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")

    print("\nPER-AXIS PARTITION -- each axis partitions all "
          f"{len(subs)} subjects independently")
    print(f"  {'':<12}{'blotch':>10}{'sharp':>10}{'grain':>10}")
    keys = ("IMPROVED", "UNCHANGED", "REGRESSED", "REFUSED")
    unscored = sum(1 for r in rows if r.get("state") != "SCORED")
    for k in keys:
        nb = sum(1 for r in rows if r.get("blotch_verdict") == k)
        ns = sum(1 for r in rows if r.get("sharp_verdict") == k)
        ng = sum(1 for r in rows if r.get("grain_verdict") == k)
        print(f"  {k:<12}{nb:>10}{ns:>10}{ng:>10}")
    print(f"  {'NOT SCORED':<12}{unscored:>10}{unscored:>10}{unscored:>10}")
    for axis in ("blotch_verdict", "sharp_verdict", "grain_verdict"):
        tot = sum(1 for r in rows if r.get(axis) in keys) + unscored
        if tot != len(subs):
            raise SystemExit(f"AXIS {axis} DOES NOT SUM: {tot} != {len(subs)}")
    print(f"  {'TOTAL':<12}{len(subs):>10}{len(subs):>10}{len(subs):>10}  (all sum)")

    sc = [r for r in rows if r.get("state") == "SCORED"]
    if sc:
        m = lambda k: float(np.median([r[k] for r in sc
                                       if r[k] is not None and np.isfinite(r[k])]))
        print(f"\ncorpus median  gain {m('gain'):.4f}   "
              f"blotch {m('blotch'):.4f} (corr {m('blotch_corr'):.4f})   "
              f"sharp {m('sharp'):.4f}   grain corr {m('grain_corr'):.4f}")
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

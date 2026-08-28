"""Is the blotch ratio biased by a brightness difference between the arms?

THE PROBLEM, and it was found by the tone census rather than by inspection. The
census reports a `mean x` column against SHIP-V4: the DEF arm sits at 1.000 on
every subject, but the FLAT1 arm runs from 0.993 to 1.115. The two arms are not
at the same level, because strehl normalises tone from each image's own p99.9
and a flat exponent changes the merged image that percentile is taken from.

WHY IT MATTERS TO ONE STATISTIC AND NOT THE OTHER:

  * `sharp` is `structure` = p99.5 over MAD. That is a RATIO taken inside one
    crop, so a global gain cancels and the number is untouched.
  * `blotch` and `grain` are `floor` = MAD, which scales LINEARLY with a global
    gain. If flat-1 is rendered 1.5% brighter, its floor is 1.5% larger for that
    reason alone, and the reported blotch ratio understates how much quieter it
    really is.

The direction matters for honesty: this bias runs AGAINST flat-1, which is the
arm this lane's recommendation goes against. Correcting it makes the case for
flat-1 stronger, and that is exactly why it has to be corrected rather than
noted and dropped.

Rather than infer the DEF->FLAT1 gain by dividing two separate comparisons
against SHIP-V4, this measures it DIRECTLY between the two arms, at the same
content sites the scorer uses, so the correction and the number it corrects come
off the same pixels.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flatexp import DEF_DIR, FLAT_DIR, CROP, content_sites  # noqa: E402

OUT = Path(r"C:\dev\strehl-out\BUILD-RECERT\logs")


def main():
    scored = json.loads((OUT / "flatexp.json").read_text(encoding="utf-8"))
    by_subject = {r["subject"]: r for r in scored}

    print(f"{'subject':<38} {'gain':>7} {'blotch':>8} {'corr':>8} "
          f"{'grain':>8} {'corr':>8}")
    print("-" * 82)
    rows = []
    for name in sorted(by_subject):
        r = by_subject[name]
        if r.get("state") != "SCORED":
            continue
        dp = DEF_DIR / f"{name}--DEF-2f858c62.tiff"
        fp = FLAT_DIR / f"{name}--FLAT1-2f858c62.tiff"
        a = tifffile.imread(dp)
        b = tifffile.imread(fp)
        gains = []
        for (y, x) in content_sites(a):
            ca = a[y:y + CROP, x:x + CROP, :].astype(np.float64)
            cb = b[y:y + CROP, x:x + CROP, :].astype(np.float64)
            ma = float(ca.mean())
            if ma > 1e-9:
                gains.append(float(cb.mean()) / ma)
        if not gains:
            continue
        g = float(np.median(gains))
        blotch, grain = r.get("blotch"), r.get("grain")
        cb_ = blotch / g if blotch is not None else None
        cg_ = grain / g if grain is not None else None
        rows.append(dict(subject=name, gain=g, blotch=blotch, blotch_corr=cb_,
                         grain=grain, grain_corr=cg_, sharp=r.get("sharp")))
        print(f"{name:<38} {g:7.4f} {blotch:8.4f} {cb_:8.4f} "
              f"{grain:8.4f} {cg_:8.4f}")

    def med(k):
        v = [r[k] for r in rows if r[k] is not None and np.isfinite(r[k])]
        return float(np.median(v)) if v else float("nan")

    print(f"\n  n = {len(rows)} subjects")
    print(f"  median FLAT1/DEF gain at the content sites : {med('gain'):.4f}")
    print(f"  median blotch  as reported                 : {med('blotch'):.4f}")
    print(f"  median blotch  gain-corrected              : {med('blotch_corr'):.4f}")
    print(f"  median grain   as reported                 : {med('grain'):.4f}")
    print(f"  median grain   gain-corrected              : {med('grain_corr'):.4f}")
    print(f"  median sharp   (scale-invariant, uncorrected): {med('sharp'):.4f}")

    sh, bl = med("sharp"), med("blotch_corr")
    print(f"\n  EXCHANGE RATE, gain-corrected: {(1 - sh) * 100:.2f}% of struct-band "
          f"sharpness spent\n  to buy {(1 - bl) * 100:.2f}% of mottle-band floor "
          f"= {(1 - sh) / (1 - bl):.2f} units of sharpness per unit of blotch.")
    (OUT / "gainbias.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT / 'gainbias.json'}")


if __name__ == "__main__":
    main()

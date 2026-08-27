"""Is there a broad backdrop pedestal that section 19 proved I could not see?

19 established that arcprofile.py is BLIND to any darkening wider than ~750 px,
because its reference is a radial annulus inside the same image. The open item:
a uniform veiling pedestal across the whole backdrop would read as zero and I
would have called it absent.

This uses an ABSOLUTE, EXTERNAL reference: a single-frame render of the same
subject through the same binary. n=1 has no election and no multi-frame merge,
so it cannot carry a merge-induced pedestal.

The single frame is 7032 px wide and the merged pair is 7040 -- an 8 px (0.11%)
difference from coverage scaling. So NOTHING here differences pixels. Both
statistics are medians over regions of millions of pixels, which an 8 px
boundary shift cannot move:

  A. BORDER  -- a fixed frame of pixels around the image edge. No mask, no
     signed distance, no registration. Unambiguously backdrop in all three.
  B. OWN MASK -- each image's own subject mask and far field. Independent
     construction; agreement between A and B is the check.

Reports DN, per the project rule that an additive bias is invisible in a ratio.
"""
import numpy as np
import ringprofile as rp
import arcprofile as ap

ONE = r"C:\dev\strehl-out\BUILD-ELECT\one-fb-{}.tiff"
BORDER = 300


def main():
    subj = "flower-bud-alone-cpl"
    imgs = {
        "single frame n=1": ONE.format("pyramid"),
        "merged BLEND": ap.FLIP.format(subj, "pyramid"),
        "merged CONTROL": ap.FLIP.format(subj, "estimator"),
    }
    lums = {k: ap.luma(p) for k, p in imgs.items()}

    print("=" * 78)
    print("BACKDROP PEDESTAL -- absolute DN against an EXTERNAL n=1 reference")
    print("=" * 78)
    for k, p in imgs.items():
        print(f"  {k:<18} {str(lums[k].shape):>14}  {p}")
    print(f"  widths differ by {7040 - 7032} px; nothing below differences pixels.\n")

    print(f"A. BORDER -- outer {BORDER} px of the frame. No mask, no registration.")
    A = {}
    for k, v in lums.items():
        m = np.zeros(v.shape, bool)
        m[:BORDER, :] = m[-BORDER:, :] = True
        m[:, :BORDER] = m[:, -BORDER:] = True
        A[k] = float(np.median(v[m]))
        print(f"    {k:<18} {A[k]:>9.0f} DN   ({int(m.sum())/1e6:.1f} Mpx)")

    print(f"\nB. OWN MASK -- each image's own subject mask, far field d>=750 px.")
    B = {}
    for k, v in lums.items():
        mask, thr, _, _ = rp.subject_mask(v)
        sd = rp.signed_distance(mask)
        m = sd >= 750
        B[k] = float(np.median(v[m]))
        print(f"    {k:<18} {B[k]:>9.0f} DN   (mask {mask.mean()*100:5.2f}% of "
              f"frame, thr {thr:.0f} DN, {int(m.sum())/1e6:.1f} Mpx)")

    ref = "single frame n=1"
    print(f"\nDIFFERENCE from the single frame. A pedestal is NEGATIVE: the merge")
    print(f"rendering the backdrop darker than any single frame of the scene was.")
    print(f"    {'':<18} {'A border':>20} {'B own mask':>20}")
    for k in imgs:
        if k == ref:
            continue
        da, db = A[k] - A[ref], B[k] - B[ref]
        print(f"    {k:<18} {da:>+11.0f} DN {100*da/A[ref]:>+6.2f}% "
              f"{db:>+11.0f} DN {100*db/B[ref]:>+6.2f}%")

    print(f"\n  AGREEMENT between the two independent constructions:")
    for k in imgs:
        if k == ref:
            continue
        da, db = A[k] - A[ref], B[k] - B[ref]
        print(f"    {k:<18} A says {da:+.0f} DN, B says {db:+.0f} DN, "
              f"spread {abs(da - db):.0f} DN")
    print(f"\n  Sanity: the two constructions on the REFERENCE itself differ by "
          f"{abs(A[ref] - B[ref]):.0f} DN\n  ({A[ref]:.0f} vs {B[ref]:.0f}) -- "
          f"that is the floor below which no difference above is meaningful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

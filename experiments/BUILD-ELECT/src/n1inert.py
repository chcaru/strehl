"""Is the pyramid path actually inert at n=1? Section 20 assumed it without measuring.

20 used a single-frame pyramid render as an ABSOLUTE reference, on the argued
mechanism that "n=1 has no election, so it cannot carry a merge-induced
pedestal". That is a mechanism explaining why a measurement must hold, which is
the point at which one should measure rather than stop.

The specific worry: the pyramid path contains a hull clamp, which this project
has established is a BASE-OCTAVE PEDESTAL CORRECTION that lifts dark pixels
(p1 +137 DN, p25 +208 DN). If it runs at n=1 as well as at n=205, it is present
in BOTH the reference and the subject of 20's comparison and cancels -- which is
exactly the failure mode 19 documented, one level up.

`argmax-baseline` is an independent path: it does not align, denoise,
regularise, or blend, and it never enters the Laplacian pyramid at all. Same
frame, same binary, full resolution both.

The pyramid n=1 render applied 0.9974 coverage scaling and argmax does not align
at all, so the two are NOT pixel-registered. Nothing here differences pixels;
both statistics are medians over 6-16 Mpx regions.
"""
import numpy as np
import ringprofile as rp
import arcprofile as ap

O = r"C:\dev\strehl-out\BUILD-ELECT\one-fb-{}.tiff"
BORDER = 300


def stats(v):
    m = np.zeros(v.shape, bool)
    m[:BORDER, :] = m[-BORDER:, :] = True
    m[:, :BORDER] = m[:, -BORDER:] = True
    border = float(np.median(v[m]))
    mask, thr, _, _ = rp.subject_mask(v)
    sd = rp.signed_distance(mask)
    far = float(np.median(v[sd >= 750]))
    dark = float(np.percentile(v[m], 1))
    return border, far, dark, mask.mean() * 100, thr


def main():
    subj = "flower-bud-alone-cpl"
    imgs = {
        "n=1 argmax (NO pyramid)": O.format("argmax"),
        "n=1 pyramid": O.format("pyramid"),
        "n=205 merged BLEND": ap.FLIP.format(subj, "pyramid"),
    }
    print("=" * 78)
    print("IS THE PYRAMID PATH INERT AT n=1?  -- testing section 20's assumption")
    print("=" * 78)
    print(f"  {'':<26} {'border DN':>10} {'far field':>10} {'p1 dark':>9} "
          f"{'mask %':>7} {'thr DN':>8}")
    r = {}
    for k, p in imgs.items():
        v = ap.luma(p)
        r[k] = stats(v)
        print(f"  {k:<26} {r[k][0]:>10.0f} {r[k][1]:>10.0f} {r[k][2]:>9.0f} "
              f"{r[k][3]:>6.2f}% {r[k][4]:>8.0f}")

    a = "n=1 argmax (NO pyramid)"
    p = "n=1 pyramid"
    print()
    print(f"  THE TEST -- same single frame, two independent code paths:")
    for i, lab in enumerate(("border", "far field", "p1 dark")):
        d = r[p][i] - r[a][i]
        print(f"    {lab:<12} pyramid - argmax = {d:>+8.0f} DN "
              f"({100.0*d/r[a][i]:>+6.2f}%)")

    print()
    print(f"  20's floor was 681 DN (the spread between its two constructions).")
    worst = max(abs(r[p][i] - r[a][i]) for i in range(3))
    if worst < 681:
        print(f"    Worst channel here: {worst:.0f} DN, BELOW that floor.")
        print(f"    -> the pyramid path adds no level shift at n=1 that 20 could")
        print(f"       have been blind to. 20's reference is clean and 20 STANDS.")
    else:
        print(f"    Worst channel here: {worst:.0f} DN, ABOVE that floor.")
        print(f"    -> the pyramid path DOES shift levels at n=1. It is present in")
        print(f"       both sides of 20's comparison and cancels. 20's null is")
        print(f"       CONTAMINATED and must be withdrawn.")

    print()
    print(f"  Control that this comparison can see anything at all: the p1 dark")
    print(f"  percentile is the channel a hull clamp would move most, and the")
    print(f"  three images span {min(x[2] for x in r.values()):.0f}-"
          f"{max(x[2] for x in r.values()):.0f} DN there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

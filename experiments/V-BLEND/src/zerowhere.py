"""Where are the zeros, and what does the other arm read there?

Tests four rival explanations for a population of exactly-zero pixels:
  packaging/border   -> they hug the frame edge
  thin edge ringing  -> they are isolated pixels beside very bright ones
  genuinely black    -> all three channels are ~0 and the other arm agrees
  a channel clamp    -> one channel pinned while the others carry real signal
                        and the other arm reads a substantial value there
"""
import sys
import numpy as np
import tifffile

CH = ("R", "G", "B")


def main(after_path, before_path, band=8):
    a = tifffile.imread(after_path)
    assert a.dtype == np.uint16 and a.ndim == 3
    h, w, _ = a.shape
    n = h * w
    print(f"AFTER  {after_path}")
    print(f"BEFORE {before_path}")
    print(f"shape {h}x{w}  n={n:,}\n")

    zero = {c: (a[:, :, i] == 0) for i, c in enumerate(CH)}

    print("1. CO-OCCURRENCE ACROSS CHANNELS (a genuinely black pixel is black in all three)")
    zr, zg, zb = zero["R"], zero["G"], zero["B"]
    allz = zr & zg & zb
    print(f"   zeros: R={zr.sum():,}  G={zg.sum():,}  B={zb.sum():,}")
    print(f"   all three zero simultaneously: {allz.sum():,} "
          f"({allz.sum()/max(zb.sum(),1)*100:.2f}% of the blue zeros)")
    for c in ("R", "G"):
        both = (zero[c] & zb).sum()
        print(f"   {c} zero AND B zero: {both:,} ({both/max(zb.sum(),1)*100:.2f}% of blue zeros)")
    print("   -> at the BLUE zero sites, the other channels read:")
    for i, c in enumerate(CH):
        v = a[:, :, i][zb]
        print(f"      {c}: median {np.median(v):,.0f} DN   p90 {np.percentile(v, 90):,.0f} DN   "
              f"frac==0 {np.mean(v == 0)*100:.2f}%")

    print("\n2. BORDER TEST (packaging artifacts hug the frame edge)")
    edge = np.zeros((h, w), bool)
    edge[:band, :] = edge[-band:, :] = True
    edge[:, :band] = edge[:, -band:] = True
    print(f"   border band of {band} px = {edge.sum():,} px ({edge.sum()/n*100:.3f}% of frame)")
    for c in CH:
        z = zero[c]
        if z.sum() == 0:
            continue
        onb = (z & edge).sum()
        print(f"   {c}: {onb:,} of {z.sum():,} zeros on the border "
              f"({onb/z.sum()*100:.3f}%); if uniform we would expect {edge.sum()/n*100:.3f}%")

    print("\n3. NEIGHBOUR TEST (thin ringing sits next to something bright)")
    for c in ("B",):
        z = zero[c]
        i = CH.index(c)
        ch = a[:, :, i]
        nb = np.zeros((h, w), np.uint16)
        nb[1:, :] = np.maximum(nb[1:, :], ch[:-1, :])
        nb[:-1, :] = np.maximum(nb[:-1, :], ch[1:, :])
        nb[:, 1:] = np.maximum(nb[:, 1:], ch[:, :-1])
        nb[:, :-1] = np.maximum(nb[:, :-1], ch[:, 1:])
        v = nb[z]
        print(f"   {c}: brightest 4-neighbour of a zero pixel -- "
              f"median {np.median(v):,.1f}  p90 {np.percentile(v,90):,.0f}  "
              f"p99 {np.percentile(v,99):,.0f}")
        print(f"      fraction of zeros with ANY neighbour > 4000 DN: {np.mean(v > 4000)*100:.3f}%")
        print(f"      fraction whose brightest neighbour is itself 0: {np.mean(v == 0)*100:.2f}%")
        del nb, v

    del a
    b = tifffile.imread(before_path)
    print("\n4. WHAT THE BEFORE ARM READS AT THOSE EXACT LOCATIONS")
    for c in CH:
        z = zero[c]
        if z.sum() == 0:
            continue
        i = CH.index(c)
        v = b[:, :, i][z]
        print(f"   {c} ({z.sum():,} sites): BEFORE median {np.median(v):,.0f} DN  "
              f"p10 {np.percentile(v,10):,.0f}  p90 {np.percentile(v,90):,.0f}  "
              f"frac BEFORE==0 {np.mean(v == 0)*100:.3f}%")
    print("\n   (a genuinely black scene region would read ~0 in BOTH arms)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

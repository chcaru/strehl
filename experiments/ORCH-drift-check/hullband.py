"""Where in frequency does the hull clamp actually act?

My Laplacian high-pass says the clamp retains 98.8% of fine detail, yet the
side-by-side crop shows an obvious difference. Both cannot be about the same
band. This splits the clamped-minus-unclamped difference by spatial scale,
which decides what the clamp really is:

  - difference concentrated at LOW frequency  -> the clamp is shifting TONE,
    and "microcontrast retained" numbers measured without a tone control are
    measuring brightness, not detail.
  - difference concentrated at HIGH frequency -> the clamp is removing edge
    acutance, i.e. real sharpening the Laplacian merge produced.

Green plane, linear DN, one binary, no tone curve. Gaussian pyramid by
repeated 2x box decimation: crude, but each level's band is unambiguous and
nothing here depends on filter shape.
"""
import sys
import numpy as np
import tifffile

CL = r"C:\dev\strehl-out\BUILD-HULL\accept\coffee-bean--clamped.tiff"
UN = r"C:\dev\strehl-out\BUILD-HULL\accept\coffee-bean--unclamped.tiff"


def decimate(a):
    h, w = a.shape
    a = a[: h // 2 * 2, : w // 2 * 2]
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def upsample(a, shape):
    out = np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)
    return out[: shape[0], : shape[1]]


def bands(g, levels=6):
    """Laplacian-style band decomposition; returns list fine -> coarse, plus residual."""
    out = []
    cur = g
    for _ in range(levels):
        h, w = cur.shape
        cur = cur[: h // 2 * 2, : w // 2 * 2]      # crop to even BEFORE differencing
        small = decimate(cur)
        out.append(cur - upsample(small, cur.shape))
        cur = small
    return out, cur


def main():
    cl = tifffile.imread(CL)[:, :, 1].astype(np.float64)
    un = tifffile.imread(UN)[:, :, 1].astype(np.float64)
    print(f"shape {cl.shape}")

    print(f"\nMEANS   clamped {cl.mean():10.2f} DN   unclamped {un.mean():10.2f} DN   "
          f"delta {cl.mean() - un.mean():+.2f} DN")
    print(f"MEDIAN  clamped {np.median(cl):10.2f} DN   unclamped {np.median(un):10.2f} DN")
    for p in (1, 25, 50, 75, 99, 99.9):
        a, b = np.percentile(cl, p), np.percentile(un, p)
        print(f"  p{p:<5} clamped {a:9.1f}   unclamped {b:9.1f}   delta {a-b:+9.1f} DN")

    bc, rc = bands(cl)
    bu, ru = bands(un)

    print("\nENERGY BY BAND (RMS, linear DN, green)")
    print(f"{'band':>6} {'period(px)':>11} {'clamped':>11} {'unclamped':>11} "
          f"{'retained':>10} {'RMS of diff':>12}")
    tot_d2 = 0.0
    rows = []
    for i, (a, b) in enumerate(zip(bc, bu)):
        ra = float(np.sqrt((a ** 2).mean()))
        rb = float(np.sqrt((b ** 2).mean()))
        rd = float(np.sqrt(((a - b) ** 2).mean()))
        # every band is at its own resolution; weight by pixel count for the share
        w = a.size
        tot_d2 += rd * rd * w
        rows.append((i, 2 ** (i + 1), ra, rb, rd, w))
    rd_res = float(np.sqrt(((rc - ru) ** 2).mean()))
    tot_d2 += rd_res * rd_res * rc.size

    for i, per, ra, rb, rd, w in rows:
        share = 100.0 * (rd * rd * w) / tot_d2
        print(f"{i:>6} {per:>11} {ra:>11.2f} {rb:>11.2f} "
              f"{100.0 * ra / rb if rb else float('nan'):>9.2f}% {rd:>12.2f}   "
              f"share of total change {share:5.1f}%")
    share = 100.0 * (rd_res * rd_res * rc.size) / tot_d2
    print(f"{'resid':>6} {'>128':>11} {float(np.sqrt((rc**2).mean())):>11.2f} "
          f"{float(np.sqrt((ru**2).mean())):>11.2f} "
          f"{100.0 * np.sqrt((rc**2).mean()) / np.sqrt((ru**2).mean()):>9.2f}% "
          f"{rd_res:>12.2f}   share of total change {share:5.1f}%")

    fine = sum(r[4] ** 2 * r[5] for r in rows[:2])
    coarse = tot_d2 - fine
    print(f"\nSPLIT: bands 0-1 (2-4 px detail) carry {100.0*fine/tot_d2:.1f}% of the change; "
          f"everything coarser carries {100.0*coarse/tot_d2:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

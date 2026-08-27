"""Blotch detector: mid-scale structure in smooth regions that noise cannot explain.

§97's adversarial sweep is powerful against edge overshoot and blind to everything else. The
classic non-edge failure of a focus stacker is blotching -- in a smooth, low-texture region
the focus measure has no signal, the winner field goes arbitrary, and the merge stitches a
patchwork whose seams are invisible as edges but plainly visible as mottling.

Statistic: in the flattest region of the frame, band-pass at 50-400 px (blotch scale) and
divide by the high-frequency residual (the noise the sensor actually delivered). Pure noise
gives a fixed ratio, measured here rather than assumed. Real blotching raises mid-scale
power without raising the noise, so the ratio climbs.

The trap this design is built against is §96's: a high reading has an innocent explanation,
and here it is defocused background structure -- genuine bokeh is smooth, mid-scale and
exactly what this statistic responds to. So ARM SOURCE measures the same region of a decoded
source frame. Structure present there is the subject's; only an excess over it is the
merge's.
"""
import pathlib
import sys

import numpy as np
import rawpy
import tifffile

SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
RAW = pathlib.Path(r"D:\personal\macro")
WIN = 900
LO_R = 50
HI_R = 400
NOISE_R = 3


def boxblur(a, r):
    if r < 1:
        return a.copy()
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)), mode="constant")
    k = 2 * r + 1
    s = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])
    return (s / (k * k)).astype(np.float32)


def flattest(lum, win=WIN):
    """Lowest-texture window; blotching is only legible where the subject is not."""
    s = 8
    d = lum[::s, ::s]
    g = np.abs(np.diff(d, axis=0)[:, :-1]) + np.abs(np.diff(d, axis=1)[:-1, :])
    w = max(1, win // s)
    e = boxblur(g.astype(np.float32), w // 2)
    m = w // 2 + 2
    e[:m, :] = np.inf
    e[-m:, :] = np.inf
    e[:, :m] = np.inf
    e[:, -m:] = np.inf
    iy, ix = np.unravel_index(np.argmin(e), e.shape)
    y = int(np.clip(iy * s - win // 2, 0, lum.shape[0] - win))
    x = int(np.clip(ix * s - win // 2, 0, lum.shape[1] - win))
    return y, x


def blotch_ratio(blk):
    """Mid-scale structure as a CONTRAST, plus the two raw terms.

    Returns (contrast, band_dn, noise_dn, mean_dn). Contrast = band/mean is invariant to
    the tone scaling the pipeline applies (masters run 4.7-6.4x brighter than a rawpy
    decode with no_auto_bright), so it is the only one of these safe to compare between a
    master and a source frame. Comparing band_dn directly indicts the merge for being
    brighter; dividing band by NOISE indicts it for being quieter. Both were measured.
    """
    lo = boxblur(blk, LO_R // 2)
    hi = boxblur(blk, HI_R // 2)
    band = lo - hi
    noise = blk - boxblur(blk, NOISE_R)
    m = float(np.mean(blk))
    nr = float(np.std(noise))
    bd = float(np.std(band))
    if m <= 0:
        return float("nan"), bd, nr, m
    return bd / m, bd, nr, m


def lum_of(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2]).astype(np.float32)


def commission(rng):
    print("COMMISSIONING")
    n = np.zeros((WIN, WIN), np.float32)
    base = 8000.0
    noise = rng.normal(0, 40, (WIN, WIN)).astype(np.float32)
    r0, _, _, _ = blotch_ratio(base + noise)
    print(f"  ARM NULL   pure noise, no blotch        ratio {r0:8.4f}")

    print("  ARM SYNTH  planted blotch field, amplitude ladder in units of noise sigma")
    coarse = rng.normal(0, 1, (WIN // 64 + 2, WIN // 64 + 2)).astype(np.float32)
    yy = np.linspace(0, coarse.shape[0] - 1, WIN)
    xx = np.linspace(0, coarse.shape[1] - 1, WIN)
    gi = np.clip(yy.astype(int), 0, coarse.shape[0] - 2)
    gj = np.clip(xx.astype(int), 0, coarse.shape[1] - 2)
    fy = (yy - gi)[:, None]
    fx = (xx - gj)[None, :]
    c = coarse[np.ix_(gi, gj)]
    blot = (c * (1 - fy) * (1 - fx) + coarse[np.ix_(gi + 1, gj)] * fy * (1 - fx)
            + coarse[np.ix_(gi, gj + 1)] * (1 - fy) * fx
            + coarse[np.ix_(gi + 1, gj + 1)] * fy * fx).astype(np.float32)
    blot /= max(float(np.std(blot)), 1e-6)
    ok = True
    prev = r0
    for amp in (0.25, 0.5, 1.0, 2.0, 4.0):
        r, _, _, _ = blotch_ratio(base + noise + blot * amp * 40.0)
        mono = r > prev
        print(f"    amp {amp:5.2f} sigma   ratio {r:8.4f}   rises {mono}")
        ok = ok and mono
        prev = r
    print(f"  {'COMMISSIONED' if ok else 'NOT COMMISSIONED'}: "
          f"monotone in blotch amplitude, null floor {r0:.4f}")
    print(f"  n unused {n.size}")
    return r0, ok


def main(argv):
    rng = np.random.default_rng(11)
    floor, ok = commission(rng)
    if not ok:
        print("commissioning failed; refusing to report")
        return 1

    want = argv if argv else None
    paths = [p for p in sorted(SHIP.iterdir()) if p.suffix.lower() == ".tiff"]
    if want:
        paths = [p for p in paths if any(w in p.stem for w in want)]

    print(f"\nARM MASTER  flattest {WIN}x{WIN} window, band {LO_R}-{HI_R} px")
    print(f"{'master':40s} {'contrast':>9s} {'vs floor':>9s} {'band DN':>9s} "
          f"{'noise DN':>9s} {'mean DN':>9s} {'x':>6s} {'y':>6s}")
    rows = []
    bands = {}
    for p in paths:
        a = tifffile.imread(str(p))
        lum = lum_of(a[:, :, :3])
        del a
        y, x = flattest(lum)
        r, bd, nd, md = blotch_ratio(lum[y:y + WIN, x:x + WIN])
        del lum
        nm = p.stem.replace("--SHIP-V2", "")
        rows.append((nm, r, y, x))
        bands[nm] = (bd, nd, md)
        print(f"{nm:40s} {r:9.5f} {r / floor:9.2f} {bd:9.1f} {nd:9.1f} {md:9.1f} "
              f"{x:6d} {y:6d}")

    rows.sort(key=lambda t: -t[1])
    print(f"\nworst three by ratio: " + ", ".join(f"{n} {v:.2f}" for n, v, _, _ in rows[:3]))

    print("\nARM SOURCE  the control: same statistic on decoded source frames")
    print("            structure present here is the subject's, not the merge's")
    for nm, r, y, x in rows[:3]:
        d = RAW / nm
        if not d.is_dir():
            print(f"  {nm:38s} no source directory at {d}")
            continue
        raws = sorted(q for q in d.iterdir() if q.suffix.lower() == ".arw")
        if not raws:
            print(f"  {nm:38s} no .arw frames")
            continue
        vals = []
        for i in (0, len(raws) // 2, len(raws) - 1):
            with rawpy.imread(str(raws[i])) as rr:
                rgb = rr.postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16,
                                     use_camera_wb=True)
            sl = lum_of(rgb)
            del rgb
            if sl.shape[0] < y + WIN or sl.shape[1] < x + WIN:
                continue
            sr, sb, sn, sm = blotch_ratio(sl[y:y + WIN, x:x + WIN])
            del sl
            vals.append((sr, sb, sn, sm))
        if not vals:
            print(f"  {nm:38s} no usable source window")
            continue
        mx = max(v[0] for v in vals)
        sb_mx = max(v[1] for v in vals)
        sn_med = float(np.median([v[2] for v in vals]))
        sm_med = float(np.median([v[3] for v in vals]))
        mb, mn, md = bands[nm]
        print(f"  {nm}")
        print(f"    mean DN   master {md:8.1f}  source med {sm_med:8.1f}  "
              f"({md / max(sm_med, 1e-9):.2f}x brighter -- the pipeline tone-scales)")
        print(f"    band DN   master {mb:8.1f}  source max {sb_mx:8.1f}  "
              f"({mb / max(sb_mx, 1e-9):.2f}x)  raw, NOT comparable")
        print(f"    noise DN  master {mn:8.1f}  source med {sn_med:8.1f}  "
              f"({mn / max(sn_med, 1e-9):.2f}x)  raw, NOT comparable")
        print(f"    CONTRAST  master {r:8.5f}  source max {mx:8.5f}  "
              f"({r / max(mx, 1e-9):.2f}x)  <-- tone-invariant, the one that counts")
        if r <= 1.3 * mx:
            print(f"    VERDICT  mid-scale contrast is NOT elevated ({r / max(mx, 1e-9):.2f}x).")
            print( "             NOT a blotch defect.")
        else:
            print(f"    VERDICT  mid-scale contrast elevated {r / mx:.2f}x beyond any "
                  f"source frame --")
            print( "             structure no input contains. A genuine merge defect.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""ORCH's bud rim, take 4: chroma profiled against DISTANCE FROM THE SILHOUETTE.

Takes 1-3 all failed on the same thing -- picking a SITE. Take 1 picked it by
argmax on one arm (biased to that arm). Take 2 walked a fixed column down a
curved boundary (mostly sampled empty sky). Take 3 zeroed its own search mask
and read the tile corner, then, once fixed, found the sharpest single-pixel
gradient in the tile and it was DARK TEXTURE -- green 2763 vs 2573 across it,
a 190 DN step, no silhouette. A |grad| maximum finds texture, not an edge
between two regions.

So stop picking sites. The boundary is a CURVE and the right coordinate is
distance from it.

`ringprofile.subject_mask` + `signed_distance` already exist in this lane and
are the machinery 17 and 20 used. `signed_distance` returns d_out - d_in, so d
is POSITIVE OUTWARD (into the backdrop) and NEGATIVE inside the subject. Profile
R-G against d and the whole silhouette contributes to every bin.

This answers ORCH's dilution failure properly rather than dodging it. They
averaged R-G over the boundary and it vanished; the rim is a FEW PIXELS WIDE and
sits at one particular d, so averaging across d is what destroyed it. Resolving
by d puts every rim pixel in the same bin. A p90 is reported beside the median
so that a rim confined to part of the silhouette also survives.

  * ONE mask and ONE distance field, computed on the reference arm and reused
    for every arm after registration. Letting each arm compute its own mask
    would let the arms disagree about where the boundary is, which is a
    difference in the mask masquerading as a difference in the rim -- the exact
    error 17 was retracted for.
  * B-G is profiled beside R-G as a SHAPE CONTROL. ORCH measured the rim
    red-dominant with B BELOW G. If R-G peaks and B-G dips at the same d, that
    is a channel-differential signature; if both move together it is a
    luminance artifact and not chromatic at all.
  * 1 px bins, because the rim is 1-3 px wide and any coarser bin smears the
    thing being measured. That is the property governing whether this check can
    see anything, so it is stated and it is not varied silently.

PRE-REGISTERED (unchanged since take 1):
  overshoot survives at n=1              -> election hypothesis DEAD
  overshoot collapses under --fix-ca off -> cause is the CA resample
  survives both                          -> neither; cause is downstream
  gone at n=1, present with --fix-ca off -> ORCH is right, it is the election
"""
import os
import numpy as np
import tifffile
import ringprofile as rp

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
DMIN, DMAX = -40, 40
REGWIN = 1024

ARMS = [
    ("n=205 DEFAULT (election + CA)", "fb-noflags.tiff"),
    ("n=205 --fix-ca off (election, NO CA)", "fb-caoff.tiff"),
    ("n=1 pyramid  (NO election)", "one-fb-pyramid.tiff"),
    ("n=1 argmax   (NO election, no pyramid)", "one-fb-argmax.tiff"),
]
REF = "fb-noflags.tiff"


def load(name):
    a = tifffile.imread(os.path.join(OUT, name))
    assert a.dtype == np.uint16, f"{name}: expected uint16, got {a.dtype}"
    return a[:, :, :3]


def phase_shift(gref, gmov):
    h, w = gref.shape
    cy, cx, r = h // 2, w // 2, REGWIN // 2
    a = gref[cy - r:cy + r, cx - r:cx + r].astype(np.float64)
    b = gmov[cy - r:cy + r, cx - r:cx + r].astype(np.float64)
    a, b = a - a.mean(), b - b.mean()
    win = np.hanning(REGWIN)[:, None] * np.hanning(REGWIN)[None, :]
    A, B = np.fft.rfft2(a * win), np.fft.rfft2(b * win)
    R = A * np.conj(B)
    m = np.abs(R)
    R = np.where(m > 0, R / np.maximum(m, 1e-12), 0)
    c = np.fft.irfft2(R, s=(REGWIN, REGWIN))
    dy, dx = np.unravel_index(int(np.argmax(c)), c.shape)
    dy = dy - REGWIN if dy > REGWIN // 2 else dy
    dx = dx - REGWIN if dx > REGWIN // 2 else dx
    a2 = gref[cy - r:cy + r, cx - r:cx + r].astype(np.float64)
    b2 = gmov[cy - r + dy:cy + r + dy, cx - r + dx:cx + r + dx].astype(np.float64)
    a2, b2 = a2 - a2.mean(), b2 - b2.mean()
    ncc = float((a2 * b2).sum() /
                (np.sqrt((a2 * a2).sum()) * np.sqrt((b2 * b2).sum())))
    return int(dy), int(dx), ncc


def profile(ch, dq, bins):
    med = np.full(len(bins), np.nan)
    p90 = np.full(len(bins), np.nan)
    for i, d in enumerate(bins):
        sel = dq == d
        n = int(sel.sum())
        if n >= 500:
            v = ch[sel]
            med[i], p90[i] = np.median(v), np.percentile(v, 90)
    return med, p90


def main():
    print("=" * 78)
    print("BUD RIM vs DISTANCE FROM SILHOUETTE -- election or lateral CA?")
    print("=" * 78)
    ref = load(REF)
    gref = ref[:, :, 1]
    lum = ref.astype(np.float64).mean(2)
    mask, thr, _, _ = rp.subject_mask(lum)
    sd = rp.signed_distance(mask)
    print(f"  mask {100 * mask.mean():.2f}% of frame, threshold {thr:.0f} DN; "
          f"d is POSITIVE OUTWARD")
    bins = np.arange(DMIN, DMAX + 1)
    dq = np.round(sd).astype(np.int32)
    npx = [int((dq == d).sum()) for d in bins]
    print(f"  boundary shell d in [{DMIN},{DMAX}]: "
          f"{min(npx)}-{max(npx)} px per 1 px bin")
    del lum

    res = {}
    print()
    print(f"  {'arm':<40} {'dy':>4} {'dx':>4} {'ncc':>6} {'R-G peak':>9} "
          f"{'at d':>5} {'ends':>7} {'OVER':>7}")
    for name, fn in ARMS:
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            print(f"  {name:<40} MISSING -- skipped, NOT a pass")
            continue
        a = ref if fn == REF else load(fn)
        if fn == REF:
            dy = dx = 0
            ncc = 1.0
        else:
            dy, dx, ncc = phase_shift(gref, a[:, :, 1])
        a = np.roll(np.roll(a, -dy, axis=0), -dx, axis=1)
        rg = (a[:, :, 0].astype(np.float64) - a[:, :, 1])
        bg = (a[:, :, 2].astype(np.float64) - a[:, :, 1])
        rmed, rp90 = profile(rg, dq, bins)
        bmed, bp90 = profile(bg, dq, bins)
        ends = max(rmed[0], rmed[-1])
        k = int(np.nanargmax(rmed))
        over = rmed[k] - ends
        res[name] = (rmed, rp90, bmed, bp90, over, bins[k], ncc)
        print(f"  {name:<40} {dy:>4} {dx:>4} {ncc:>6.3f} {rmed[k]:>9.0f} "
              f"{bins[k]:>5} {ends:>7.0f} {over:>7.0f}")
        if fn != REF:
            del a
        del rg, bg

    print()
    print("  R-G MEDIAN vs d (linear DN). d<0 inside bud, d>0 backdrop.")
    show = [d for d in range(-20, 21, 2)]
    print(f"    {'d =':<40}" + "".join(f"{d:>6}" for d in show))
    for name, (rmed, _, _, _, _, _, _) in res.items():
        s = "".join(f"{rmed[list(bins).index(d)]:>6.0f}" for d in show)
        print(f"    {name:<40}{s}")
    print()
    print("  B-G MEDIAN vs d -- SHAPE CONTROL. Must DIP where R-G peaks if the")
    print("  rim is channel-differential; must track R-G if it is luminance.")
    for name, (_, _, bmed, _, _, _, _) in res.items():
        s = "".join(f"{bmed[list(bins).index(d)]:>6.0f}" for d in show)
        print(f"    {name:<40}{s}")

    print()
    print("  VERDICT")
    for name, (_, _, _, _, over, at, ncc) in res.items():
        q = "  UNRELIABLE registration" if ncc < 0.90 else ""
        print(f"    {name:<40} overshoot {over:+7.0f} DN at d={at:+d}{q}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

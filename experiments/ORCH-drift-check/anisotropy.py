"""ORCH: radial-vs-tangential high-frequency anisotropy of a rendered stack.

WHY THIS EXISTS
---------------
Fact 1271: the alignment solve applies 50.2% of the drift, leaving ~150 plane px
of residual misregistration on bee-3-cpl. M103 is fixing it. When M103 lands I
need to prove the render got better, and I do not currently have any instrument
that can say so -- the gallery and the gate strips have only ever been eyeballed,
and M87 (facts 1275-1278) just demonstrated that a metric and the eye can
disagree with the eye being right. A claim of improvement backed by looking at it
is not a measurement (rule 12).

THE IDEA
--------
A residual *scale* error is radial by construction: frame k is a scaled copy of
the reference, so every feature slides along its own radius, by an amount
proportional to that radius. When the merge gathers from misregistered frames,
the resulting smear is therefore:

  (a) oriented ALONG the local radial direction, and
  (b) zero at the image centre, growing with radius.

Both properties are signatures, not just symptoms. Isotropic softness -- from
diffraction, defocus, the noise gate, demosaic, or a soft subject -- has neither.
So the instrument measures orientation, not sharpness:

  A(r) = P(k parallel to radial) / P(k parallel to tangential)   in a high band

A blur along a direction attenuates the frequencies whose wavevector lies along
that direction, so radial smear drives A below 1. Under a correct solve, and for
a subject with no preferred radial orientation, A(r) == 1 at every radius.

WHAT MAKES IT TRUSTWORTHY
-------------------------
1. A BUILT-IN NULL AT r=0. At the centre "radial" is undefined and the geometry
   forbids any scale-induced displacement. A(0) must read 1 whatever the subject
   is. If the instrument reports a centre anomaly it is measuring the subject or
   itself, not the defect, and the run is void.
2. SPECIFICITY, NOT JUST SENSITIVITY. Discipline: a null shows the instrument is
   quiet, only a planted effect shows it can respond at all -- but an instrument
   that responds to *everything* is equally useless. So there are three plants:
   radial smear (must fire), isotropic blur of matched strength (must NOT fire),
   and identity (must not fire). Sensitivity and specificity are both bars.
3. SUBJECT ANISOTROPY IS THE OBVIOUS CONFOUND and it is measured, not assumed.
   The tweezers' striations are horizontal: at tiles due left/right of centre
   those striations are radial, at tiles above/below they are tangential. Angular
   averaging over a full annulus cancels that to first order, but "to first
   order" is an argument, so the per-annulus angular spread is reported and a
   subject-dominated annulus is flagged rather than silently averaged.

PRE-REGISTERED PREDICTIONS (written before M103's fix exists, and before any
number below has been computed -- these are falsifiable, and I expect at least
one to die):

  P1  On the CURRENT bee-3-cpl render, A(r) falls monotonically with radius.
      This is the residual misregistration made visible. If A(r) is flat, then
      either the residual does not reach the render or this instrument cannot
      see it, and in both cases I must not claim M103 improved anything on the
      strength of it.

  P2  A(r) falls FASTER at higher gate. Gate 0 elects a single frame per pixel,
      so a misregistered frame displaces detail but does not smear it; gate 8
      averages many frames whose displacements differ, which does smear. This is
      a genuine prediction that could easily be wrong (if the elected frames at
      one pixel are all near the same index, their displacements are nearly
      equal and averaging them smears very little).

  P3  After M103's fix, A(r) rises toward 1 at large r and is UNCHANGED at r=0.
      The unchanged centre is the important half: it is what distinguishes a
      real alignment improvement from a global sharpening of the whole frame.

USAGE
  python anisotropy.py <render.tif> [more.tif ...]        measure
  python anisotropy.py --controls <render.tif>            sensitivity/specificity
"""

import json
import os
import sys

import numpy as np

# --- geometry / band constants -------------------------------------------------
# A tile must be big enough to resolve the band and small enough that its own
# radial direction is well defined. 128 px subtends ~1.9 deg of angle at the
# corner radius of a 7032x4688 render, so the "radial direction" is unambiguous
# within a tile.
TILE = 128
STRIDE = 128

# The band is chosen ABOVE the scales where defocus and diffraction live and
# BELOW the demosaic/Nyquist corner where CFA reconstruction invents structure.
# In cycles/px: 0.5 is Nyquist. M5's diffraction cutoff and the demosaic corner
# are the two things I do not want in the numerator.
BAND_LO = 0.20
BAND_HI = 0.40

# Half-angle of the wedge, in degrees, around the radial and tangential axes.
WEDGE_DEG = 30.0

# Annuli are defined on normalised radius (1.0 = half-diagonal).
N_ANNULI = 10

# A tile with no texture cannot report an orientation. Tiles whose in-band power
# is below this quantile of the frame are dropped rather than averaged in as
# noise-orientation.
MIN_POWER_Q = 0.35


def load_luma(path):
    """Read a 16-bit RGB TIFF and return float32 luma, without any resampling."""
    try:
        import tifffile
    except ImportError:
        sys.exit("need tifffile: python -m pip install tifffile")
    a = tifffile.imread(path)
    if a.ndim == 3 and a.shape[2] >= 3:
        # Rec.709 luma. The exact coefficients do not matter for a power RATIO,
        # but a fixed choice keeps runs comparable.
        y = (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2])
    else:
        y = a.astype(np.float64)
    return np.ascontiguousarray(y.astype(np.float32))


# Number of |k| rings the band is split into. The ratio is formed WITHIN a ring
# and only then averaged across rings -- see tile_anisotropy for why this is the
# difference between an instrument that works and one that does not.
N_RINGS = 8


def _wedge_masks():
    """Frequency-plane geometry, in TILE-local coordinates.

    Returns (fy, fx) grids in cycles/px, the in-band mask, and a per-bin ring
    index so the radial/tangential ratio can be formed at MATCHED |k|.
    """
    f = np.fft.fftfreq(TILE)
    fy = f[:, None] * np.ones((1, TILE))
    fx = np.ones((TILE, 1)) * f[None, :]
    fr = np.sqrt(fy ** 2 + fx ** 2)
    band = (fr >= BAND_LO) & (fr <= BAND_HI)
    ring = np.full(fr.shape, -1, dtype=np.int32)
    edges = np.linspace(BAND_LO, BAND_HI, N_RINGS + 1)
    for i in range(N_RINGS):
        ring[band & (fr >= edges[i]) & (fr < edges[i + 1])] = i
    return fy, fx, band, ring


_FY, _FX, _BAND, _RING = _wedge_masks()
_WIN = np.outer(np.hanning(TILE), np.hanning(TILE)).astype(np.float32)
_FR = np.sqrt(_FY ** 2 + _FX ** 2)


def tile_anisotropy(tile, ry, rx):
    """Per-|k|-ring radial and tangential power for one tile.

    (ry, rx) is the unit vector from the image centre to the tile centre.
    Returns (p_radial[N_RINGS], p_tangential[N_RINGS], p_band_total).

    A displacement along a direction d attenuates the frequency components whose
    WAVEVECTOR is parallel to d. So the radial-smear signature is a deficit in
    the wedge around k parallel to (ry, rx).

    WHY PER-RING, AND NOT A SINGLE BAND MEAN. The first version of this function
    averaged power over the whole band and took one ratio. Its specificity
    control failed hard: a planted ISOTROPIC blur, which by definition cannot
    prefer a direction, moved A from 0.527 to 0.307. The reason is that a band
    mean does not hold |k| fixed between the two wedges -- this subject puts its
    radial and tangential power at different |k| WITHIN the band, so an isotropic
    transfer function |H(|k|)| weights the two wedge means differently and the
    ratio moves. Forming the ratio inside a ring and averaging afterwards makes
    the cancellation exact: |H| is constant on a ring, so it divides out
    identically from numerator and denominator whatever the subject does.
    """
    t = tile - tile.mean()
    if not np.isfinite(t).all():
        return None
    p = np.abs(np.fft.fft2(t * _WIN)) ** 2

    with np.errstate(invalid="ignore", divide="ignore"):
        cos = (_FY * ry + _FX * rx) / _FR
    cos = np.nan_to_num(cos)
    c = np.cos(np.deg2rad(WEDGE_DEG))
    rad_w = np.abs(cos) >= c
    tan_w = np.abs(cos) <= np.sin(np.deg2rad(WEDGE_DEG))

    pr = np.zeros(N_RINGS)
    pt = np.zeros(N_RINGS)
    for i in range(N_RINGS):
        m = _RING == i
        a, b = m & rad_w, m & tan_w
        if a.sum() == 0 or b.sum() == 0:
            return None
        pr[i] = p[a].mean()
        pt[i] = p[b].mean()
    return pr, pt, float(p[_BAND].mean())


def measure(y, label="", tile_keys=None):
    """A(r) over annuli, with the per-annulus angular spread that detects a
    subject-dominated annulus.

    tile_keys: if given, the exact set of (ty, tx) tiles to use. Passing the set
    chosen on the UNMODIFIED frame is what makes the control arms paired.

    WHY THIS ARGUMENT EXISTS. The first version re-derived the texture threshold
    inside each arm. A planted radial smear destroys power in exactly the outer
    tiles it acts on hardest, so those tiles fell below the per-arm quantile and
    were dropped -- leaving a survivor set enriched for tiles the plant had
    failed to affect. The sensitivity control consequently read 0.5268 -> 0.5294
    for a 150 px smear that should have flattened the outer annuli. The
    selection must not be allowed to depend on the treatment.
    """
    h, w = y.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = np.hypot(cy, cx)

    recs = []
    keys = []
    for ty in range(0, h - TILE + 1, STRIDE):
        for tx in range(0, w - TILE + 1, STRIDE):
            if tile_keys is not None and (ty, tx) not in tile_keys:
                continue
            my, mx = ty + TILE / 2.0, tx + TILE / 2.0
            dy, dx = my - cy, mx - cx
            r = np.hypot(dy, dx)
            if r < 1e-6:
                continue
            got = tile_anisotropy(y[ty:ty + TILE, tx:tx + TILE], dy / r, dx / r)
            if got is None:
                continue
            pr, pt, pb = got
            recs.append((r / rmax, pb, np.arctan2(dy, dx), pr, pt))
            keys.append((ty, tx))

    if not recs:
        return None
    rn = np.array([q[0] for q in recs])
    pb = np.array([q[1] for q in recs])
    ang = np.array([q[2] for q in recs])
    PR = np.array([q[3] for q in recs])
    PT = np.array([q[4] for q in recs])

    if tile_keys is None:
        # Drop textureless tiles: they report the orientation of noise.
        thr = np.quantile(pb, MIN_POWER_Q)
        keep = pb >= thr
        rn, ang, PR, PT = rn[keep], ang[keep], PR[keep], PT[keep]
        keys = [k for k, v in zip(keys, keep) if v]

    edges = np.linspace(0.0, 1.0, N_ANNULI + 1)
    out = []
    rng = np.random.default_rng(20260824)
    for i in range(N_ANNULI):
        sel = (rn >= edges[i]) & (rn < edges[i + 1])
        n = int(sel.sum())
        if n < 8:
            continue
        pr_s, pt_s = PR[sel], PT[sel]

        def pooled(a, b):
            # Ratio formed inside each |k| ring, then averaged across rings, so
            # an isotropic transfer function cancels exactly (see
            # tile_anisotropy). Summing over tiles first keeps low-power tiles
            # from dominating a mean-of-ratios.
            return float(np.mean(a.sum(axis=0) / b.sum(axis=0)))

        a = pooled(pr_s, pt_s)
        bs = [pooled(pr_s[k], pt_s[k])
              for k in (rng.integers(0, n, n) for _ in range(400))]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        cov = float(np.abs(np.exp(1j * 2 * ang[sel]).mean()))
        out.append({
            "r_mid": float((edges[i] + edges[i + 1]) / 2),
            "A": float(a),
            "ci": [float(lo), float(hi)],
            "n_tiles": n,
            "angular_clustering": cov,
        })
    return {"label": label, "annuli": out, "keys": keys}


def _radial_smear(y, px_at_corner):
    """Plant a KNOWN radial smear: displace by an amount proportional to radius,
    integrated over sub-steps, exactly as a residual scale error would.

    SUB-STEP COUNT IS NOT A FREE PARAMETER. The first version used 7 steps for
    any magnitude. At 150 px that is not a smear at all -- it is seven discrete
    copies 25 px apart, and the transfer function of a 7-tooth comb is periodic
    with passbands rather than a monotone low-pass, so it barely touched the
    0.20-0.40 cyc/px band it was supposed to destroy. Worse, at small radius the
    comb spacing fell to ~5 px, putting its first zero AT the band, so the plant
    fired at the centre and not at the edge -- the exact inverse of the geometry
    it was modelling. Steps are now chosen so the largest step is <= 0.5 px,
    which is the condition for the sum to approximate the continuous integral
    that a real residual scale error produces.
    SAMPLING MUST BE SUB-PIXEL. A nearest-neighbour version of this function
    silently produced a no-op at 1 px (mean |delta| 0.00 DN): with the corner
    displaced by +/-0.5 px, np.rint sends every sub-step to the same source
    pixel. An instrument validated only against plants it can round away has not
    been validated at the magnitudes that matter, so the plant interpolates.
    """
    h, w = y.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy, dx = yy - cy, xx - cx
    del yy, xx
    rmax = np.hypot(cy, cx)
    n_steps = max(5, int(4.0 * px_at_corner) + 1)
    acc = np.zeros(y.shape, dtype=np.float32)
    yf = y.astype(np.float32)
    for s in np.linspace(-0.5, 0.5, n_steps):
        f = 1.0 + s * px_at_corner / rmax
        sy = np.clip(cy + dy * f, 0, h - 1.001)
        sx = np.clip(cx + dx * f, 0, w - 1.001)
        y0 = sy.astype(np.int32)
        x0 = sx.astype(np.int32)
        wy = sy - y0
        wx = sx - x0
        del sy, sx
        acc += ((1 - wy) * (1 - wx) * yf[y0, x0]
                + (1 - wy) * wx * yf[y0, x0 + 1]
                + wy * (1 - wx) * yf[y0 + 1, x0]
                + wy * wx * yf[y0 + 1, x0 + 1])
        del y0, x0, wy, wx
    return acc / n_steps


def _isotropic_blur(y, sigma):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(y, sigma).astype(np.float32)


def controls(path):
    """Sensitivity, specificity, and geometry.

    A green identity control alone would only prove the instrument is quiet. The
    isotropic arm proves it is measuring ORIENTATION rather than mere softness.
    The dose ladder proves it responds PROPORTIONALLY -- a detector that fires
    once tells you nothing about a residual of unknown size, and the ladder is
    also what turns A into a rough ruler in px. The geometry check proves the
    response lives where a scale error puts it (outside, not centre), which is
    what separates this from a generic blur detector.
    """
    y = load_luma(path)
    print(f"controls on {os.path.basename(path)}  {y.shape}")

    # Choose the tiles ONCE, on the untreated frame, and reuse that exact set in
    # every arm. See measure().
    base = measure(y, "identity")
    keys = set(base["keys"])
    print(f"tile set fixed on the untreated frame: {len(keys)} tiles\n")

    def outer(m):
        return float(np.mean([a["A"] for a in m["annuli"] if a["r_mid"] > 0.6]))

    def centre(m):
        return float(np.mean([a["A"] for a in m["annuli"] if a["r_mid"] < 0.25]))

    rows = [("identity", base)]
    # Dose range chosen AFTER a first ladder at 10/30 px showed A_outer floors
    # at 0.028 by 10 px -- the instrument is far more sensitive than expected, so
    # a ladder that saturates on its first rung measures nothing but the floor
    # and cannot test geometry. These doses keep the response on its slope.
    doses = (1.0, 3.0, 10.0)
    for dose in doses:
        yy = _radial_smear(y, dose)
        d = float(np.abs(yy.astype(np.float64) - y.astype(np.float64)).mean())
        if d < 1.0:
            print(f"PLANT DID NOT LAND (radial {dose:g}px, mean |delta| {d:.2f} DN).")
            return 1
        rows.append((f"radial {dose:g}px@corner", measure(yy, "", keys)))
        del yy

    y_iso = _isotropic_blur(y, 1.6)
    d = float(np.abs(y_iso.astype(np.float64) - y.astype(np.float64)).mean())
    if d < 1.0:
        print(f"PLANT DID NOT LAND (isotropic, mean |delta| {d:.2f} DN).")
        return 1
    rows.append(("isotropic sigma=1.6", measure(y_iso, "", keys)))
    del y_iso

    print(f"{'arm':<26} {'A(centre)':>10} {'A(outer)':>10} {'d_outer':>9} {'d_centre':>9}")
    for name, m in rows:
        print(f"{name:<26} {centre(m):>10.4f} {outer(m):>10.4f} "
              f"{outer(m) - outer(base):>9.4f} {centre(m) - centre(base):>9.4f}")

    a0 = outer(base)
    a_dose = [outer(m) for _, m in rows[1:1 + len(doses)]]
    aiso = outer(rows[-1][1])

    ok_sens = a_dose[-1] < a0 - 0.02
    ok_dose = all(x > y_ for x, y_ in zip([a0] + a_dose, a_dose))
    ok_spec = abs(aiso - a0) < 0.02
    ok_null = abs(centre(base) - 1.0) < 0.05
    # A scale error displaces by an amount proportional to radius, so the plant
    # must bite harder outside than at the centre. Tested at the SMALLEST dose:
    # at large doses the outer annuli saturate at the noise floor while the
    # centre is still on its slope, which inverts the comparison for a reason
    # that has nothing to do with geometry.
    m1 = rows[1][1]
    ok_geom = (a0 - outer(m1)) > (centre(base) - centre(m1))

    print()
    for label, ok in (
        (f"SENSITIVITY  {doses[-1]:g}px plant must lower A_outer", ok_sens),
        ("DOSE ORDER   A must fall monotonically with dose", ok_dose),
        ("SPECIFICITY  isotropic plant must NOT move it", ok_spec),
        ("BUILT-IN NULL A(centre) ~ 1 untreated", ok_null),
        (f"GEOMETRY     at {doses[0]:g}px, outer bites harder than centre", ok_geom),
    ):
        print(f"{label:<48}: {'PASS' if ok else 'FAIL'}")

    if not all((ok_sens, ok_dose, ok_spec, ok_null, ok_geom)):
        print("\nInstrument is NOT trustworthy. Do not report A(r) from this build.")
        return 1
    json.dump({n: {k: v for k, v in m.items() if k != "keys"} for n, m in rows},
              open("anisotropy-controls.json", "w"), indent=1)
    print("\nInstrument passes all five. Calibration on this subject:")
    for dose, a in zip(doses, a_dose):
        print(f"  {dose:>5.1f} px radial residual @corner -> A_outer {a:.4f}")
    print(f"  {0.0:>5.1f} px (untreated render)          -> A_outer {a0:.4f}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--controls":
        sys.exit(controls(args[1]))
    results = []
    for p in args:
        y = load_luma(p)
        m = measure(y, os.path.basename(p))
        results.append({k: v for k, v in m.items() if k != "keys"})
        print(f"\n{os.path.basename(p)}  {y.shape}")
        print(f"  {'r':>6} {'A':>8} {'95% CI':>18} {'tiles':>7} {'angclust':>9}")
        for a in m["annuli"]:
            print(f"  {a['r_mid']:>6.2f} {a['A']:>8.4f} "
                  f"[{a['ci'][0]:.4f},{a['ci'][1]:.4f}] {a['n_tiles']:>7} "
                  f"{a['angular_clustering']:>9.3f}")
    json.dump(results, open("anisotropy.json", "w"), indent=1)

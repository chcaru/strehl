"""BUILD-RECERT: the band-separated measurement every re-certification number comes from.

WHY THIS FILE EXISTS
--------------------
ORCH's requirement is that every noise/blotch number be PAIRED with a sharpness
number on the same pixels, band-separated, because the fix now being built in
`pyramid.rs` can win every blotch number by blurring. That is not hypothetical:
on `119MSDCF__worst-on-subject`, `focus-stack` reads sigma_hp 0.077 and
sigma_mid 0.260 -- 10-25x below both other arms -- and it is the arm that
resolves 1.326x LESS than we do. It wins the noise table by being blurred.

So a noise statistic alone cannot certify anything. std() of a band residual is
minimised by destroying the band, and a merge that destroys the band is exactly
the failure we are trying to detect.

THE PAIRING, AND WHY IT DISCRIMINATES
-------------------------------------
Within one band, on one crop, we separate the residual into two statistics that
respond DIFFERENTLY to blur and to denoise:

  floor = 1.4826 * MAD(residual)     the NOISE FLOOR.
        MAD is a robust scale. Scene structure in a band is SPARSE -- edges are
        rare and strong -- so structure sits in the tail and barely moves the
        median absolute deviation. What MAD measures is the stuff that is
        everywhere, which is grain. Lower is quieter.

  peak  = p99.5(|residual|)          the STRUCTURE.
        The sparse strong tail is edges and detail. Higher is sharper.

  ratio = peak / floor               STRUCTURE-TO-NOISE.

The discrimination is in how the two move together:

  a BLUR       lowers `peak` and `floor` TOGETHER, because it removes the whole
               band. `ratio` therefore does NOT rise, and `peak` visibly falls.
  a DENOISE    lowers `floor` while leaving `peak` alone, because it removes
               what is everywhere and not what is sparse. `ratio` RISES.

That asymmetry is the entire point: it is what lets the harness say "this
candidate got quieter by cleaning" rather than "this candidate got quieter by
blurring", from statistics taken on identical pixels. A single scalar cannot do
that, which is why nothing here is ever averaged into one.

Commissioned in `commission_bands.py` with three arms -- null, planted
degradation (blur), planted improvement (denoise) -- because a suite that plants
only degradations cannot distinguish a metric that is BLIND to a defect from one
that is PERVERSE on it, and this project has shipped exactly that bug.

BANDS, AND WHY ONE OF THEM MAY NOT CARRY A SHARPNESS CLAIM
----------------------------------------------------------
Bands are stated in pixels AND in cycles/px, because a band number without its
band is not a number. Passbands are the box-filter windows: a difference of box
filters with windows ka < kb passes scales between ka and kb px, i.e. spatial
frequencies between 1/kb and 1/ka cyc/px.

  grain    p - box(1)            <=3 px      >=0.33 cyc/px
  struct   box(2) - box(6)      5-13 px    0.077-0.20 cyc/px
  mottle   box(10) - box(30)   21-61 px   0.016-0.048 cyc/px

`grain` reports NOISE ONLY. It sits above 0.30 cyc/px, and this project WITHDREW
sharpness claims above 0.30 cyc/px when the noise control (3.866) was measured
larger than the effect it was supposed to support (3.462). A `peak` computed
there is not distinguishable from noise, so `sharpness_admissible` is False for
that band and the harness refuses to form a sharpness verdict from it. Noise in
that band is still perfectly measurable -- that withdrawal was about sharpness.

`struct` is the band sharpness verdicts are taken in. Its passband lies entirely
at or below 0.20 cyc/px, inside the region this project can still support.

`mottle` is the band the six convicted subjects were convicted in (20-60 px).

The display transform and the per-channel gain are applied first, replicating
`orch_eye_check.py` exactly -- `boxblur` and `srgb` are IMPORTED from it rather
than re-typed, so the band definitions cannot drift apart from ORCH's. A
statistic measured somewhere other than where the verdict was formed cannot
overturn the verdict.
"""
import sys
from pathlib import Path

import numpy as np

# Import the display transform and the box filter from ORCH's implementation
# rather than copying them. If ORCH changes the band definition, this harness
# changes with it; a second copy would silently diverge and we would be
# comparing two different measurements while believing they were one.
_ORCH = Path(__file__).resolve().parents[1] / "ORCH-drift-check"
if str(_ORCH) not in sys.path:
    sys.path.insert(0, str(_ORCH))
from orch_eye_check import boxblur, srgb  # noqa: E402

CROP = 400

# The share of a noise win that may be paid for out of structure before the win
# is called a blur. Justified only by arm F of `commission_bands.py`, which
# requires the planted-blur and planted-denoise populations to stay disjoint
# across subjects with this value between them. It is an absolute threshold and
# therefore owes that commissioning; see the note in `classify`.
PAID_MAX = 0.25

# name -> (residual fn, px passband, cyc/px passband, sharpness_admissible)
BANDS = {
    "grain": (lambda p: p - boxblur(p, 1), "<=3px", (0.33, 0.50), False),
    "struct": (lambda p: boxblur(p, 2) - boxblur(p, 6), "5-13px", (0.077, 0.20), True),
    "mottle": (lambda p: boxblur(p, 10) - boxblur(p, 30), "21-61px", (0.016, 0.048), True),
}


def display_crop(arr, y, x, shift, gain, offset, exposure, crop=CROP, already_srgb=False):
    """The exact pixels a viewer judged: shift-registered, gain-matched, tone-mapped.

    Registration is integer-shift only. Sub-pixel resampling would add blur to
    the very quantity `peak` measures, which would make the instrument charge a
    sharpness penalty it invented itself.

    `already_srgb` exists because this harness reads two different kinds of file
    and they are not in the same state. The head-to-head arms under `V-NOISE2`
    are LINEAR (the manifest calls them `linear_arms`), so the sRGB curve is
    part of the display transform and `orch_eye_check.py` applies it. The
    acceptance masters under `SHIP-V4` were rendered `--srgb`, so the curve is
    already baked in and applying it again would encode twice -- which
    compresses the highlights a second time and would change every `peak` this
    harness reports. Getting this wrong is silent: the numbers still come out.
    """
    dy, dx = shift
    c = arr[y + dy:y + dy + crop, x + dx:x + dx + crop, :3].astype(np.float32)
    if c.shape[:2] != (crop, crop):
        raise ValueError(f"crop fell off the image: got {c.shape[:2]} want {(crop, crop)}")
    g = np.asarray(gain, dtype=np.float32)
    o = np.asarray(offset, dtype=np.float32)
    c = c * g[None, None, :] + o[None, None, :]
    v = np.clip(c / 65535.0 * exposure, 0.0, 1.0)
    return (v if already_srgb else srgb(v)) * 255.0


def _noise_peak_ratio(band, n=1024, seed=7):
    """p99.5(|r|) / floor for a band residual of PURE noise.

    `peak` is not a structure statistic. It is p99.5 of a band residual, and a
    band residual of pure noise has a perfectly good p99.5 -- about 2.8 times its
    own scale for a Gaussian. So `peak` always contains a noise term, and the
    size of that term is knowable: it is this constant times `floor`.

    Commissioning is what forced this. With `peak` used raw, removing PLANTED
    band-confined noise scored as a BLUR_TRADE with `paid` = 1.06, because the
    plant had raised `peak` and `floor` together and removing it lowered them
    together -- which is indistinguishable from a blur if you do not know how
    much of `peak` the noise was entitled to.

    The constant is MEASURED here per band rather than taken as the Gaussian
    2.807, because these bands are differences of box filters: they correlate the
    noise, and a correlated field's percentile-to-scale ratio is not the
    Gaussian one. Measuring it from the filter makes it a property of the
    instrument, which is what it is.
    """
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 1.0, size=(n, n))
    r = BANDS[band][0](w)
    med = np.median(r)
    scale = 1.4826 * float(np.median(np.abs(r - med)))
    return float(np.percentile(np.abs(r - med), 99.5)) / scale


NOISE_PEAK = {b: _noise_peak_ratio(b) for b in BANDS}


def _structure(peak, floor, band):
    """Peak with the noise contribution removed in quadrature.

    Returns (amplitude, detectable). `detectable` is False when `peak` does not
    exceed what pure noise of this floor would produce anyway -- in which case
    the band holds no structure this instrument can see, and no sharpness claim
    may be formed from it. That refusal is the same discipline that made this
    project withdraw its sharpness claims above 0.30 cyc/px when the noise
    control was measured larger than the effect it was meant to support.
    """
    expected = NOISE_PEAK[band] * floor
    detectable = peak > expected * 1.05
    return (float(np.sqrt(max(peak * peak - expected * expected, 0.0))), detectable)


def band_stats(disp, band):
    """floor / peak / structure for one band, averaged over the three channels.

    Returns 8-bit code units. Channels are averaged only AFTER each channel's own
    floor and peak are formed, so a channel that is quiet for one arm and loud
    for another cannot be hidden by a ratio-of-means.
    """
    fn, px, cyc, admissible = BANDS[band]
    floors, peaks = [], []
    for ch in range(disp.shape[2]):
        r = fn(disp[..., ch].astype(np.float64))
        med = np.median(r)
        floors.append(1.4826 * float(np.median(np.abs(r - med))))
        peaks.append(float(np.percentile(np.abs(r - med), 99.5)))
    floor = float(np.mean(floors))
    peak = float(np.mean(peaks))
    # A ZERO FLOOR IS NOT A QUIET CROP -- IT IS A CROP WITH NO MEASURABLE NOISE.
    # MAD is zero exactly when at least half the residual equals its own median,
    # which happens when half the crop is a single constant: clipped white, or
    # the crushed black backdrop that three subjects in this corpus carry
    # (`119MSDCF` reads 3.260% crush overall and far more than that inside a
    # backdrop crop). Commissioning found this at two of the three published
    # sites on `119MSDCF`, where every ratio came back `nan` -- and `nan` fails
    # every `<` and `>` comparison, so the classifier returned "HELD". A broken
    # measurement was reading as a clean result, which is the exact failure this
    # project keeps naming. Such a band is REFUSED, and refusal is counted
    # separately from a pass everywhere downstream.
    const = float(np.mean([np.mean(disp[..., c] == np.median(disp[..., c]))
                           for c in range(disp.shape[2])]))
    degenerate = not (floor > 1e-9)
    amp, detectable = (0.0, False) if degenerate else _structure(peak, floor, band)
    return {
        "band": band, "px": px, "cyc_px": list(cyc),
        "sharpness_admissible": admissible,
        "floor": floor, "peak": peak, "structure": amp,
        "structure_detectable": bool(detectable),
        "noise_peak_ratio": NOISE_PEAK[band],
        "ratio": peak / floor if not degenerate else None,
        "degenerate": degenerate, "const_frac": const,
        "floor_ch": floors, "peak_ch": peaks,
    }


def measure_crop(disp):
    return {b: band_stats(disp, b) for b in BANDS}


def classify(base, cand, floor_tol=0.02, peak_tol=0.02, paid_max=PAID_MAX):
    """Name what moved between two band measurements, refusing to average them.

    `floor` lower is better (quieter). `peak` higher is better (sharper).
    Tolerances are RELATIVE: this project's rule is that a statistic earns an
    absolute threshold only when commissioned to be subject-invariant.

    THE DISCRIMINATOR IS NOT `peak` ALONE, AND COMMISSIONING IS WHY.
    A first version classified a noise win as a BLUR_TRADE whenever `peak` fell
    by more than 2%. That misread a planted pure denoise -- structure was
    bit-identical between the two arms by construction -- because `peak` is
    p99.5 of a band residual and a band residual contains grain as well as
    edges, so removing grain legitimately costs a few percent of `peak`. The
    tolerance was not wrong by a little; the QUANTITY was wrong.

    What separates the two is not how far `peak` fell but how much of the noise
    win was PAID FOR out of structure:

        paid = d_peak / d_floor        (both negative, so paid >= 0)

    A blur removes the whole band, so structure and floor fall together and
    `paid` approaches 1. A denoise removes what is everywhere and not what is
    sparse, so `paid` approaches 0. Measured on the planted arms it separates by
    more than an order of magnitude, and `commission_bands.py` arm F checks that
    the two populations stay disjoint across subjects before this threshold is
    allowed to be an absolute one.

    The verdict this exists to produce is BLUR_TRADE, because that is the trade
    the fix under construction is most likely to make and the one a single
    averaged score would hide.
    """
    if base.get("degenerate") or cand.get("degenerate"):
        return {"d_floor": None, "d_peak": None, "paid": None, "refused": True,
                "verdict": "REFUSED -- noise floor is degenerate (>=50%% of this crop is one "
                           "constant, typically clipped black or white); no ratio can be formed",
                "quieter": False, "softer": False}
    # A band whose p99.5 does not exceed what its own noise floor would produce
    # anyway holds no structure this instrument can see. Forming a sharpness
    # verdict there would be reading the noise and calling it detail.
    if base["sharpness_admissible"] and not (base["structure_detectable"]
                                             and cand["structure_detectable"]):
        df0 = (cand["floor"] - base["floor"]) / base["floor"] if base["floor"] > 1e-12 else None
        return {"d_floor": df0, "d_peak": None, "paid": None, "refused": True,
                "verdict": "REFUSED -- no structure above this band's own noise floor "
                           "(p99.5 <= %.2f x floor); no sharpness claim can be formed"
                           % base["noise_peak_ratio"],
                "quieter": bool(df0 is not None and df0 < -floor_tol), "softer": False}
    df = (cand["floor"] - base["floor"]) / base["floor"]
    # `structure` is `peak` with the noise term removed in quadrature, so that
    # removing noise -- which raises `peak` and `floor` together -- is not
    # charged as a loss of detail. See `_structure`.
    bp, cp = base["structure"], cand["structure"]
    dp = (cp - bp) / bp if bp > 1e-12 else 0.0
    quieter, louder = df < -floor_tol, df > floor_tol
    softer, sharper = dp < -peak_tol, dp > peak_tol
    paid = None
    if quieter:
        # `paid` is a RATIO OF TWO CHANGES, so it is only meaningful once the
        # denominator is a real change. Commissioning arm F measured the cost of
        # ignoring that: with `paid` computed for arbitrarily small `d_floor`,
        # the planted-denoise population reached 0.534 and the planted-blur
        # population fell to 0.407, and the two OVERLAPPED -- not because the
        # metric confused a blur with a clean-up, but because dividing a small
        # noisy numerator by a small noisy denominator produces a large number
        # with no content. Restricting `paid` to cases that cleared `floor_tol`
        # is what makes PAID_MAX separable at all.
        paid = (dp / df) if dp < 0 else 0.0
    if not base["sharpness_admissible"]:
        # Noise-only band. We may say it got quieter; we may not say why, because
        # `peak` above 0.30 cyc/px is not distinguishable from noise, and this
        # project withdrew sharpness claims there when the noise control (3.866)
        # was measured larger than the effect it was meant to support (3.462).
        verdict = "QUIETER" if quieter else ("LOUDER" if louder else "HELD")
        verdict += " (noise-only band; no sharpness claim admissible)"
    elif quieter and paid is not None and paid > paid_max:
        verdict = (f"BLUR_TRADE -- quieter, but {paid * 100:.0f}%% of the noise win was paid "
                   f"for out of structure; that is a blur, not a clean-up")
    elif quieter:
        verdict = "CLEANER -- quieter with structure held"
    elif softer:
        verdict = "SOFTER -- structure lost with no noise win"
    elif louder and sharper:
        verdict = "SHARPER BUT NOISIER"
    elif louder:
        verdict = "NOISIER"
    elif sharper:
        verdict = "SHARPER"
    else:
        verdict = "HELD"
    return {"d_floor": df, "d_peak": dp, "paid": paid, "refused": False,
            "verdict": verdict, "quieter": bool(quieter), "softer": bool(softer)}

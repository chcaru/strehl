"""M68 step 01 - PRE-REGISTRATION. Committed before this script was run.

Is the B plane's measured 0.84x per-plane scale (M61 fact 22, 0.8396 +/- 0.0112)
a scale that touches the DARK noise, or one that does not?

=========================================================================
0. WHAT I READ FIRST (rule 40), AND WHAT IS ALREADY SETTLED
=========================================================================
Searched docs/research/ for `conversion gain`, `PTC`, `per-plane`, `dark`,
`B plane`. Read in full or in the relevant part:

  M61-ptc-high-iso-measured.md   direct predecessor; facts 22/23, 29,
                                 50-58, questions 1 and 10. Read in full.
  M48c-defect-layer-measured.md  the 13,630 recurrent defects, criterion B,
                                 the 68x odd/even row-parity asymmetry.
  M4-fpn-measured.md             section 8.1's per-plane dark-sigma table at
                                 11 ISOs; sections 1, 2, 5, 8.2, 8.3, 9, 10.
  crates/strehl-core/src/profile.rs  the module header (which statistic the
                                 constants are), gain_divisor, base_iso,
                                 read_noise_e_*, DARK_SIGMA_RMS_DN.
  M48-read-noise-measured.md     cited by profile.rs for the rawpy
                                 reproduction of M4's 44 cells.
  M25-simulator-measured.md      fact 200, the only prior PTC on captures.
  Also grepped and skimmed: M53-flat-ratio.md, M62-sqrt-n.md, M22, M50,
  SYNTHESIS.md, OWNER-QUESTIONS.md, C-landscape.md, F-camera-lens-optics.md.

Settled, and NOT reopened here: the shipped single-line gain relation is
right across the dual-gain switch (M61 facts 13-15, refuting M48c fact 17);
the 0.84x is applied BEFORE quantisation (M61 facts 52-55); a QE difference
cannot produce a var/mean deficit at all (M61 fact 51).

=========================================================================
1. HYPOTHESES - by MECHANISM, and none of them by expected sign
=========================================================================
Derived from first principles and checked against a planted signal chain in
`00-derivation.py`, whose output is in `data/00-derivation.txt`. The chain is

    sigma^2(ISO) = alpha * G^2 + delta,     G = max(ISO, base_iso)

with alpha carrying everything generated UPSTREAM of the programmable gain
(electron-domain shot noise and source-follower voltage noise) and delta
everything generated downstream of it (column ADC noise and quantisation).

  P1  charge-domain conversion gain - the sense-node capacitance differs, so
      q/C differs per plane. Touches only the electron-domain term.
  P2  analog scale after the source follower, ahead of the ADC. Touches
      everything analog, leaves the ADC and quantisation.
  P3  P2 in the limit delta -> 0.
  P4  post-ADC digital scale. Refuted by M61 facts 53-55; carried as a
      reference prediction.
  P5  mean-preserving charge sharing - wavelength-dependent lateral charge
      diffusion / optical crosstalk, which suppresses per-pixel shot
      variance while conserving the mean. NOT a QE difference. This
      candidate is not in M61's fact-50 list and is not a scale at all.

I DISAGREE WITH PART OF M61's FORECAST and say so before measuring. M61
question 10 predicts "a sensor conversion gain ... pinned at 0.84 and flat
in ISO". That holds only if the read noise is generated upstream of the
charge-to-voltage conversion. The dominant read-noise term in a modern CMOS
is source-follower VOLTAGE noise, which is downstream of q/C, so a
charge-domain conversion gain difference leaves the dark sigma alone: P1
predicts 1.00, not 0.84. M61's falling-toward-0.84 signature for an analog
attenuation is correct algebra and the plant reproduces it.

=========================================================================
2. THE OBSERVABLE
=========================================================================
Per CFA plane p and per ISO group, the POOLED RMS TEMPORAL SIGMA -

    sigma_p(ISO) = sqrt( mean over surviving pixels of
                         the per-pixel temporal variance over T frames )

- which is the exact statistic every noise constant in profile.rs is,
per that module's header, so any correction this milestone recommends is
denominated in the same unit the model already uses.

Fitted per plane over the ISO ladder:  sigma_p^2 = alpha_p,mode * G^2 + delta_p,
G = max(ISO, 100), alpha separate per gain mode (the dual-gain switch is a
change of analog gain), delta SHARED across modes (the ADC is not switched).
Ordinary least squares on sigma^2 against G^2. Uncertainty by leave-one-
ISO-out.

PRIMARY comparison: B against G2. M48c fact 9 puts R and G1 on even sensor
rows and G2 and B on odd, with 68x more recurrent defects on odd rows, and
M48c fact 10 argues an interleaved readout chain. If the chain differs by
row parity then delta may differ by parity, and B-against-pooled-green would
mix two chains. SECONDARY: B against the pooled greens, which is what M61's
PTC compared and is what a correction to profile.rs would be phrased in.

=========================================================================
3. ISO RANGE AND DATA
=========================================================================
All 11 folders of D:\\macro-dark-frames, ISO 50-2000, 1/100 s, ILCE-7CM2.
ISO read from EXIF per file and asserted uniform within a folder; the
folder->ISO map is discovered, never assumed. NOTHING IS WRITTEN TO D:.

Frames: the owner's first two shots per folder are stabilisation and are
dropped. T = 20 per folder, matching M4 and profile.rs's declared basis.

Geometry: rawpy's raw_image_visible only, never the padded buffer (rule 7).
Per-plane sample count asserted exactly, so a geometry slip cannot pass
silently. Rule 32: every decoded array is copied inside the `with`.

ISO 50 is a pull setting reading out at base gain (M4 section 8.2), so
G = max(ISO,100) puts ISO 50 and ISO 100 at the same abscissa. They then act
as a REPLICATE PAIR at fixed gain, which is a free repeatability estimate.

=========================================================================
4. EXCLUSION RULES
=========================================================================
Hot pixels and dark current will contaminate a dark-sigma statistic, and
M48c fact 9 shows the contamination is grossly asymmetric between the planes
I am comparing: R 101, G1 98, G2 7,757, B 5,674 recurrent defects.

  Defect map: M48c criterion B, unchanged and not re-tuned. Per plane per
  ISO, excess = temporal mean minus the median of the four same-plane
  4-neighbours; sigma_rob = 1.4826 * MAD(excess); flag |excess| > 6*sigma_rob.
  Require recurrence in >= 6 of the 11 ISO groups. The resulting FIXED pixel
  set is excluded at EVERY ISO - M48c discipline 1, measure a fixed
  population rather than moving a threshold with ISO.

  Border: the one-pixel plane border cannot be high-passed and is excluded
  from both the map and the statistic, at every ISO, for every plane.

  Why this cannot bias the answer: for Gaussian samples the sample mean and
  the sample variance are independent, so selecting pixels on the temporal
  MEAN map leaves E[per-pixel temporal variance] unbiased among the
  survivors. Same independence M61-E1 used to select on u while estimating v.

  Dark current in the surviving population is reported, not assumed: the
  median temporal-mean excess of the survivors is printed per plane per ISO.

=========================================================================
5. CONTROLS AND PRE-REGISTERED CRITERIA
=========================================================================
C0  DECODE GATE. My no-exclusion pooled RMS must reproduce M4 section 8.1's
    44 published cells (4 planes x 11 ISOs) to within 0.5%. M4 decoded
    through strehl-raw/rawler; this script decodes through rawpy/LibRaw, so
    C0 is a cross-implementation check on the loader (rule 32) and not on
    the estimator. NOTE the crop differs: rawpy's visible width is 7028
    against rule 7's 7032, 0.057% of the columns, which the 0.5% band
    swallows by ~10x.
    IF C0 FAILS THE MILESTONE STOPS AND REPORTS THAT.

C1  THE CONTROL THAT CAN FAIL - G1 vs G2. The two green planes must not
    show the effect I am attributing to B, and their spread bounds my
    measurement noise. PASSES iff BOTH:
      C1a  |alpha_G2/alpha_G1 - 1| <= 0.10   (one third of the 0.295
           separation between the two hypothesis classes)
      C1b  max - min of sigma_G2/sigma_G1 over the 11 ISOs <= 0.03
    IF C1 FAILS, THE B RESULT IS UNINTERPRETABLE AND I REPORT IT AS SUCH,
    because the instrument would then be manufacturing per-plane alpha
    differences of exactly the kind under test.

C2  SPLIT-HALF NULL ON REAL DATA. Frames 3-12 and 13-22 give two disjoint
    10-frame estimates of the SAME plane. Treating half A as "test" and
    half B as "reference" must return unity. PASSES iff
      C2a  |alpha ratio - 1| <= 0.05      C2b  |delta ratio - 1| <= 0.35
    on G1 and on B. This is a floor on the instrument, measured through the
    real decoder, the real defects and the real fit, at HALF the frames and
    therefore pessimistic. IF C2a FAILS the alpha ratio has no resolution
    and the headline is void. IF C2b FAILS I report delta as unresolved and
    decline to split P2 from P3.

C3  THE DISCRIMINATION, on alpha_B/alpha_G2 (primary) and alpha_B/alpha_Gpool:
      within 1.000 +/- 0.05  =>  {P1, P5}: the scale does not touch the dark
                                 noise; P2, P3, P4 refuted.
      within 0.705 +/- 0.05  =>  {P2, P3, P4}: the scale is upstream of the
                                 dark-noise generation; P1 and P5 refuted.
                                 (0.705 = 0.8396^2, M61 fact 22.)
      anything else          =>  NEITHER. Report the number, refuse the
                                 binary, and say the two-term model is
                                 incomplete.
    The +/- 0.05 half-width is one sixth of the separation and is set by C2a.

C4  WHAT WOULD MAKE ME CONCLUDE THE OBSERVABLE CANNOT SEPARATE THE
    HYPOTHESES. Declared in advance, with its consequence:
      (a) C1 fails                                -> uninterpretable, stop
      (b) C2a fails                               -> headline void
      (c) C3 lands in neither band                -> refuse the binary
      (d) delta_G2 is not resolved above zero at 3x its leave-one-ISO-out
          spread                                  -> P2 and P3 are not
          separable; report no upstream fraction
    AND, WHATEVER THE DATA SAYS: this observable can never separate P1 from
    P5. Both predict an exact null in darkness. That residue is reported as
    unsettled regardless of outcome, and naming what WOULD separate them is
    part of the deliverable.

=========================================================================
6. ROBUSTNESS ARMS (reported, not gates)
=========================================================================
  A  no defect exclusion at all (this is also C0's arm)
  B  recurrence thresholds 3 and 9 instead of 6
  C  median per-pixel variance instead of the pooled mean
  D  delta fitted per gain mode instead of shared
  E  high-mode-only fit (ISO 400-2000, 7 points)
  F  R vs G1 - same row parity, and M61's PTC put R/green at 0.985, so R is
     a second near-null the instrument must not break

=========================================================================
7. DISCLOSURE - THIS PRE-REGISTRATION IS NOT BLIND
=========================================================================
M61 fact 6 set the precedent of saying so. Mine is worse than M61's and I
state exactly how.

M4 section 8.1's published table IS the numerator and denominator of my
observable, at all 11 ISOs, and rule 40 required me to read it. Worse, while
designing the fit I did a two-point (ISO 400 and ISO 2000) solve of
sigma^2 = alpha*G^2 + delta on M4's published green and B rows, to check
that delta is resolvable at all. It is: that solve put delta_G near
0.25 DN^2, about 15% of the ISO-400 variance, which is why the alpha/delta
decomposition is the primary estimator here rather than the raw sigma ratio.
The same solve returned an alpha ratio near 0.86 and a delta ratio near
0.59, i.e. NEITHER hypothesis band cleanly. I have therefore already seen an
indication that C3 may land in its third branch, and I record that here so
that reporting the third branch cannot be read as a discovery and reporting
either of the other two cannot be read as motivated.

What IS blind: M4's table carries no defect exclusion, and the defect
population is 60x heavier on B and G2 than on R and G1. I have not seen what
excluding it does to any of these numbers, nor what a proper 11-point
shared-delta fit does, nor the split-half null, nor the G1/G2 control.

What the pre-registration is worth is therefore not blindness. It is that
the estimator, the exclusions, the bands, and the CONSEQUENCE attached to
each unmet criterion are fixed in writing before the run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

DARKS = Path(r"D:\macro-dark-frames")
HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "cache"
DATA = HERE / "data"

DROP_FIRST = 2  # owner's stabilisation shots
T_FRAMES = 20
BASE_ISO = 100.0
S_PTC = 0.8396  # M61 fact 22
S2_PTC = S_PTC * S_PTC

# rawpy raw_pattern for this body is [[0,1],[3,2]] with color_desc RGBG,
# i.e. R G1 / G2 B. Asserted at run time rather than assumed.
PLANES = ["R", "G1", "G2", "B"]
PLANE_OFFSET = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}

# M4 section 8.1, quoted verbatim for gate C0. ISO -> (R, G1, G2, B).
M4_TABLE = {
    50: (1.0079, 1.0054, 1.0120, 0.9211),
    100: (1.0048, 1.0042, 1.0105, 0.9185),
    200: (1.7709, 1.7782, 1.7929, 1.6246),
    250: (2.1927, 2.2104, 2.2284, 2.0201),
    400: (1.2130, 1.2266, 1.2403, 1.1146),
    500: (1.4940, 1.4949, 1.5105, 1.3724),
    640: (1.8308, 1.8438, 1.8657, 1.6914),
    800: (2.2752, 2.2872, 2.3138, 2.1100),
    1000: (2.8376, 2.8582, 2.8920, 2.6463),
    1600: (4.4369, 4.4702, 4.5407, 4.1739),
    2000: (5.5866, 5.6165, 5.6883, 5.2406),
}

C0_BAND = 0.005
C1A_BAND = 0.10
C1B_BAND = 0.03
C2A_BAND = 0.05
C2B_BAND = 0.35
C3_HALF = 0.05


def read_iso(path: Path) -> int:
    import exifread

    with open(path, "rb") as fh:
        tags = exifread.process_file(fh, details=False, stop_tag="EXIF ISOSpeedRatings")
    for key in ("EXIF ISOSpeedRatings", "EXIF PhotographicSensitivity", "MakerNote ISOSetting"):
        if key in tags:
            v = tags[key].values
            return int(v[0] if isinstance(v, list) else v)
    raise KeyError(f"no ISO tag in {path}: {sorted(tags)[:20]}")


def folder_iso(folder: Path) -> tuple[int, list[Path]]:
    files = sorted(folder.glob("DSC*.ARW"))
    isos = {read_iso(f) for f in files}
    if len(isos) != 1:
        raise RuntimeError(f"{folder.name} is not uniform in ISO: {sorted(isos)}")
    return isos.pop(), files


def accumulate(files: list[Path]) -> dict[str, np.ndarray]:
    """Streaming per-pixel temporal sums over the whole 20 and over half A."""
    n = 0
    s = ss = sa = ssa = None
    shape = None
    for i, path in enumerate(files):
        import rawpy

        with rawpy.imread(str(path)) as raw:
            if i == 0:
                pat = raw.raw_pattern.tolist()
                desc = raw.color_desc
                if pat != [[0, 1], [3, 2]] or desc != b"RGBG":
                    raise RuntimeError(f"unexpected CFA layout {pat} {desc!r}")
            # rule 32: allocate AND copy inside the with-block.
            a = raw.raw_image_visible.astype(np.float64) - 512.0
        if shape is None:
            shape = a.shape
            s = np.zeros(shape, np.float64)
            ss = np.zeros(shape, np.float64)
            sa = np.zeros(shape, np.float64)
            ssa = np.zeros(shape, np.float64)
        elif a.shape != shape:
            raise RuntimeError(f"shape changed: {a.shape} vs {shape}")
        s += a
        ss += a * a
        if i < len(files) // 2:
            sa += a
            ssa += a * a
        n += 1
    if n != T_FRAMES:
        raise RuntimeError(f"expected {T_FRAMES} frames, accumulated {n}")
    na = len(files) // 2
    nb = n - na
    mean = s / n
    var = (ss - s * s / n) / (n - 1)
    var_a = (ssa - sa * sa / na) / (na - 1)
    sb = s - sa
    ssb = ss - ssa
    var_b = (ssb - sb * sb / nb) / (nb - 1)
    return {
        "mean": mean.astype(np.float32),
        "var": var.astype(np.float32),
        "var_a": var_a.astype(np.float32),
        "var_b": var_b.astype(np.float32),
    }


def split_plane(a: np.ndarray, plane: str) -> np.ndarray:
    r, c = PLANE_OFFSET[plane]
    return a[r::2, c::2]


def defect_flags(mean_plane: np.ndarray) -> np.ndarray:
    """M48c criterion B on one plane's temporal-mean map. Border excluded."""
    m = mean_plane.astype(np.float32)
    nb = np.stack([m[:-2, 1:-1], m[2:, 1:-1], m[1:-1, :-2], m[1:-1, 2:]], axis=0)
    nb.sort(axis=0)
    med = 0.5 * (nb[1] + nb[2])
    excess = m[1:-1, 1:-1] - med
    mad = np.median(np.abs(excess - np.median(excess)))
    sig = 1.4826 * float(mad)
    flags = np.zeros(m.shape, bool)
    flags[1:-1, 1:-1] = np.abs(excess) > 6.0 * sig
    return flags


def interior_mask(shape: tuple[int, int]) -> np.ndarray:
    k = np.zeros(shape, bool)
    k[1:-1, 1:-1] = True
    return k


def fit_alpha_delta(g: np.ndarray, mode: np.ndarray, var: np.ndarray,
                    shared_delta: bool = True) -> dict[str, float]:
    """sigma^2 = alpha[mode]*G^2 + delta. mode is 0 (low) / 1 (high)."""
    g2 = g**2
    if shared_delta:
        design = np.column_stack([g2 * (mode == 0), g2 * (mode == 1), np.ones_like(g2)])
        coef = np.linalg.lstsq(design, var, rcond=None)[0]
        return {"alpha_low": coef[0], "alpha_high": coef[1],
                "delta_low": coef[2], "delta_high": coef[2]}
    design = np.column_stack([g2 * (mode == 0), g2 * (mode == 1),
                              1.0 * (mode == 0), 1.0 * (mode == 1)])
    coef = np.linalg.lstsq(design, var, rcond=None)[0]
    return {"alpha_low": coef[0], "alpha_high": coef[1],
            "delta_low": coef[2], "delta_high": coef[3]}


def jackknife(g, mode, var, shared_delta=True):
    keys = ["alpha_low", "alpha_high", "delta_low", "delta_high"]
    out = {k: [] for k in keys}
    for i in range(len(g)):
        sel = np.ones(len(g), bool)
        sel[i] = False
        f = fit_alpha_delta(g[sel], mode[sel], var[sel], shared_delta)
        for k in keys:
            out[k].append(f[k])
    return {k: float(np.std(v, ddof=1) * np.sqrt(len(g) - 1)) for k, v in out.items()}


def selftest() -> int:
    """Synthetic end-to-end check of the fit and the ratio machinery. No corpus."""
    print("=== selftest: planted ladders through fit_alpha_delta ===")
    isos = np.array(sorted(M4_TABLE))
    g = np.maximum(isos, BASE_ISO).astype(float)
    mode = (isos >= 400).astype(int)
    a_lo, a_hi, d = 7.6e-5, 7.9e-6, 0.25
    base = np.where(mode == 0, a_lo, a_hi) * g**2 + d
    for name, alpha_s, delta_s in [("null", 1.0, 1.0), ("P2", S2_PTC, 1.0),
                                   ("P4-ish", S2_PTC, 2.78)]:
        planted = np.where(mode == 0, a_lo, a_hi) * alpha_s * g**2 + d * delta_s
        f0 = fit_alpha_delta(g, mode, base)
        f1 = fit_alpha_delta(g, mode, planted)
        print(f"  {name:8s} alpha_high ratio {f1['alpha_high'] / f0['alpha_high']:.4f} "
              f"(planted {alpha_s:.4f})  delta ratio "
              f"{f1['delta_high'] / f0['delta_high']:.4f} (planted {delta_s:.4f})")
    print("  jackknife on the null ladder:", {k: round(v, 6) for k, v in
                                              jackknife(g, mode, base).items()})
    print("=== selftest: plane split geometry ===")
    a = np.arange(24).reshape(4, 6)
    for p in PLANES:
        print(f"  {p:2s} -> {split_plane(a, p).tolist()}")
    print("=== selftest: defect_flags on a planted map ===")
    m = np.zeros((64, 64), np.float32)
    m += np.random.default_rng(7).normal(0, 0.05, m.shape).astype(np.float32)
    m[10, 10] = 5.0
    m[40, 33] = -5.0
    fl = defect_flags(m)
    print(f"  flagged {int(fl.sum())} (expect 2 planted, found at "
          f"{[tuple(int(x) for x in c) for c in np.argwhere(fl)]})")
    print("SELFTEST OK")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    CACHE.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)

    folders = sorted(p for p in DARKS.iterdir() if p.is_dir())
    print(f"folders: {[p.name for p in folders]}")
    groups = []
    for folder in folders:
        iso, files = folder_iso(folder)
        used = files[DROP_FIRST:]
        print(f"  {folder.name}  ISO {iso:5d}  {len(files)} files, "
              f"dropping {DROP_FIRST}, using {len(used)}")
        groups.append((iso, folder.name, used))
    groups.sort()

    stats = {}
    for iso, name, files in groups:
        npz = CACHE / f"{name}-iso{iso}.npz"
        if npz.exists():
            print(f"  cache hit {npz.name}")
            z = np.load(npz)
            stats[iso] = {k: z[k] for k in z.files}
        else:
            print(f"  decoding {name} (ISO {iso}) ...", flush=True)
            acc = accumulate(files)
            np.savez(npz, **acc)
            stats[iso] = acc
    print("decode complete")

    shape = stats[groups[0][0]]["mean"].shape
    print(f"visible geometry {shape}, per plane {(shape[0] // 2, shape[1] // 2)}, "
          f"{(shape[0] // 2) * (shape[1] // 2)} px")

    # --- fixed defect map: M48c criterion B, recurrence over the 11 ISOs ---
    isos = np.array([g[0] for g in groups])
    recur = {p: np.zeros((shape[0] // 2, shape[1] // 2), np.uint8) for p in PLANES}
    for iso in isos:
        for p in PLANES:
            recur[p] += defect_flags(split_plane(stats[iso]["mean"], p)).astype(np.uint8)
    np.savez(CACHE / "recurrence.npz", **recur)
    for p in PLANES:
        for thr in (3, 6, 9):
            print(f"  {p:2s} recurrence>={thr}: {int((recur[p] >= thr).sum())}")

    out = {"planes": PLANES, "isos": isos.tolist(), "geometry": list(shape)}
    rows = {}
    for thr_name, thr in [("none", None), ("r3", 3), ("r6", 6), ("r9", 9)]:
        rows[thr_name] = {}
        for p in PLANES:
            keep = interior_mask(recur[p].shape)
            if thr is not None:
                keep &= recur[p] < thr
            per = []
            for iso in isos:
                v = split_plane(stats[iso]["var"], p)[keep]
                m = split_plane(stats[iso]["mean"], p)[keep]
                va = split_plane(stats[iso]["var_a"], p)[keep]
                vb = split_plane(stats[iso]["var_b"], p)[keep]
                per.append({
                    "iso": int(iso), "n": int(v.size),
                    "rms": float(np.sqrt(v.mean(dtype=np.float64))),
                    "var": float(v.mean(dtype=np.float64)),
                    "median_var": float(np.median(v)),
                    "median_mean_excess": float(np.median(m)),
                    "var_a": float(va.mean(dtype=np.float64)),
                    "var_b": float(vb.mean(dtype=np.float64)),
                })
            rows[thr_name][p] = per
    out["rows"] = rows

    (DATA / "01-dark-iso-sweep.json").write_text(json.dumps(out, indent=1))
    print(f"wrote {DATA / '01-dark-iso-sweep.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

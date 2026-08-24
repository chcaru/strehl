"""M72 step 1 -- PRE-REGISTRATION and the measurement.

=============================================================================
                            PRE-REGISTRATION
    Committed before any corpus frame is decoded.  Nothing below this
    banner was written after seeing a result.  Rule 41.
=============================================================================

SECTION 0 -- prior work read before writing this (rule 40)

  Searched docs/research/ for "conversion gain", "PTC", "dark", "per-plane",
  "correlat", "covarian", "G1/G2", "0.073", "0.5365".  Files found and read,
  in full or in the cited section:

    M62-sqrt-n.md          sections 9, 9.1, 10 -- THE SOURCE.  P17 is fact 895.
    M61-ptc-high-iso-measured.md  section 4.13 (facts 59, 60) -- the design
                           I am running, including the pairing geometry it
                           fixed in advance; section 4.12 for the alpha/delta
                           argument I reuse.
    M68-b-plane-mechanism.md      my own, sections 1, 4, 7 -- the alpha/delta
                           instrument, and the G2/G1 null control that ran at
                           0.99937 +/- 0.00511.
    M48c-defect-layer-measured.md  the 13 630 recurrent hot pixels and the
                           exclusion criterion I reuse.
    M4-fpn-measured.md     section 8.1 dark sigma per ISO per plane (the C0
                           cross-check table), section 8.2 dark sigma.
    M48-read-noise-measured.md, M48b-fpn-rho-measured.md  -- M48b is SPATIAL
                           rho (fixed-pattern), a different object from this
                           TEMPORAL rho; read to be sure I was not about to
                           re-run it.
    SYNTHESIS.md           facts 895, 958 (read only; never edited).
    crates/strehl-core/src/noise.rs       green_luma_sigma at line 126, and
                           the independence assumption stated in words at
                           line 122.
    crates/strehl-core/src/merge.rs       green_mean at line 937,
                           0.5*(G1+G2) at the SAME cell index -- this fixes
                           the pairing geometry the fix must use.
    crates/strehl-core/src/plane.rs       green_luma at line 71.
    crates/strehl-core/src/stack.rs       roi_green at line 624.
    crates/strehl-core/src/profile.rs     read, not modified.

  Settled and NOT reopened: M62's P15 (frame-to-frame temporal independence,
  sqrt(N) to 1 %) -- this rho is a WITHIN-frame BETWEEN-plane correlation and
  does not contradict it.  M68's alpha/delta fit and its B-plane result.
  M48c's defect census.

SECTION 1 -- hypotheses.  The space is enumerated, not assumed closed.

  H0  rho = 0.  Fact 895 is an artefact of M62's difference-of-variances
      estimator, whose error amplification is ~15x (step 0, section 2).
      CONSEQUENCE: fact 895 withdrawn, the item closes permanently.

  H1  Uniform per-frame common mode -- supply, black-level, temperature.
      Adds an identical offset to every cell, so it correlates EVERY pair of
      planes equally and survives arbitrary spatial displacement.
      CONSEQUENCE: real but not a plane property.  The fix is a per-frame
      pedestal subtraction, not a green covariance.

  H2  Local green-specific coupling -- something shared by the two green
      photosites and not by R or B.
      CONSEQUENCE: belongs in noise.rs as a green covariance term.

  H3  Local coupling that is NOT green-specific: a property of the diagonal
      pairing within a 2x2 cell, showing equally on R-B.
      CONSEQUENCE: belongs in the model as a per-pair covariance matrix, and
      green is not special.

  H4  Shared sensor ROW.  On this body's [[0,1],[3,2]] RGBG layout,
      R(even,even) and G1(even,odd) share a row; G2(odd,even) and B(odd,odd)
      share a row.  G1 and G2 share NO row.
      CONSEQUENCE: a row-wise term; would NOT explain a G1/G2 correlation.

  H5  Shared sensor COLUMN.  R and G2 share even columns; G1 and B share odd
      columns.  G1 and G2 share NO column.
      CONSEQUENCE: a column-wise term; would NOT explain a G1/G2 correlation.

  H6  Signal-proportional crosstalk -- charge or optical leakage between
      neighbouring photosites, cov = k g S.
      DECLARED NOW: a dark frame has S ~ 0 and is STRUCTURALLY BLIND to H6.
      No result in this report, of any sign, can exclude it.  A null in the
      dark means "no read-domain covariance", never "no covariance".

  H7  Decode.  Excluded a priori on prior work: rawpy raw_image_visible is
      pre-demosaic, and M61 measured rawler bit-identical to LibRaw (max
      difference 0).  Listed so the exclusion is on the record.

  H0 and H1 are artefact/nuisance; H2-H5 are model content; H6 is outside
  the reach of the instrument.  I do not claim this list is exhaustive; I
  claim it is the list I wrote down before measuring.

SECTION 2 -- observables

  O1  Direct pooled per-cell TEMPORAL correlation for all 6 plane pairs.
      Per-cell temporal mean removed (this removes fixed-pattern offset
      exactly); cross-products pooled over cells before normalising.  No
      difference of variances anywhere -- this is the independent instrument.
  O2  Temporal covariance matrix of the PER-FRAME SPATIAL MEANS of the four
      planes.  This measures H1's uniform common mode DIRECTLY rather than
      inferring it.
  O3  Frame-permutation null: a fixed derangement of the 20 frame indices
      (seed 20250823).  Destroys any genuine temporal correlation while
      preserving every spatial statistic.
  O4  Cell-displacement null: plane 2 offset by (dr, dc) = (401, 401) plane
      cells.  Shares no local structure; retains anything uniform.
  O5  M61's PRE-FIXED within-plane geometry: for each plane, the temporal
      correlation of horizontal in-plane neighbours (same sensor row,
      columns 2 apart) against vertical in-plane neighbours (same sensor
      column, rows 2 apart).
  O6  cov(ISO) fitted as alpha_c G^2 + delta_c, the same two-term
      upstream/downstream decomposition M68 validated for the variance.

  ALL rho reported for the ISO question carry Sheppard's correction,
  var -> var - 1/12, for the reason derived in step 0 section 5f: the
  quantisation dilution is ISO-DEPENDENT by ~8 % across the range on disk
  and biases in the direction that mimics an upstream covariance.  The
  uncorrected value is reported alongside every corrected one.

SECTION 3 -- data and ISO range

  D:\\macro-dark-frames, 11 groups of 22, ISO 50 to 2000.  First 2 frames of
  every group discarded as the owner's stabilisation shots; 20 kept.
  Group 118MSDCF is M62's own group and is the replication target for C1.
  Read-only.  D:\\personal\\macro\\flat-fields is NOT touched: M71 owns it.

SECTION 4 -- exclusions

  Defects: M48c criterion B on each plane's temporal-mean map, 6.0 x MAD
  against the 4-neighbour median.  A cell is dropped if ANY of the four
  planes flags it, so all six pairs are computed on an IDENTICAL cell set.
  Border row/column excluded.  Robustness arms at 3.0 x MAD and no
  exclusion at all.  Direction fixed in advance (step 0, 5e): defects
  inflate variance and therefore DILUTE rho, so exclusion RAISES it.

SECTION 5 -- criteria, each with its consequence

  C0  INSTRUMENT, void-on-fail.  Synthetic Gaussian null |rho| <= 0.005 AND
      real-data frame-permutation null |rho| <= 0.005.  If either fails, no
      rho in this report stands and the milestone reports that.

  C1  REPLICATION at ISO 100, group 118MSDCF, pair G1-G2, Sheppard-corrected:
        |rho - 0.073| <= 0.020         -> REPLICATED
        |rho|         <= 0.010         -> REFUTED; fact 895 withdrawn,
                                          item closes permanently
        otherwise                      -> PARTIAL: report the number and
                                          decline to label it

  C2  GREEN-SPECIFICITY, the control that can fail.  R-B is the OTHER
      diagonal pair in the 2x2 cell: same geometry as G1-G2, different
      colours.  With d = rho(R,B) and r = rho(G1,G2):
        |d - r| <= 0.010               -> NOT green-specific (H3)
        d <= 0.3 r                     -> green-specific (H2)
        otherwise                      -> intermediate; report both, name
                                          neither
      If C1 is REFUTED this criterion is not evaluated.

  C3  COMMON-MODE SHARE.  f_uniform = cov_from_frame_means / cov_per_cell:
        f >= 0.8                       -> H1; a per-frame pedestal
        f <= 0.2                       -> local
        otherwise                      -> mixed; report the split

  C4  GEOMETRY, M61's fixed pairing.  Compare the three pair classes
      {row: R-G1, G2-B}, {column: R-G2, G1-B}, {diagonal: G1-G2, R-B} on
      LOCAL covariance (uniform part removed), and O5's within-plane
      row-vs-column.  If the three classes agree within 0.010 the geometry
      does not discriminate and I say so.

  C5  MECHANISM LOCATION.  Fit cov(ISO) = alpha_c G^2 + delta_c per pair.
      Report the upstream fraction at base ISO with a leave-one-ISO-out
      jackknife.
      CANNOT-SEPARATE OUTCOME, declared in advance: if the jackknife bars on
      alpha_c and delta_c both span zero, OR if the Sheppard-corrected and
      uncorrected series disagree about the DIRECTION of the trend, C5 is
      reported as instrument-limited and NO mechanism is named.

  C6  OPERATIONAL REGIME, following the form of my own corrected M68 fact
      994: state the regime, not just the magnitude.  Compute the sigma
      error on green_luma_sigma across signal under H-read with the measured
      covariance.  PRE-DECLARED COMPARISON: M69 is finding FOCUS_NOISE_SD
      19-21 % off on real texture.  If the worst-case sigma error over the
      operating range is below 1/4 of that, the item is reported as
      IMMATERIAL IN PRACTICE regardless of whether rho is real.

  WHAT WOULD MAKE ME SAY THE OBSERVABLE CANNOT ANSWER THE QUESTION:
    - C5's cannot-separate outcome above, for mechanism location.
    - H6 for signal dependence, unconditionally: dark frames cannot see it.
    - If C2 lands intermediate AND C3 lands mixed, the mechanism is not
      determined by this instrument and I report that rather than choosing.

SECTION 6 -- non-blindness disclosure

  I already know fact 895's value (+0.073), its sign, and its published
  consequence (0.5365 sigma^2).  I am not blind to the target.  The
  mitigations are that the criteria above are numeric and committed before
  any decode, that C1 has a REFUTED branch with a stated consequence, that
  C2's control has a failing branch, and that the estimator is independent
  of the one that produced the number I am checking.

=============================================================================

Run:  python 01-green-correlation.py            (full sweep, ~11 groups)
      python 01-green-correlation.py --selftest (no corpus contact)
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

DARKS = Path(r"D:\macro-dark-frames")
HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"

DROP_FIRST = 2
T_FRAMES = 20
PEDESTAL = 512.0
QUANT_VAR = 1.0 / 12.0
PERM_SEED = 20250823
DISPLACE = (401, 401)

PLANES = ["R", "G1", "G2", "B"]
PLANE_OFFSET = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}

# The six unordered pairs, with their geometry class fixed here, before
# measuring, exactly as M61 section 4.13 requires.
PAIRS = [
    ("R", "G1", "row"),
    ("G2", "B", "row"),
    ("R", "G2", "column"),
    ("G1", "B", "column"),
    ("G1", "G2", "diagonal"),
    ("R", "B", "diagonal"),
]

M62_GROUP = "118MSDCF"
RHO_M62 = 0.073

C0_BAND = 0.005
C1_REPLICATE = 0.020
C1_REFUTE = 0.010
C2_SAME = 0.010
C2_SPECIFIC = 0.3
C3_UNIFORM = 0.8
C3_LOCAL = 0.2
C4_AGREE = 0.010
C6_MATERIAL_FRACTION = 0.25
M69_FOCUS_NOISE_SD_ERROR = 0.19


def read_iso(path: Path) -> int:
    import exifread

    with open(path, "rb") as fh:
        tags = exifread.process_file(fh, details=False, stop_tag="EXIF ISOSpeedRatings")
    for key in ("EXIF ISOSpeedRatings", "EXIF PhotographicSensitivity", "MakerNote ISOSetting"):
        if key in tags:
            v = tags[key].values
            return int(v[0] if isinstance(v, list) else v)
    raise KeyError(f"no ISO tag in {path}")


def decode_one(path: Path) -> np.ndarray:
    import rawpy

    with rawpy.imread(str(path)) as raw:
        pat = raw.raw_pattern.tolist()
        desc = raw.color_desc
        if pat != [[0, 1], [3, 2]] or desc != b"RGBG":
            raise RuntimeError(f"unexpected CFA layout {pat} {desc!r} in {path.name}")
        # rule 32: raw_image_visible is a view into LibRaw memory; copy inside.
        return (raw.raw_image_visible.astype(np.int32) - int(PEDESTAL)).astype(np.int16)


def load_group(folder: Path) -> tuple[int, np.ndarray]:
    files = sorted(folder.glob("DSC*.ARW"))
    if len(files) != 22:
        raise RuntimeError(f"{folder.name}: expected 22 files, found {len(files)}")
    isos = {read_iso(f) for f in files}
    if len(isos) != 1:
        raise RuntimeError(f"{folder.name} is not uniform in ISO: {sorted(isos)}")
    keep = files[DROP_FIRST:]
    if len(keep) != T_FRAMES:
        raise RuntimeError(f"{folder.name}: {len(keep)} frames after dropping {DROP_FIRST}")
    with ThreadPoolExecutor(max_workers=6) as pool:
        frames = list(pool.map(decode_one, keep))
    shapes = {f.shape for f in frames}
    if len(shapes) != 1:
        raise RuntimeError(f"{folder.name}: mixed shapes {shapes}")
    return isos.pop(), np.stack(frames, axis=0)


def split_plane(a: np.ndarray, plane: str) -> np.ndarray:
    r, c = PLANE_OFFSET[plane]
    return a[..., r::2, c::2]


def defect_flags(mean_plane: np.ndarray, k: float) -> np.ndarray:
    """M48c criterion B on one plane's temporal-mean map. Border excluded."""
    m = mean_plane.astype(np.float32)
    nb = np.stack([m[:-2, 1:-1], m[2:, 1:-1], m[1:-1, :-2], m[1:-1, 2:]], axis=0)
    nb.sort(axis=0)
    med = 0.5 * (nb[1] + nb[2])
    excess = m[1:-1, 1:-1] - med
    mad = np.median(np.abs(excess - np.median(excess)))
    sig = 1.4826 * float(mad)
    flags = np.ones(m.shape, bool)  # border counts as excluded
    flags[1:-1, 1:-1] = np.abs(excess) > k * sig
    return flags


def pooled_moments(x: np.ndarray, y: np.ndarray, mask: np.ndarray,
                   chunk: int = 64) -> tuple[float, float, float, int]:
    """Pooled Sxx, Syy, Sxy over masked cells, per-cell temporal mean removed.

    x, y are (T, h, w) float32.  Accumulation is float64 and chunked over
    rows so an 8.2 Mcell x 20 frame reduction does not lose precision.
    """
    t = x.shape[0]
    sxx = syy = sxy = 0.0
    n = 0
    for r0 in range(0, x.shape[1], chunk):
        r1 = min(r0 + chunk, x.shape[1])
        m = mask[r0:r1]
        if not m.any():
            continue
        xb = x[:, r0:r1][:, m].astype(np.float64)
        yb = y[:, r0:r1][:, m].astype(np.float64)
        xb -= xb.mean(axis=0, keepdims=True)
        yb -= yb.mean(axis=0, keepdims=True)
        sxx += float(np.einsum("ij,ij->", xb, xb))
        syy += float(np.einsum("ij,ij->", yb, yb))
        sxy += float(np.einsum("ij,ij->", xb, yb))
        n += int(m.sum())
    dof = n * (t - 1)
    return sxx / dof, syy / dof, sxy / dof, n


def rho_from(vxx: float, vyy: float, vxy: float, sheppard: bool) -> float:
    a, b = vxx, vyy
    if sheppard:
        a -= QUANT_VAR
        b -= QUANT_VAR
    if a <= 0 or b <= 0:
        return float("nan")
    return vxy / np.sqrt(a * b)


def derangement(t: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    while True:
        p = rng.permutation(t)
        if not np.any(p == np.arange(t)):
            return p


def analyse_group(name: str, iso: int, frames: np.ndarray) -> dict:
    out: dict = {"group": name, "iso": iso, "shape": list(frames.shape)}
    planes = {p: split_plane(frames, p).astype(np.float32) for p in PLANES}
    del frames

    # O2 -- the uniform common mode, measured directly from per-frame means.
    fm = {p: planes[p].mean(axis=(1, 2), dtype=np.float64) for p in PLANES}
    out["frame_means"] = {p: fm[p].tolist() for p in PLANES}
    out["frame_mean_span"] = {p: float(fm[p].max() - fm[p].min()) for p in PLANES}
    cm = {}
    for a, b, _ in PAIRS:
        ca = fm[a] - fm[a].mean()
        cb = fm[b] - fm[b].mean()
        cm[f"{a}-{b}"] = float((ca * cb).sum() / (T_FRAMES - 1))
    out["frame_mean_cov"] = cm

    means = {p: planes[p].mean(axis=0) for p in PLANES}
    out["plane_mean_dn"] = {p: float(means[p].mean()) for p in PLANES}

    perm = derangement(T_FRAMES, PERM_SEED)
    out["permutation"] = perm.tolist()
    out["arms"] = {}

    for arm, k in (("k6", 6.0), ("k3", 3.0), ("none", None)):
        if k is None:
            bad = np.zeros(means["R"].shape, bool)
            bad[0, :] = bad[-1, :] = bad[:, 0] = bad[:, -1] = True
        else:
            bad = np.zeros(means["R"].shape, bool)
            for p in PLANES:
                bad |= defect_flags(means[p], k)
        good = ~bad
        rec: dict = {"retained": float(good.mean()), "cells": int(good.sum()), "pairs": {}}

        for a, b, cls in PAIRS:
            vxx, vyy, vxy, n = pooled_moments(planes[a], planes[b], good)
            entry = {
                "class": cls,
                "var_a": vxx, "var_b": vyy, "cov": vxy, "n": n,
                "rho_raw": rho_from(vxx, vyy, vxy, False),
                "rho_shep": rho_from(vxx, vyy, vxy, True),
            }
            # O3 -- frame permutation null.
            _, _, cxy_p, _ = pooled_moments(planes[a], planes[b][perm], good)
            entry["cov_perm"] = cxy_p
            entry["rho_perm"] = rho_from(vxx, vyy, cxy_p, True)
            # O4 -- cell displacement null.
            dr, dc = DISPLACE
            h, w = good.shape
            g2 = good[:h - dr, :w - dc] & good[dr:, dc:]
            vxx2, vyy2, vxy2, _ = pooled_moments(
                planes[a][:, :h - dr, :w - dc], planes[b][:, dr:, dc:], g2)
            entry["cov_disp"] = vxy2
            entry["rho_disp"] = rho_from(vxx2, vyy2, vxy2, True)
            rec["pairs"][f"{a}-{b}"] = entry

        # O5 -- M61's within-plane geometry, fixed before measuring.
        rec["within"] = {}
        for p in PLANES:
            h, w = good.shape
            gh = good[:, :w - 1] & good[:, 1:]
            vxx, vyy, vxy, _ = pooled_moments(planes[p][:, :, :w - 1],
                                              planes[p][:, :, 1:], gh)
            same_row = rho_from(vxx, vyy, vxy, True)
            gv = good[:h - 1, :] & good[1:, :]
            vxx, vyy, vxy, _ = pooled_moments(planes[p][:, :h - 1, :],
                                              planes[p][:, 1:, :], gv)
            same_col = rho_from(vxx, vyy, vxy, True)
            rec["within"][p] = {"same_row": same_row, "same_col": same_col}

        out["arms"][arm] = rec

    return out


def synthetic_null() -> dict:
    """C0 -- the identical estimator on data where no correlation can exist."""
    rng = np.random.default_rng(PERM_SEED)
    h, w = 600, 900
    a = rng.normal(0.0, 1.0, (T_FRAMES, h, w)).astype(np.float32)
    b = rng.normal(0.0, 1.0, (T_FRAMES, h, w)).astype(np.float32)
    a += rng.normal(0.0, 30.0, (h, w)).astype(np.float32)  # fixed pattern
    b += rng.normal(0.0, 30.0, (h, w)).astype(np.float32)
    a = np.rint(a).astype(np.float32)
    b = np.rint(b).astype(np.float32)
    good = np.ones((h, w), bool)
    good[0, :] = good[-1, :] = good[:, 0] = good[:, -1] = False
    vxx, vyy, vxy, n = pooled_moments(a, b, good)
    perm = derangement(T_FRAMES, PERM_SEED)
    _, _, vxy_p, _ = pooled_moments(a, b[perm], good)
    return {
        "cells": n,
        "rho_raw": rho_from(vxx, vyy, vxy, False),
        "rho_shep": rho_from(vxx, vyy, vxy, True),
        "rho_perm": rho_from(vxx, vyy, vxy_p, True),
        "var_a": vxx, "var_b": vyy,
    }


def selftest() -> int:
    print("M72 selftest -- no corpus contact")
    fails = 0

    print("\n  plane geometry, asserted against the layout the report claims:")
    a = np.zeros((4, 4), np.int16)
    for r in range(4):
        for c in range(4):
            a[r, c] = 10 * r + c
    for p, (r, c) in PLANE_OFFSET.items():
        got = split_plane(a, p)
        print(f"    {p:2s} offset {(r, c)}  ->  {got.ravel().tolist()}")
    row_pairs = [(x, y) for x, y, cls in PAIRS if cls == "row"]
    for x, y in row_pairs:
        if PLANE_OFFSET[x][0] != PLANE_OFFSET[y][0]:
            print(f"    FAIL {x}-{y} labelled row but rows differ")
            fails += 1
    for x, y, cls in PAIRS:
        if cls == "column" and PLANE_OFFSET[x][1] != PLANE_OFFSET[y][1]:
            print(f"    FAIL {x}-{y} labelled column but columns differ")
            fails += 1
        if cls == "diagonal" and (PLANE_OFFSET[x][0] == PLANE_OFFSET[y][0]
                                  or PLANE_OFFSET[x][1] == PLANE_OFFSET[y][1]):
            print(f"    FAIL {x}-{y} labelled diagonal but shares a row or column")
            fails += 1
    if not fails:
        print("    ok  all six pair classes match the CFA offsets")

    print("\n  derangement:")
    p = derangement(T_FRAMES, PERM_SEED)
    print(f"    {p.tolist()}")
    if np.any(p == np.arange(T_FRAMES)):
        print("    FAIL not a derangement")
        fails += 1
    else:
        print("    ok  no frame keeps its partner")

    print("\n  C0 synthetic null (identical code path, no correlation exists):")
    s = synthetic_null()
    print(f"    cells {s['cells']}  var_a {s['var_a']:.5f}  var_b {s['var_b']:.5f}")
    print(f"    rho_raw  {s['rho_raw']:+.6f}")
    print(f"    rho_shep {s['rho_shep']:+.6f}")
    print(f"    rho_perm {s['rho_perm']:+.6f}")
    for key in ("rho_raw", "rho_shep", "rho_perm"):
        if abs(s[key]) > C0_BAND:
            print(f"    FAIL {key} outside +/-{C0_BAND}")
            fails += 1
    if not fails:
        print(f"    ok  all within +/-{C0_BAND}")

    print("\n  planted recovery through pooled_moments:")
    rng = np.random.default_rng(7)
    h, w = 400, 600
    shared = rng.normal(0, 1, (T_FRAMES, h, w)).astype(np.float32)
    want = 0.073
    x = (np.sqrt(want) * shared
         + np.sqrt(1 - want) * rng.normal(0, 1, (T_FRAMES, h, w))).astype(np.float32)
    y = (np.sqrt(want) * shared
         + np.sqrt(1 - want) * rng.normal(0, 1, (T_FRAMES, h, w))).astype(np.float32)
    good = np.ones((h, w), bool)
    vxx, vyy, vxy, _ = pooled_moments(x, y, good)
    got = rho_from(vxx, vyy, vxy, False)
    ok = abs(got - want) < 0.006
    print(f"    planted {want:+.4f}  recovered {got:+.6f}  {'ok' if ok else 'FAIL'}")
    if not ok:
        fails += 1

    print()
    print("FAILED" if fails else "selftest OK")
    return fails


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    DATA.mkdir(parents=True, exist_ok=True)
    folders = sorted(d for d in DARKS.iterdir() if d.is_dir())
    print(f"M72 sweep over {len(folders)} groups")
    results = []
    for folder in folders:
        iso, frames = load_group(folder)
        print(f"  {folder.name}  ISO {iso:5d}  frames {frames.shape}", flush=True)
        rec = analyse_group(folder.name, iso, frames)
        g = rec["arms"]["k6"]["pairs"]["G1-G2"]
        print(f"      G1-G2 rho_shep {g['rho_shep']:+.5f}  "
              f"perm {g['rho_perm']:+.5f}  disp {g['rho_disp']:+.5f}", flush=True)
        results.append(rec)

    payload = {
        "planes": PLANES,
        "pairs": [list(p) for p in PAIRS],
        "drop_first": DROP_FIRST,
        "t_frames": T_FRAMES,
        "displace": list(DISPLACE),
        "perm_seed": PERM_SEED,
        "synthetic_null": synthetic_null(),
        "groups": results,
    }
    path = DATA / "01-green-correlation.json"
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Split the half-stack disagreement into the part a REGISTRATION error could
explain and the part only an incoherent CHOICE can explain.

THE DISCRIMINATOR.  Two hypotheses predict that two independent halves of a
stack disagree, and they predict different SHAPES of disagreement:

  alignment error   the halves are solved separately, so they can land on
                    slightly different geometry.  That is a similarity warp,
                    and to first order it makes the half-difference a linear
                    combination of the half-sum's own gradients.  COHERENT.
  selection error   the halves pick different frames -- different focus planes
                    -- at the same pixel.  Nothing about that is a warp of the
                    other half.  INCOHERENT.

So regress the half-difference D = A - B onto the basis that a similarity warp
plus an exposure difference spans:

    [ S, Sx, Sy, x*Sx + y*Sy, -y*Sx + x*Sy ]      S = (A + B) / 2

  S                 gain: the two halves differ in exposure
  Sx, Sy            translation
  x*Sx + y*Sy       scale (the coverage crop k differing between halves)
  -y*Sx + x*Sy      rotation

Whatever survives that fit is disagreement that NO registration error and NO
exposure difference between the halves can account for.  That residual is the
quantity the over-selection prediction is about, and this lane is the one that
can separate it, because separating a warp from everything else is what its
instruments already do.

BANDS.  Everything is reported as a ratio to the half-sum's own amplitude in
the same band, at BUILD-TRIAGE's `high` = 0.30-0.45 cycles per SENSOR sample
evaluated at f*k in each arm's grid.  A raw residual energy would scale with
scene contrast and could not be compared between subjects or depths.

REGISTRATION OF THE PAIR IS INTEGER-ONLY.  Sub-pixel resampling adds blur to
the very quantity being measured, so the partner tile is located on an integer
grid and any residual sub-pixel and scale difference is left for the basis
above to absorb -- which is precisely what it is there for.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402
from detail import ncc_offset, pick_sites  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
TILE = 256
SEARCH = 48


def basis(S: np.ndarray) -> np.ndarray:
    """Similarity-warp + gain basis for the half-difference, columns as vectors."""
    n = S.shape[0]
    Sy, Sx = np.gradient(S)
    c = np.arange(n) - (n - 1) / 2.0
    Y, X = np.meshgrid(c, c, indexing="ij")
    cols = [S, Sx, Sy, X * Sx + Y * Sy, -Y * Sx + X * Sy]
    return np.stack([c.ravel() for c in cols], axis=1)


def decompose(A: np.ndarray, B: np.ndarray, k: float, band: str = "high") -> dict:
    """Return the band-ratioed total, registration-explained and residual parts.

    `band` NAMES THE SCORING BAND and is a parameter because the first version of
    this instrument hardcoded `high` = 0.30-0.45 cyc/px, a period of 2.2-3.3 px,
    while the defect the fleet has actually convicted is a plateau at 20-60 px --
    a band roughly ten times coarser, which `tri.BANDS["low"]` (0.02-0.08 cyc/px,
    period 12.5-50 px) covers and `high` does not reach.  Measuring the wrong band
    does not return "no effect", it returns no information, and the two look
    identical in the output.  The dict keys keep their `high_*` spelling so the
    already-published high-band rows reproduce byte-for-byte; read them as
    "scoring-band" throughout.
    """
    S = 0.5 * (A + B)
    D = A - B
    M = basis(S)
    coef, *_ = np.linalg.lstsq(M, D.ravel(), rcond=None)
    fit = (M @ coef).reshape(D.shape)
    R = D - fit

    hs = tri.band_amp(S, k)[band]
    return {
        "high_S": hs,
        # Coherence-blind companion, required because every other number here is
        # a coherence statistic and would move if the halves merely agreed more.
        # A single half's own high-band amplitude counts the detail it contains
        # whether or not the other half agrees about it.  Note the V-DRIFT
        # section 8 hazard: this rises under geometric damage (ghosting adds
        # high-frequency energy), so it is a detail-PRESENCE statistic and must
        # never be read as a quality score.
        "high_A": tri.band_amp(A, k)[band],
        "high_B": tri.band_amp(B, k)[band],
        "dis": tri.band_amp(D, k)[band] / hs,
        "reg": tri.band_amp(fit, k)[band] / hs,
        "sel": tri.band_amp(R, k)[band] / hs,
        "explained": 1.0 - float((R * R).sum() / max((D * D).sum(), 1e-12)),
        # coef[1], coef[2] are the translation the fit attributes to the pair,
        # in pixels.  This is the residual sub-pixel misregistration BETWEEN the
        # two halves after integer matching, and it is what sets how much of
        # `sel` could be registration leak rather than selection.
        "dx": float(coef[1]), "dy": float(coef[2]),
        "shift_px": float(np.hypot(coef[1], coef[2])),
    }


def fshift(t: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Exact sub-pixel translation by a Fourier phase ramp: no interpolation blur."""
    ny, nx = t.shape
    fy = np.fft.fftfreq(ny)[:, None]
    fx = np.fft.fftfreq(nx)[None, :]
    ph = np.exp(-2j * np.pi * (fy * dy + fx * dx))
    return np.real(np.fft.ifft2(np.fft.fft2(t) * ph))


def leak_name(band: str, mode: str = "detail") -> str:
    """Calibration filename. The high/detail pair keeps the original name so the
    already-published rows keep reading the file they were computed against."""
    return ("half-leak.json" if (band, mode) == ("high", "detail")
            else f"half-leak-{band}-{mode}.json")


def leak_ratio(shift_px: float, band: str = "high", mode: str = "detail") -> float:
    """How much `sel` a pure registration error of this size produces, per unit `reg`.

    Measured by commission_half.py's two plant families: exact sub-pixel
    translation by Fourier phase ramp, and a centred scale change matching the
    coverage-crop difference between real halves.  The basis is a first-order
    model of a warp and part of a warp's energy escapes the fit.  That leak is
    proportional to `reg`, which makes it a calibration rather than a caveat.

    The WORST ratio over both families is used, not the interpolated one, so the
    subtraction errs toward removing too much and any surviving `sel_net`
    understates rather than overstates the incoherent part.

    THE CALIBRATION IS BAND-SPECIFIC AND IS NOT TRANSFERABLE.  The leak exists
    because a shift of d px is a phase error of 2*pi*f*d, so it grows with the
    scoring frequency: at 0.35 cyc/px a 0.2 px shift is a large phase error and
    the first-order basis fails, while at 0.05 cyc/px the same shift is small and
    the basis fits well.  Carrying the high-band ratio of 1.28 down to the low
    band would subtract several times the real leak and could manufacture a
    negative result out of nothing.  So each band gets its own file and a band
    with no calibration on disk REFUSES rather than borrowing one.
    """
    p = ROOT / leak_name(band, mode)
    if not p.exists():
        raise SystemExit(
            f"no leak calibration for band '{band}' support '{mode}' at {p}\n"
            f"run: python commission_half.py --band {band} --site-mode {mode}\n"
            "REFUSING to reuse another band's calibration -- the leak scales with "
            "the scoring frequency and borrowing it would corrupt sel_net.")
    cal = json.loads(p.read_text(encoding="utf-8"))
    rows = cal["shift"]
    near = float(np.interp(shift_px, [r["shift_px"] for r in rows],
                           [r["sel"] / max(r["reg"], 1e-12) for r in rows]))
    return max(near, cal.get("worst_leak_ratio", near))


def sites_flat(base: np.ndarray, k: float, n_sites: int, tile: int) -> list[tuple[int, int]]:
    """The LEAST detailed non-overlapping sites: where blotch and plateau live.

    `pick_sites` ranks tiles by mid-band amplitude DESCENDING and keeps the top
    n.  That is the correct sampling for a sharpness question and the wrong one
    for this question.  The defect under investigation is flat-region mottle --
    a 20-60 px plateau in areas with little scene detail -- so an instrument that
    samples only the most textured tiles in the frame is looking everywhere
    except where the defect was convicted.  This is the same failure shape the
    falsification lane self-caught: an aggregate taken over the wrong support.
    """
    return _rank_sites(base, k, n_sites, tile, reverse=False)


def sites_grid(base: np.ndarray, k: float, n_sites: int, tile: int) -> list[tuple[int, int]]:
    """Content-blind uniform grid: no selection bias toward or against the defect.

    Both `pick_sites` and `sites_flat` choose sites using the image itself, so
    each can be accused of sampling for its own answer.  A grid cannot be.  It
    is the arbiter when the detail-ranked and flat-ranked supports disagree.
    """
    H, W = base.shape
    m = SEARCH + 8
    ys = np.linspace(m, H - tile - m, int(np.ceil(np.sqrt(n_sites))), dtype=int)
    xs = np.linspace(m, W - tile - m, int(np.ceil(np.sqrt(n_sites))), dtype=int)
    return [(int(y), int(x)) for y in ys for x in xs][:n_sites]


def _rank_sites(base, k, n_sites, tile, reverse):
    H, W = base.shape
    m = SEARCH + 8
    step = tile // 2
    cand = []
    for y in range(m, H - tile - m, step):
        for x in range(m, W - tile - m, step):
            t = base[y:y + tile, x:x + tile]
            cand.append((tri.band_amp(t, k)["mid"], y, x))
    cand.sort(reverse=reverse)
    taken: list[tuple[int, int]] = []
    for _, y, x in cand:
        if all(abs(y - a) >= tile or abs(x - b) >= tile for a, b in taken):
            taken.append((y, x))
        if len(taken) == n_sites:
            break
    return taken


SITE_MODES = {"detail": pick_sites, "flat": sites_flat, "grid": sites_grid}


def pair(pa: Path, pb: Path, k: float, n_sites: int, tile: int,
         band: str = "high", mode: str = "detail", ncc_floor: float = 0.0) -> dict:
    A = tri.luma(tri.load16(str(pa)))
    B = tri.luma(tri.load16(str(pb)))
    sites = SITE_MODES[mode](A, k, n_sites, tile)
    out: dict[str, list[float]] = {"dis": [], "reg": [], "sel": [],
                                   "explained": [], "high_S": [], "ncc": [],
                                   "shift_px": [], "high_A": [], "high_B": []}
    rej_wall = rej_ncc = 0
    for (y, x) in sites:
        ta = A[y:y + tile, x:x + tile]
        hay = B[y - SEARCH:y + tile + SEARCH, x - SEARCH:x + tile + SEARCH]
        dy, dx, sc = ncc_offset(ta, hay)
        if dy in (0, 2 * SEARCH) or dx in (0, 2 * SEARCH):
            rej_wall += 1
            continue                      # peak against the wall: not a match
        # A flat tile has no NCC peak to speak of, so the argmax lands on noise
        # and the decomposition then measures a randomly-offset partner.  On the
        # flat and grid supports this is a live risk, so the match must clear a
        # floor.  Rejections are COUNTED, not silently dropped: a support that
        # loses most of its sites is a different measurement, not a quiet one.
        if sc < ncc_floor:
            rej_ncc += 1
            continue
        tb = B[y - SEARCH + dy:y - SEARCH + dy + tile,
               x - SEARCH + dx:x - SEARCH + dx + tile]
        r = decompose(ta, tb, k, band)
        for key in ("dis", "reg", "sel", "explained", "high_S", "shift_px",
                    "high_A", "high_B"):
            out[key].append(r[key])
        out["ncc"].append(sc)
    med = {key: (float(np.median(v)) if v else float("nan")) for key, v in out.items()}
    lr = leak_ratio(med["shift_px"], band, mode)
    med["leak_ratio"] = lr
    med["sel_net"] = med["sel"] - lr * med["reg"]
    med["n_sites"] = len(out["dis"])
    med["n_asked"] = len(sites)
    med["rej_wall"] = rej_wall
    med["rej_ncc"] = rej_ncc
    med["band"] = band
    med["site_mode"] = mode
    return med


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="flower")
    ap.add_argument("--sites", type=int, default=24)
    ap.add_argument("--tile", type=int, default=TILE)
    ap.add_argument("--ladder", default="n",
                    help="'n' = interleaved-subset ladder (partner separation "
                         "varies with N); 's' = fixed-separation control ladder")
    ap.add_argument("--band", default="high", choices=sorted(tri.BANDS),
                    help="scoring band. 'high' 0.30-0.45 cyc/px (period 2.2-3.3 px) "
                         "is what the first pass used; 'low' 0.02-0.08 cyc/px "
                         "(period 12.5-50 px) is the band the 20-60 px plateau "
                         "defect actually occupies")
    ap.add_argument("--site-mode", default="detail", choices=sorted(SITE_MODES),
                    help="'detail' = most textured tiles (sharpness support); "
                         "'flat' = least textured (where blotch lives); "
                         "'grid' = content-blind uniform")
    ap.add_argument("--ncc-floor", type=float, default=0.0,
                    help="reject sites whose partner match scores below this; "
                         "use ~0.5 on the flat and grid supports where a tile "
                         "may have no NCC peak at all")
    ap.add_argument("--tag", default="", help="suffix for the output json")
    a = ap.parse_args()

    recs = [json.loads(l) for l in
            (ROOT / f"half-{a.subject}.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    by_set: dict[str, dict] = {}
    for r in recs:
        if r["set"].startswith(a.ladder):
            by_set.setdefault(r["set"], {})[r["half"]] = r
    order = sorted((s for s, h in by_set.items() if set(h) == {"A", "B"}),
                   key=lambda s: by_set[s]["A"]["n_set"])

    lo_hz, hi_hz = tri.BANDS[a.band]
    print(f"band {a.band} = {lo_hz}-{hi_hz} cyc/px (period "
          f"{1/hi_hz:.1f}-{1/lo_hz:.1f} px)   support '{a.site_mode}'   "
          f"ncc floor {a.ncc_floor:.2f}")
    print(f"{'set':6s} {'N set':>6s} {'N half':>7s} {'sep':>4s} {'kA':>7s} {'kB':>7s} "
          f"{'shift':>7s} {'registr':>8s} {'SEL_NET':>8s} {'SEL_ABS':>8s} "
          f"{'ampS':>7s} {'A/B':>5s} {'sites':>6s}")
    print("-" * 110)
    rows = []
    for name in order:
        ra, rb = by_set[name]["A"], by_set[name]["B"]
        k = 0.5 * (ra["k"] + rb["k"])
        m = pair(Path(ra["out"]), Path(rb["out"]), k, a.sites, a.tile,
                 a.band, a.site_mode, a.ncc_floor)
        m |= {"set": name, "n_set": ra["n_set"], "n_half": ra["n_half"],
              "kA": ra["k"], "kB": rb["k"], "subject": a.subject,
              "sep": ra.get("sep", ra["stride"])}
        # Absolute incoherent amplitude.  sel_net is a RATIO to the half-sum's
        # own detail, and that denominator is not constant across a depth ladder,
        # so a falling ratio can mean "less disagreement" or merely "more
        # delivered detail".  Both are reported because on bee they disagree.
        m["sel_abs"] = m["sel_net"] * m["high_S"]
        m["ab"] = m["high_A"] / max(m["high_B"], 1e-9)
        rows.append(m)
        print(f"{name:6s} {ra['n_set']:6d} {ra['n_half']:7d} {m['sep']:4d} "
              f"{ra['k']:7.4f} {rb['k']:7.4f} {m['shift_px']:7.3f} "
              f"{m['reg']:8.4f} {m['sel_net']:8.4f} {m['sel_abs']:8.1f} "
              f"{m['high_S']:7.1f} {m['ab']:5.2f} "
              f"{m['n_sites']:3d}/{m['n_asked']:<3d}")

    drop = [m for m in rows if m["n_sites"] < 0.6 * m["n_asked"]]
    for m in drop:
        print(f"\n  WARNING {m['set']}: only {m['n_sites']} of {m['n_asked']} sites "
              f"survived ({m['rej_wall']} wall, {m['rej_ncc']} ncc).\n"
              "  This support is thin enough that its median is a different "
              "estimator than the others'.")

    for m in rows:
        if not 0.8 < m["ab"] < 1.25:
            print(f"\n  WARNING {m['set']}: the two halves differ in their own "
                  f"high-band amplitude by {m['ab']:.2f}x.\n"
                  "  They are not interchangeable samples of the same scene, so this "
                  "row's\n  disagreement is partly a content difference and not a "
                  "merge property.")

    if len(rows) >= 2:
        lo, hi = rows[0], rows[-1]
        print(f"\nIncoherent disagreement -- what no registration difference or "
              f"exposure\ndifference between the halves can account for.  Subject "
              f"{a.subject}, band\n{a.band} {lo_hz}-{hi_hz} cyc/px, support "
              f"'{a.site_mode}', {lo['n_half']}-frame halves "
              f"(N={lo['n_set']}) -> {hi['n_half']}-frame halves (N={hi['n_set']}):")
        print(f"  as a fraction of delivered detail : {lo['sel_net']:.4f} -> "
              f"{hi['sel_net']:.4f}  ({hi['sel_net']/lo['sel_net']:.2f}x)")
        print(f"  absolute amplitude               : {lo['sel_abs']:.1f} -> "
              f"{hi['sel_abs']:.1f}  ({hi['sel_abs']/lo['sel_abs']:.2f}x)")
        print(f"  registration part, for contrast  : {lo['reg']:.4f} -> "
              f"{hi['reg']:.4f}  ({hi['reg']/lo['reg']:.2f}x)")
        print(f"  fitted inter-half shift          : {lo['shift_px']:.3f} -> "
              f"{hi['shift_px']:.3f} px  ({hi['shift_px']/lo['shift_px']:.2f}x)")
        print(f"  coherence-blind: one half's own {a.band}-band amplitude "
              f"{lo['high_A']:.1f} -> {hi['high_A']:.1f} "
              f"({hi['high_A']/lo['high_A']:.2f}x)")
        print("\nThe prediction under test is that the incoherent part RISES with N.")

    tag = a.tag or (f"-{a.band}-{a.site_mode}"
                    if (a.band, a.site_mode) != ("high", "detail") else "")
    (ROOT / f"halfmetric-{a.subject}-{a.ladder}{tag}.json").write_text(
        json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

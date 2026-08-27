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


def decompose(A: np.ndarray, B: np.ndarray, k: float) -> dict:
    """Return the band-ratioed total, registration-explained and residual parts."""
    S = 0.5 * (A + B)
    D = A - B
    M = basis(S)
    coef, *_ = np.linalg.lstsq(M, D.ravel(), rcond=None)
    fit = (M @ coef).reshape(D.shape)
    R = D - fit

    hs = tri.band_amp(S, k)["high"]
    return {
        "high_S": hs,
        # Coherence-blind companion, required because every other number here is
        # a coherence statistic and would move if the halves merely agreed more.
        # A single half's own high-band amplitude counts the detail it contains
        # whether or not the other half agrees about it.  Note the V-DRIFT
        # section 8 hazard: this rises under geometric damage (ghosting adds
        # high-frequency energy), so it is a detail-PRESENCE statistic and must
        # never be read as a quality score.
        "high_A": tri.band_amp(A, k)["high"],
        "high_B": tri.band_amp(B, k)["high"],
        "dis": tri.band_amp(D, k)["high"] / hs,
        "reg": tri.band_amp(fit, k)["high"] / hs,
        "sel": tri.band_amp(R, k)["high"] / hs,
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


def leak_ratio(shift_px: float) -> float:
    """How much `sel` a pure registration error of this size produces, per unit `reg`.

    Measured by commission_half.py's two plant families: exact sub-pixel
    translation by Fourier phase ramp, and a centred scale change matching the
    coverage-crop difference between real halves.  The basis is a first-order
    model of a warp and the scoring band's period is only 2.2-3.3 px, so part of
    a warp's energy escapes the fit.  That leak is proportional to `reg`, which
    makes it a calibration rather than a caveat.

    The WORST ratio over both families is used, not the interpolated one, so the
    subtraction errs toward removing too much and any surviving `sel_net`
    understates rather than overstates the incoherent part.
    """
    p = ROOT / "half-leak.json"
    if not p.exists():
        raise SystemExit("run commission_half.py first: no leak calibration on disk")
    cal = json.loads(p.read_text(encoding="utf-8"))
    rows = cal["shift"]
    near = float(np.interp(shift_px, [r["shift_px"] for r in rows],
                           [r["sel"] / max(r["reg"], 1e-12) for r in rows]))
    return max(near, cal.get("worst_leak_ratio", near))


def pair(pa: Path, pb: Path, k: float, n_sites: int, tile: int) -> dict:
    A = tri.luma(tri.load16(str(pa)))
    B = tri.luma(tri.load16(str(pb)))
    sites = pick_sites(A, k, n_sites, tile)
    out: dict[str, list[float]] = {"dis": [], "reg": [], "sel": [],
                                   "explained": [], "high_S": [], "ncc": [],
                                   "shift_px": [], "high_A": [], "high_B": []}
    for (y, x) in sites:
        ta = A[y:y + tile, x:x + tile]
        hay = B[y - SEARCH:y + tile + SEARCH, x - SEARCH:x + tile + SEARCH]
        dy, dx, sc = ncc_offset(ta, hay)
        if dy in (0, 2 * SEARCH) or dx in (0, 2 * SEARCH):
            continue                      # peak against the wall: not a match
        tb = B[y - SEARCH + dy:y - SEARCH + dy + tile,
               x - SEARCH + dx:x - SEARCH + dx + tile]
        r = decompose(ta, tb, k)
        for key in ("dis", "reg", "sel", "explained", "high_S", "shift_px",
                    "high_A", "high_B"):
            out[key].append(r[key])
        out["ncc"].append(sc)
    med = {key: (float(np.median(v)) if v else float("nan")) for key, v in out.items()}
    lr = leak_ratio(med["shift_px"])
    med["leak_ratio"] = lr
    med["sel_net"] = med["sel"] - lr * med["reg"]
    med["n_sites"] = len(out["dis"])
    return med


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="flower")
    ap.add_argument("--sites", type=int, default=24)
    ap.add_argument("--tile", type=int, default=TILE)
    ap.add_argument("--ladder", default="n",
                    help="'n' = interleaved-subset ladder (partner separation "
                         "varies with N); 's' = fixed-separation control ladder")
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

    print(f"{'set':6s} {'N set':>6s} {'N half':>7s} {'sep':>4s} {'kA':>7s} {'kB':>7s} "
          f"{'shift':>7s} {'registr':>8s} {'SEL_NET':>8s} {'SEL_ABS':>8s} "
          f"{'highS':>7s} {'A/B':>5s} {'sites':>6s}")
    print("-" * 104)
    rows = []
    for name in order:
        ra, rb = by_set[name]["A"], by_set[name]["B"]
        k = 0.5 * (ra["k"] + rb["k"])
        m = pair(Path(ra["out"]), Path(rb["out"]), k, a.sites, a.tile)
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
              f"{m['high_S']:7.1f} {m['ab']:5.2f} {m['n_sites']:6d}")

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
              f"{a.subject}, band\n0.30-0.45 cyc/px, {lo['n_half']}-frame halves "
              f"(N={lo['n_set']}) -> {hi['n_half']}-frame halves (N={hi['n_set']}):")
        print(f"  as a fraction of delivered detail : {lo['sel_net']:.4f} -> "
              f"{hi['sel_net']:.4f}  ({hi['sel_net']/lo['sel_net']:.2f}x)")
        print(f"  absolute amplitude               : {lo['sel_abs']:.1f} -> "
              f"{hi['sel_abs']:.1f}  ({hi['sel_abs']/lo['sel_abs']:.2f}x)")
        print(f"  registration part, for contrast  : {lo['reg']:.4f} -> "
              f"{hi['reg']:.4f}  ({hi['reg']/lo['reg']:.2f}x)")
        print(f"  fitted inter-half shift          : {lo['shift_px']:.3f} -> "
              f"{hi['shift_px']:.3f} px  ({hi['shift_px']/lo['shift_px']:.2f}x)")
        print(f"  coherence-blind: one half's own high-band amplitude "
              f"{lo['high_A']:.1f} -> {hi['high_A']:.1f} "
              f"({hi['high_A']/lo['high_A']:.2f}x)")
        print("\nThe prediction under test is that the incoherent part RISES with N.")

    (ROOT / f"halfmetric-{a.subject}-{a.ladder}.json").write_text(
        json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

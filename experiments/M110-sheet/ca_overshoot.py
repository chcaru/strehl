"""Does the extrapolated CA correction OVERSHOOT past r = 0.788, and does it
narrow fringes or only recolour them?

Two questions that the |R-Y| magnitude cannot answer, because a magnitude that
falls is consistent with both "the fringe was removed" and "the fringe flipped
polarity and regrew smaller". They need the SIGN and they need SPACE.

Q1 OVERSHOOT. An over-large extrapolated `eps_r` does not fail by leaving the
fringe alone; it fails by pushing red past register, which REVERSES the fringe's
polarity. The signature is per-pixel and it is specific: the sign of R-Y flips
AND the magnitude grows. Either alone is innocent -- a flip with shrinkage is a
fringe correctly driven through neutral, and growth without a flip is not a
reversal. Only the conjunction is overshoot.

Gated to |R-Y|_off >= 1 display level, because below that the sign is decided by
rounding and every statistic built on it counts coin flips.

Floored against an RMS-matched inert null, because random noise also produces
flip-with-growth and the real number means nothing until it beats that.

Q2 WIDTH vs COLOUR. `eps_b` is None -- blue was never fitted -- so this is a
red-only correction on a red/cyan pair, and recolouring without narrowing is a
real possible outcome. Measured as the chroma profile in bands of distance from
a strong edge: if the fringe genuinely narrows, the outer bands must improve
proportionally more than the core, because the tail is what retracts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT_ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
DN_PER_LEVEL = 257.0
SUPPORT = 0.788


def ry(img: np.ndarray) -> np.ndarray:
    f = img.astype(np.float32)
    y = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
    return f[:, :, 0] - y


def luma(img: np.ndarray) -> np.ndarray:
    f = img.astype(np.float32)
    return 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]


def grad(y: np.ndarray) -> np.ndarray:
    gy = np.zeros_like(y)
    gx = np.zeros_like(y)
    gy[1:-1, :] = np.abs(y[2:, :] - y[:-2, :])
    gx[:, 1:-1] = np.abs(y[:, 2:] - y[:, :-2])
    return gy + gx


def dilate(m: np.ndarray) -> np.ndarray:
    o = m.copy()
    o[1:, :] |= m[:-1, :]
    o[:-1, :] |= m[1:, :]
    o[:, 1:] |= m[:, :-1]
    o[:, :-1] |= m[:, 1:]
    return o


def radius(shape) -> np.ndarray:
    h, w = shape[:2]
    cy, cx = h / 2.0, w / 2.0
    return (np.hypot(np.arange(h, dtype=np.float32)[:, None] - cy,
                     np.arange(w, dtype=np.float32)[None, :] - cx)
            / float(np.hypot(cy, cx)))


def overshoot_by_radius(d_off, d_on, em, r, nbin=10) -> list[dict]:
    """P(sign flip AND magnitude grew), per radial bin, gated by visibility."""
    a_off, a_on = np.abs(d_off), np.abs(d_on)
    gate = a_off >= DN_PER_LEVEL
    sel0 = em & gate
    rows = []
    for k in range(nbin):
        lo, hi = k / nbin, (k + 1) / nbin
        sel = sel0 & ((r >= lo) & (r < hi) if k < nbin - 1 else (r >= lo))
        n = int(sel.sum())
        if n < 1000:
            continue
        flip = np.sign(d_off[sel]) != np.sign(d_on[sel])
        grew = a_on[sel] > a_off[sel]
        over = flip & grew
        rows.append({
            "r_lo": round(lo, 3), "r_hi": round(hi, 3), "n": n,
            "flip_pct": round(float(flip.mean() * 100), 2),
            "grew_pct": round(float(grew.mean() * 100), 2),
            "overshoot_pct": round(float(over.mean() * 100), 2),
            "mean_abs_on_when_over_lv": round(
                float(a_on[sel][over].mean() / DN_PER_LEVEL), 3) if over.any() else 0.0,
            "beyond_support": lo >= SUPPORT,
        })
    return rows


def width_profile(d_off, d_on, y_off, nband=6) -> list[dict]:
    """Chroma magnitude in bands of distance from a strong edge.

    Band 0 is the edge itself (top 2% of gradient); band k is the ring exactly
    k pixels out. If the correction genuinely NARROWS a fringe, the outer bands
    must improve proportionally more than the core, because narrowing is the
    tail retracting. If every band improves by roughly the same percentage, the
    profile has been scaled rather than contracted -- the fringe was recoloured,
    not narrowed.
    """
    g = grad(y_off)
    thr = float(np.percentile(g[::7, ::7], 98.0))
    core = g >= thr

    grown = [core]
    for _ in range(1, nband):
        grown.append(dilate(grown[-1]))

    rows = []
    for k in range(nband):
        band = grown[k] if k == 0 else (grown[k] & ~grown[k - 1])
        n = int(band.sum())
        if n < 1000:
            continue
        mo = float(np.abs(d_off[band]).mean())
        mn = float(np.abs(d_on[band]).mean())
        rows.append({
            "dist_px": k, "n": n,
            "abs_ry_off_dn": round(mo, 1), "abs_ry_on_dn": round(mn, 1),
            "delta_pct": round((mn - mo) / mo * 100, 2) if mo > 0 else None,
            "delta_levels8": round((mn - mo) / DN_PER_LEVEL, 3),
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", action="append", required=True)
    ap.add_argument("--off", default="default")
    ap.add_argument("--on", default="ca")
    a = ap.parse_args()

    report = {}
    for s in a.subject:
        off = tifffile.imread(str(OUT_ROOT / s / f"{a.off}.tif"))
        on = tifffile.imread(str(OUT_ROOT / s / f"{a.on}.tif"))
        y_off = luma(off)
        em = grad(y_off) >= float(np.percentile(grad(y_off)[::7, ::7], 90.0))
        r = radius(off.shape)
        d_off, d_on = ry(off), ry(on)

        # Inert null: same RMS red perturbation, no information in it.
        rms = float(np.sqrt(((on[:, :, 0].astype(np.float32)
                              - off[:, :, 0].astype(np.float32))[em] ** 2).mean()))
        rng = np.random.default_rng(1102)
        fake = off.astype(np.float32).copy()
        fake[:, :, 0] = np.clip(fake[:, :, 0] + rng.normal(0.0, rms, size=off.shape[:2]),
                                0, 65535)
        d_null = ry(fake.astype(np.uint16))

        print(f"\n=== {s}: {a.off} -> {a.on} ===")

        # N1 null control: identical input must show zero flips, zero overshoot.
        nn = overshoot_by_radius(d_off, d_off, em, r)
        worst = max(x["overshoot_pct"] for x in nn)
        print(f"  [{'PASS' if worst == 0.0 else 'FAIL'}] N1 null overshoot = {worst} "
              f"(want 0 exactly)")

        real = overshoot_by_radius(d_off, d_on, em, r)
        null = overshoot_by_radius(d_off, d_null, em, r)
        nullmap = {x["r_lo"]: x for x in null}

        print(f"  Q1 OVERSHOOT = P(sign flip AND magnitude grew), gated to "
              f"|R-Y|_off >= 1 display level")
        print(f"    {'r':>11} {'flip%':>7} {'grew%':>7} {'OVER%':>7} "
              f"{'inert%':>7} {'excess':>8}  support")
        for x in real:
            nx = nullmap.get(x["r_lo"], {})
            ex = x["overshoot_pct"] - nx.get("overshoot_pct", 0.0)
            flag = "EXTRAPOLATED" if x["beyond_support"] else ""
            print(f"    {x['r_lo']:.2f}-{x['r_hi']:.2f} {x['flip_pct']:>7.2f} "
                  f"{x['grew_pct']:>7.2f} {x['overshoot_pct']:>7.2f} "
                  f"{nx.get('overshoot_pct', 0.0):>7.2f} {ex:>+8.2f}  {flag}")

        wp = width_profile(d_off, d_on, y_off)
        print(f"  Q2 WIDTH: |R-Y| by distance from a strong edge "
              f"(top 2% gradient = band 0)")
        print(f"    {'dist':>5} {'n':>10} {'off DN':>9} {'on DN':>9} "
              f"{'d %':>8} {'d lv8':>8}")
        for x in wp:
            print(f"    {x['dist_px']:>5} {x['n']:>10} {x['abs_ry_off_dn']:>9.1f} "
                  f"{x['abs_ry_on_dn']:>9.1f} {str(x['delta_pct']):>8} "
                  f"{x['delta_levels8']:>8.3f}")
        report[s] = {"overshoot_real": real, "overshoot_inert_null": null,
                     "null_control_worst": worst, "width_profile": wp,
                     "matched_rms_dn": round(rms, 2)}

    dst = OUT_ROOT / f"ca_overshoot_{a.off}_vs_{a.on}.json"
    dst.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Resolve the confidence headroom SPATIALLY, because a whole-field mean can
hide a defect that lives in one part of the field.

WHY THIS EXISTS.  V-SELECT section 7 reported headroom -- the gap between the
shipped weighting and `--pyramid-select hard-max` on the same stack -- as a
single mean over the whole confidence map.  The falsification lane then reported
that one of its own instrument defects survived its self-test *because the test
asserted only the mean of a field whose defect was at the borders*.  That is the
same shape of error, and this lane's statistic has the same shape of exposure:

  - the convicted defect is flat-region mottle, a 20-60 px plateau in areas of
    LOW scene detail;
  - a mean over the whole field is dominated by the textured majority;
  - so a headroom that grows only in the flat regions would be diluted, and
    would read as a small effect.

So partition the field and report headroom per region.  Two partitions are used
because they fail differently: DETAIL QUARTILE targets the defect's convicted
support, and BORDER-VS-INTERIOR targets the exact geometry that fooled the
falsification lane.

COMMISSIONING IS SPATIAL TOO.  A region-wise statistic must be shown to (a) find
a planted offset in the region it was planted in, and (b) NOT report it in the
regions it was absent from.  A statistic that spreads a local plant across every
region would turn any localised effect into a global one and could not answer
the question this script exists to ask.  `--commission` does both, and it also
plants a NEGATIVE offset, because a gate that only ever sees damage passes a
damage-only test trivially.
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

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
HEAD = ROOT / "head"
BLOCK = 128
# The ladder rungs headroom.py already rendered, as (subject, N) pairs.
RUNGS = [("flower", 18), ("flower", 205), ("bee", 25), ("bee", 299)]


def conf(subject: str, n: int, arm: str) -> np.ndarray:
    p = HEAD / f"{subject}-h{n}-{arm}-conf.tif"
    a = tri.load16(str(p)).astype(np.float64)
    return a[..., 0] if a.ndim == 3 else a


def detail_field(subject: str, n: int, shape: tuple[int, int], k: float) -> np.ndarray:
    """Per-block mid-band amplitude of the DEFAULT merge, on the conf map's grid.

    The partition is defined by the delivered image, not by the confidence map,
    so the regions are a property of the scene rather than of the statistic
    being tested.  Defining them on the confidence map itself would let the
    statistic choose its own support and the comparison would be circular.
    """
    img = tri.luma(tri.load16(str(HEAD / f"{subject}-h{n}-default.tif")))
    by, bx = shape
    ys = np.linspace(0, img.shape[0], by + 1).astype(int)
    xs = np.linspace(0, img.shape[1], bx + 1).astype(int)
    out = np.zeros(shape)
    for i in range(by):
        for j in range(bx):
            t = img[ys[i]:ys[i + 1], xs[j]:xs[j + 1]]
            out[i, j] = _sq_amp(t, k)
    return out


def _sq_amp(t: np.ndarray, k: float) -> float:
    """Mid-band amplitude of a centred square crop; tri.spectrum wants a square."""
    s = min(t.shape)
    if s < 32:
        return float("nan")
    y0 = (t.shape[0] - s) // 2
    x0 = (t.shape[1] - s) // 2
    return tri.band_amp(t[y0:y0 + s, x0:x0 + s], k)["mid"]


def blocks(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Block means of `a` onto `shape`, matching detail_field's grid exactly."""
    by, bx = shape
    ys = np.linspace(0, a.shape[0], by + 1).astype(int)
    xs = np.linspace(0, a.shape[1], bx + 1).astype(int)
    out = np.zeros(shape)
    for i in range(by):
        for j in range(bx):
            out[i, j] = a[ys[i]:ys[i + 1], xs[j]:xs[j + 1]].mean()
    return out


def expand(bm: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Blow a block-grid mask up to a pixel grid using blocks()' own edges."""
    by, bx = bm.shape
    ys = np.linspace(0, shape[0], by + 1).astype(int)
    xs = np.linspace(0, shape[1], bx + 1).astype(int)
    out = np.zeros(shape)
    for i in range(by):
        for j in range(bx):
            out[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = bm[i, j]
    return out


def border_mask(shape: tuple[int, int], frac: float = 0.15) -> np.ndarray:
    by, bx = shape
    ry, rx = max(1, int(by * frac)), max(1, int(bx * frac))
    m = np.zeros(shape, dtype=bool)
    m[:ry, :] = m[-ry:, :] = True
    m[:, :rx] = m[:, -rx:] = True
    return m


def measure(subject: str, n: int, k: float, plant=None) -> dict:
    d = conf(subject, n, "default")
    h = conf(subject, n, "hardmax")
    if plant is not None:
        d = d + plant(d.shape)
    shape = (max(2, d.shape[0] // BLOCK), max(2, d.shape[1] // BLOCK))
    hb = blocks(d - h, shape)
    det = detail_field(subject, n, shape, k)

    ok = np.isfinite(det)
    q = np.full(shape, -1)
    if ok.sum():
        edges = np.nanpercentile(det[ok], [25, 50, 75])
        q[ok] = np.digitize(det[ok], edges)
    bm = border_mask(shape)
    return {
        "subject": subject, "n": n, "blocks": list(shape),
        "whole": float(hb.mean()),
        # Q0 is the FLATTEST quartile: the convicted support.
        "q0_flat": float(hb[q == 0].mean()), "q1": float(hb[q == 1].mean()),
        "q2": float(hb[q == 2].mean()), "q3_detail": float(hb[q == 3].mean()),
        "border": float(hb[bm].mean()), "interior": float(hb[~bm].mean()),
    }


KS = {("flower", 18): 0.9973, ("flower", 205): 0.9971,
      ("bee", 25): 0.9217, ("bee", 299): 0.9321}
COLS = ["whole", "q0_flat", "q1", "q2", "q3_detail", "border", "interior"]


def table(rows: list[dict], title: str) -> None:
    print(f"\n{title}")
    print(f"{'subject':8s} {'N':>4s} " + " ".join(f"{c:>10s}" for c in COLS))
    print("-" * (14 + 11 * len(COLS)))
    for r in rows:
        print(f"{r['subject']:8s} {r['n']:4d} "
              + " ".join(f"{r[c]:10.2f}" for c in COLS))
    for subj in ("flower", "bee"):
        pair = [r for r in rows if r["subject"] == subj]
        if len(pair) == 2:
            lo, hi = pair
            print(f"{subj + ' ratio':8s} {'':4s} "
                  + " ".join(f"{hi[c]/lo[c]:9.2f}x" if abs(lo[c]) > 1e-9
                             else f"{'-':>10s}" for c in COLS))


def commission() -> int:
    """Plant a localised offset and require it to be seen THERE and not elsewhere."""
    subject, n, k = "flower", 18, KS[("flower", 18)]
    base = measure(subject, n, k)
    bad = 0

    def ring(shape, amp):
        # Build the ring on the BLOCK grid and expand it, so the planted region
        # and the region the statistic reports are identical by construction.
        # Ringing pixels at 15% and masking blocks at 15% are NOT the same set:
        # blocks straddling the boundary get part of the plant and are then
        # scored as interior, which reads as a leak that is really a
        # misalignment between the plant and the partition.
        bshape = (max(2, shape[0] // BLOCK), max(2, shape[1] // BLOCK))
        return expand(border_mask(bshape).astype(float) * amp, shape)

    for amp in (40.0, -40.0):
        got = measure(subject, n, k, plant=lambda s, a=amp: ring(s, a))
        db, di = got["border"] - base["border"], got["interior"] - base["interior"]
        # The border ring is ~44% of blocks, so the whole-field mean sees well
        # under half of a border-only plant.  That dilution is the entire point.
        dw = got["whole"] - base["whole"]
        tag = "positive" if amp > 0 else "negative"
        if abs(db - amp) > 0.15 * abs(amp):
            print(f"[FAIL] {tag} border plant {amp:+.0f}: border moved {db:+.2f}")
            bad += 1
        else:
            print(f"[PASS] {tag} border plant {amp:+.0f}: border moved {db:+.2f} "
                  f"(want {amp:+.0f})")
        if abs(di) > 0.05 * abs(amp):
            print(f"[FAIL] {tag} border plant leaked into interior: {di:+.2f}")
            bad += 1
        else:
            print(f"[PASS] {tag} border plant did not leak into interior "
                  f"({di:+.2f})")
        if abs(dw) >= abs(amp):
            print(f"[FAIL] whole-field mean saw {dw:+.2f} of a {amp:+.0f} "
                  "border-only plant; it should be diluted")
            bad += 1
        else:
            print(f"[PASS] whole-field mean diluted the {amp:+.0f} border plant "
                  f"to {dw:+.2f} -- this is the failure mode being guarded")

    # A flat-quartile plant must be seen by q0 and must NOT be reported by q3.
    det = detail_field(subject, n,
                       (max(2, conf(subject, n, "default").shape[0] // BLOCK),
                        max(2, conf(subject, n, "default").shape[1] // BLOCK)),
                       k)
    thr = np.nanpercentile(det[np.isfinite(det)], 25)

    def flatplant(shape, amp=60.0):
        sel = (np.isfinite(det) & (det <= thr)).astype(float) * amp
        return expand(sel, shape)

    got = measure(subject, n, k, plant=flatplant)
    d0, d3 = got["q0_flat"] - base["q0_flat"], got["q3_detail"] - base["q3_detail"]
    if abs(d0 - 60.0) > 0.15 * 60.0:
        print(f"[FAIL] flat-quartile plant: q0 moved {d0:+.2f}, want +60")
        bad += 1
    else:
        print(f"[PASS] flat-quartile plant: q0 moved {d0:+.2f} (want +60)")
    if abs(d3) > 3.0:
        print(f"[FAIL] flat-quartile plant leaked into the detail quartile: {d3:+.2f}")
        bad += 1
    else:
        print(f"[PASS] flat-quartile plant did not leak into q3 ({d3:+.2f})")

    print("\n" + ("SPATIAL HEADROOM COMMISSIONED" if bad == 0
                  else f"{bad} CHECK(S) FAILED"))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()
    if a.commission:
        return commission()

    rows = [measure(s, n, KS[(s, n)]) for s, n in RUNGS]
    table(rows, "Confidence headroom (default - hard-max), mean per region, "
                "in confidence units")
    print("\nq0_flat is the flattest quartile of the delivered image -- the "
          "support the\n20-60 px plateau defect was convicted on.  q3_detail is "
          "the most textured.\nA dilution mechanism localised to flat regions "
          "would grow fastest in q0_flat\nand would be understated by 'whole'.")
    (ROOT / "headmap.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

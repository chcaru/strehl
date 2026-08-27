#!/usr/bin/env python3
"""Commission the half-stack decomposition, both ways, for separation, AND for
the leak that the first commissioning run exposed.

A decomposition that always reports "incoherent" is as useless as one that
always reports "registration".  Four requirements:

  1. NULL.  An image against itself must give zero.  A non-zero null means the
     basis fit or the tile matcher is manufacturing signal.
  2. RESPONSE, both directions, on a ladder.  A planted shift and a planted
     incoherent selection must each be detected, monotonically in dose, and
     backing the plant off must bring the statistic back down -- a plant that
     only ever raises the number passes a one-sided test trivially.
  3. SEPARATION.  At a matched total disagreement, a planted registration error
     must land in `reg` and a planted selection error must land in `sel`.
  4. LEAK, AND ITS DOSE.  This one was added because the first run failed it.
     The basis is a FIRST-ORDER Taylor model of a warp, and the band it is
     scored in, 0.30-0.45 cycles per sample, has a period of only 2.2-3.3 px.
     A whole-pixel shift is a third of a period -- far outside the linear
     regime -- and duly split its energy about evenly between `reg` and `sel`
     (1 px: reg 0.867, sel 0.902).  So `sel` is NOT automatically selection:
     a large enough registration error leaks into it.

     The regime that matters is not 1-4 px.  Two halves of one stack are
     registered to a fraction of a pixel, so this run plants EXACT sub-pixel
     shifts by Fourier phase ramp (no interpolation blur, unlike resampling)
     and records how much leaks into `sel` at each dose.  That curve is then
     the calibration: at whatever inter-half shift the real data turns out to
     carry, it gives the largest `sel` that registration alone could produce.
     Anything above that line is not registration.

THE SELECTION PLANT.  A merge that picks a different frame at a pixel renders
that pixel at a different focus.  So the plant replaces a random set of blobs
with a blurred copy of themselves in ONE half only: same scene, same geometry,
locally different focus, at random locations.  That is what an incoherent
choice does to an image, and nothing about it is a warp of the other half.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402
from commission_detail import gauss  # noqa: E402
from detail import pick_sites  # noqa: E402
from halfmetric import decompose, fshift  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
TILE = 256
K = 0.9321
PAD = 8
SHIFT_DOSES = (0.05, 0.1, 0.2, 0.4, 0.8)
BLOB_DOSES = (0.1, 0.3, 0.6)


def scale_plant(t: np.ndarray, e: float, out: int) -> np.ndarray:
    """Resample about the centre by (1+e), bilinearly, cropping to `out`.

    bee's two halves differ in coverage crop k by up to 0.83%, which is a SCALE
    difference, not a translation: within a 256 px tile it is a shift ramp of a
    couple of pixels rather than a constant offset.  The basis has a scale
    column, but the same first-order truncation that leaks translation leaks
    scale too, and the translation ladder cannot measure that leak because the
    fitted translation of a centred scale change is zero.  Interpolation blur
    is unavoidable here, so the e=0 rung runs the identical interpolation path
    and isolates how much of the leak is the resampler rather than the scale.
    """
    n = t.shape[0]
    c = (n - 1) / 2.0
    g = (np.arange(out) - (out - 1) / 2.0) / (1.0 + e) + c
    y0 = np.clip(np.floor(g).astype(int), 0, n - 2)
    fy = g - y0
    r = t[y0][:, :] * (1 - fy)[:, None] + t[y0 + 1][:, :] * fy[:, None]
    r = r[:, y0] * (1 - fy)[None, :] + r[:, y0 + 1] * fy[None, :]
    return r


def sel_plant(t: np.ndarray, frac: float, rng: np.random.Generator,
              sigma: float = 1.5, blob: int = 24) -> np.ndarray:
    """Blur a random `frac` of the tile's area, in blobs, as a wrong frame choice would."""
    n = t.shape[0]
    m = np.zeros((n, n), dtype=bool)
    for _ in range(max(int(frac * (n * n) / (blob * blob)), 0)):
        y, x = rng.integers(0, n - blob, 2)
        m[y:y + blob, x:x + blob] = True
    return np.where(m, gauss(t, sigma), t)


def main() -> int:
    base = tri.luma(tri.load16(str(ROOT / "merge" / "d0.tif")))
    sites = pick_sites(base, K, 12, TILE)
    rng = np.random.default_rng(20260827)
    print(f"commissioning on d0.tif, {len(sites)} sites, {TILE}px tiles\n")

    def run(make_b) -> dict:
        acc: dict[str, list[float]] = {"dis": [], "reg": [], "sel": [], "shift_px": []}
        for i, (y, x) in enumerate(sites):
            r = decompose(base[y:y + TILE, x:x + TILE], make_b(y, x, i), K)
            for key in acc:
                acc[key].append(r[key])
        return {key: float(np.median(v)) for key, v in acc.items()}

    def crop(y, x):
        return base[y - PAD:y + TILE + PAD, x - PAD:x + TILE + PAD]

    print(f"{'arm':>18s} {'total':>9s} {'registr':>9s} {'SELECT':>9s} "
          f"{'sel/reg':>9s} {'fit dx,dy':>10s}")
    print("-" * 72)

    null = run(lambda y, x, i: base[y:y + TILE, x:x + TILE])
    print(f"{'null (A vs A)':>18s} {null['dis']:9.5f} {null['reg']:9.5f} "
          f"{null['sel']:9.5f} {'-':>9s} {null['shift_px']:10.4f}")

    shift_rows, sel_rows = [], []
    for d in SHIFT_DOSES:
        r = run(lambda y, x, i, d=d: fshift(crop(y, x), d, 0.0)[PAD:PAD + TILE,
                                                               PAD:PAD + TILE])
        r["dose"] = d
        shift_rows.append(r)
        print(f"{'shift ' + format(d, '.2f') + 'px':>18s} {r['dis']:9.5f} "
              f"{r['reg']:9.5f} {r['sel']:9.5f} "
              f"{r['sel']/max(r['reg'],1e-9):9.3f} {r['shift_px']:10.4f}")
    for f in BLOB_DOSES:
        r = run(lambda y, x, i, f=f: sel_plant(crop(y, x), f, rng)[PAD:PAD + TILE,
                                                                  PAD:PAD + TILE])
        r["dose"] = f
        sel_rows.append(r)
        print(f"{'blob-blur ' + str(f):>18s} {r['dis']:9.5f} {r['reg']:9.5f} "
              f"{r['sel']:9.5f} {r['sel']/max(r['reg'],1e-9):9.3f} "
              f"{r['shift_px']:10.4f}")

    bad = 0
    print()

    # Scale plant: bee's halves differ in k, and a centred scale change fits a
    # translation of zero, so the translation ladder above cannot calibrate it.
    scale_rows = []
    big = 2 * PAD
    print(f"{'arm':>18s} {'total':>9s} {'registr':>9s} {'SELECT':>9s} {'sel/reg':>9s}")
    print("-" * 60)
    for e in (0.0, 0.002, 0.008):
        r = run(lambda y, x, i, e=e: scale_plant(
            base[y - big:y + TILE + big, x - big:x + TILE + big], e, TILE))
        r["dose"] = e
        scale_rows.append(r)
        lbl = "interp only (e=0)" if e == 0.0 else f"scale {100*e:.1f}%"
        print(f"{lbl:>18s} {r['dis']:9.5f} {r['reg']:9.5f} {r['sel']:9.5f} "
              f"{r['sel']/max(r['reg'],1e-9):9.3f}")
    print()

    ok = null["dis"] < 1e-6 and null["sel"] < 1e-6
    bad += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] null reads {null['dis']:.2e} total, "
          f"{null['sel']:.2e} select (want ~0)")

    for rows, name, key in ((shift_rows, "shift", "reg"), (sel_rows, "blob-blur", "sel")):
        v = [r[key] for r in rows]
        mono = all(v[i] < v[i + 1] for i in range(len(v) - 1)) and v[0] > null[key]
        bad += not mono
        print(f"[{'PASS' if mono else 'FAIL'}] {name} ladder is monotone in "
              f"'{key}' ({v[0]:.4f} -> {v[-1]:.4f}) and above the null")

    # The fit must RECOVER the planted translation, not merely react to it.
    err = max(abs(r["shift_px"] - r["dose"]) / r["dose"] for r in shift_rows)
    ok = err < 0.15
    bad += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] fitted translation recovers the planted "
          f"dose to {100*err:.1f}% worst case (want < 15%)")

    sh, se = shift_rows[2], sel_rows[1]          # 0.2 px vs 30% blobs
    sep = (se["sel"] / max(se["reg"], 1e-9)) / (sh["sel"] / max(sh["reg"], 1e-9))
    ok = sep > 3.0
    bad += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] SEPARATION: the selection plant's sel/reg is "
          f"{sep:.1f}x the shift plant's (want > 3x)")
    print(f"         shift 0.20px -> total {sh['dis']:.4f}, sel/reg {sh['sel']/sh['reg']:.3f}")
    print(f"         blob 0.3     -> total {se['dis']:.4f}, sel/reg {se['sel']/se['reg']:.3f}")

    print("\nLEAK CALIBRATION -- the largest `sel` a pure registration error of each\n"
          "size can produce.  A measured `sel` above the line for the pair's own\n"
          "fitted shift cannot be registration.")
    for r in shift_rows:
        print(f"    shift {r['dose']:.2f} px  ->  sel {r['sel']:.4f}  "
              f"(leak {100*r['sel']/max(r['dis'],1e-9):.0f}% of its own total, "
              f"sel/reg {r['sel']/max(r['reg'],1e-9):.2f})")
    sc = scale_rows[-1]
    print(f"    scale {100*sc['dose']:.1f}%  ->  sel {sc['sel']:.4f}  "
          f"(sel/reg {sc['sel']/max(sc['reg'],1e-9):.2f}); the interpolation-only\n"
          f"    rung contributes sel {scale_rows[0]['sel']:.4f} of that.")
    worst = max([r["sel"] / max(r["reg"], 1e-9) for r in shift_rows]
                + [sc["sel"] / max(sc["reg"], 1e-9)])
    print(f"\n    Worst leak ratio over BOTH plant families: {worst:.2f} sel per unit\n"
          f"    reg.  halfmetric.py subtracts leak_ratio * reg, so a `sel_net`\n"
          f"    that survives is not a registration difference between the halves.")

    (ROOT / "half-leak.json").write_text(json.dumps(
        {"shift": shift_rows, "blob": sel_rows, "scale": scale_rows,
         "null": null, "worst_leak_ratio": worst}, indent=1), encoding="utf-8")
    print(f"\n{'HALF-STACK DECOMPOSITION COMMISSIONED' if bad == 0 else f'{bad} CHECK(S) FAILED'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Radially resolved detail, against a graded registration dose.

WHY THIS IS NOT M86's TENENGRAD. M86 measured whole-frame Tenengrad at 0.9859x
and M85 at 0.985x, and the orchestrator has ruled whole-frame gradient energy
measured-dead for this purpose. The change here is not a cleverer functional --
it is the SAMPLING. A scale error is exactly zero at the optical centre and
grows linearly with radius, so a whole-frame mean averages a real edge effect
against a guaranteed centre null. Resolving by radius is the difference between
an instrument and a foregone conclusion.

WHY IT IS ALLOWED TO BE A SIMPLE METRIC. Because it is not asked to be
trustworthy on its own. It is scored against a GRADED DOSE of the treatment:

    UNALIGNED  0% of drift removed      (422.3 plane px residual)
    ALIGNED   33.3%                     (281.8 px, as shipped)
    GAINED    89.5%                     ( 44.2 px, gain-corrected)
    JITTER    89.5% + 8.855 px planted noise

all MEASURED by signtest.py. A metric that moves monotonically along a dose it
was not told about is measuring the dose. A metric that does not, is not -- and
that is a reportable result rather than a failure.

ZOOMNULL is the denominator throughout: same resampler, same field of view,
relative registration discarded. It is the only comparison that isolates
registration.
"""

import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_erosion


def load(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float64) if a.ndim == 3 else a.astype(np.float64)


def valid_mask(arms: dict[str, np.ndarray], erode: int) -> np.ndarray:
    """Pixels usable in EVERY arm. M86's first render read a fake 1.4565x
    because its metric was measuring a black fill boundary over 9.544% of the
    frame; every number here is computed inside this mask."""
    m = np.ones(next(iter(arms.values())).shape, dtype=bool)
    for a in arms.values():
        m &= a > 0
    return binary_erosion(m, np.ones((2 * erode + 1, 2 * erode + 1), bool))


def energy(a: np.ndarray) -> np.ndarray:
    gy = np.zeros_like(a)
    gx = np.zeros_like(a)
    gy[:-1, :] = np.diff(a, axis=0)
    gx[:, :-1] = np.diff(a, axis=1)
    return gy * gy + gx * gx


def bands(shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    return r / r.max()


def main(argv: list[str]) -> int:
    out_json, base_dir = argv[1], argv[2]
    names = ["UNALIGNED", "ZOOMNULL", "ALIGNED", "GAINED", "JITTER"]
    dose = {"UNALIGNED": 0.0, "ZOOMNULL": 0.0, "ALIGNED": 33.3, "GAINED": 89.5,
            "JITTER": 89.5}

    arms = {}
    for n in names:
        try:
            arms[n] = load(rf"{base_dir}\marker-{n}.tif")
        except FileNotFoundError:
            print(f"  (missing {n}, skipping)")
    print(f"shape {next(iter(arms.values())).shape}   arms: {', '.join(arms)}")

    mask = valid_mask(arms, erode=24)
    print(f"coverage mask keeps {100.0 * mask.mean():.3f}% of the frame "
          f"(erode 24 px, and >0 in every arm)")

    # Q4 boundary immunity, proven by a plant rather than asserted. Blacken a
    # ring just inside the frame edge; if the mask works, the number must not
    # move. If it does move, the mask is not doing its job and no number below
    # can be trusted.
    probe = arms["ZOOMNULL"].copy()
    ring = np.zeros(probe.shape, bool)
    ring[:16, :] = ring[-16:, :] = ring[:, :16] = ring[:, -16:] = True
    probe[ring] = 0.0
    e_clean = energy(arms["ZOOMNULL"])[mask].mean()
    e_plant = energy(probe)[mask].mean()
    dev = abs(e_plant - e_clean) / e_clean
    print(f"Q4 boundary plant: {ring.sum()} px blackened at the rim -> "
          f"metric moves {100 * dev:.4f}%  "
          f"{'PASS (masked out)' if dev < 1e-3 else 'FAIL (leaking into the metric)'}")

    r = bands(next(iter(arms.values())).shape)
    edges = [0.0, 0.25, 0.50, 0.75, 1.01]
    den = "ZOOMNULL"
    e = {n: energy(a) for n, a in arms.items()}

    rows = []
    hdr = "  ".join(f"{n:>9}" for n in names if n in arms)
    print(f"\n{'band':>12}  {'tiles':>8}  {hdr}     (ratio to {den})")
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = mask & (r >= lo) & (r < hi)
        if m.sum() < 1000:
            continue
        d = e[den][m].mean()
        vals = {n: float(e[n][m].mean() / d) for n in arms}
        rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), ratios=vals))
        cells = "  ".join(f"{vals[n]:>9.4f}" for n in names if n in arms)
        print(f"  {lo:.2f}-{hi:.2f}  {m.sum():>8}  {cells}")

    print()
    if "GAINED" in arms and "JITTER" in arms:
        inner, outer = rows[0]["ratios"], rows[-1]["ratios"]
        print(f"centre band GAINED/ZOOMNULL = {inner['GAINED']:.4f}")
        print(f"outer  band GAINED/ZOOMNULL = {outer['GAINED']:.4f}")
        print(f"radial gradient (outer-centre) = {outer['GAINED']-inner['GAINED']:+.4f}")
        print()
        # Q1: the plant must move the metric by >=5x the ALIGNED-vs-ZOOMNULL gap.
        signal = abs(outer.get("ALIGNED", 1.0) - 1.0)
        plant = abs(outer["JITTER"] - outer["GAINED"])
        ratio = plant / signal if signal > 0 else float("inf")
        print(f"Q1 responsiveness (outer band): planted jitter moves "
              f"{plant:.4f}, ALIGNED-vs-null signal is {signal:.4f} -> {ratio:.1f}x  "
              f"{'PASS' if ratio >= 5 else 'FAIL: metric cannot see a planted defect'}")
        # Q3: monotone in dose?
        seq = [(dose[n], outer[n]) for n in ("UNALIGNED", "ALIGNED", "GAINED") if n in outer]
        mono = all(b >= a for (_, a), (_, b) in zip(seq, seq[1:])) or \
               all(b <= a for (_, a), (_, b) in zip(seq, seq[1:]))
        print(f"Q3 dose-response (outer band): "
              f"{' -> '.join(f'{d:.0f}%:{v:.4f}' for d, v in seq)}  "
              f"{'MONOTONE' if mono else 'NOT MONOTONE'}")

    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(dict(mask_frac=float(mask.mean()), q4_dev=float(dev), bands=rows),
                  fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

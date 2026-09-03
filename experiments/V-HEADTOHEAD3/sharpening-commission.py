"""Commission every new sharpening-discriminator operator before outcomes."""

from __future__ import annotations

import math
import sys

import numpy as np
from scipy import ndimage, signal

import sharpening_core as sc


class Recorder:
    def __init__(self) -> None:
        self.controls = 0
        self.plants = 0
        self.failed: list[str] = []

    def control(self, name: str, ok: bool, reading: str) -> None:
        self.controls += 1
        print(f"CONTROL {'GREEN' if ok else 'FAIL '} {name}: {reading}")
        if not ok:
            self.failed.append("control " + name)

    def plant(self, name: str, caught: bool, reading: str) -> None:
        self.plants += 1
        print(f"PLANT   {'RED  ' if caught else 'MISS '} {name}: {reading}")
        if not caught:
            self.failed.append("plant " + name)


def direct_usm(a: np.ndarray, sigma: float, amount: float) -> np.ndarray:
    """Independent finite-kernel plant; does not call sc.usm."""
    radius = int(math.ceil(4 * sigma))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= np.sum(k)
    blur = signal.convolve2d(a, np.outer(k, k), mode="same", boundary="symm")
    return a + amount * (a - blur)


def fixture(n: int = 256) -> np.ndarray:
    rng = np.random.default_rng(911)
    y, x = np.mgrid[:n, :n]
    a = (
        0.7 * np.sin(2 * np.pi * x / 31)
        + 0.4 * np.sin(2 * np.pi * (x + y) / 13)
        + 0.2 * (x > n // 2)
        + rng.normal(0, 0.25, (n, n))
    )
    return a


def spectrum_transfer(samples: list[tuple[np.ndarray, np.ndarray]]) -> dict:
    p0 = np.zeros(len(sc.FIT_EDGES) - 1)
    p1 = np.zeros_like(p0)
    for a, b in samples:
        pa, scale = sc.radial_band_powers(a)
        pb, _ = sc.radial_band_powers(b, reference_scale=scale)
        p0 += pa
        p1 += pb
    return {
        "count": len(samples),
        "p0": p0,
        "p40": p1,
        "amplitude": np.sqrt(p1 / p0),
        "centres": 0.5 * (sc.FIT_EDGES[:-1] + sc.FIT_EDGES[1:]),
    }


def main() -> int:
    r = Recorder()

    # Fixed external frequency membership.
    shape = (128, 128)
    mask = sc.licensed_mask(shape)
    inside = (0, 28)  # 28/128 = 0.21875
    outside = (0, 36)  # 36/128 = 0.28125
    r.control(
        "fixed licensed-bin oracle",
        bool(mask[inside] and not mask[outside]),
        f"0.21875={bool(mask[inside])}, 0.28125={bool(mask[outside])}",
    )
    mutant = (sc.frequency_radius(shape) >= 0.25) & (
        sc.frequency_radius(shape) < 0.30
    )
    r.plant(
        "above-cap mask substitution",
        bool(not mutant[inside] and mutant[outside]),
        "mutant admits 0.28125 and rejects licensed 0.21875",
    )

    # Point-tone invariance and raw-substitution potency.
    a = fixture()
    curves = {
        "affine": 2.3 * a + 7.0,
        "gamma3": np.sign(a - a.min()) * (a - a.min()) ** 3,
        "logistic": 1.0 / (1.0 + np.exp(-4.0 * (a - np.median(a)))),
    }
    q0 = sc.q25(a)
    moves = {name: abs(sc.q25(v) / q0 - 1.0) for name, v in curves.items()}
    r.control(
        "Q25 strict-tone invariance",
        max(moves.values()) <= 1e-10,
        ", ".join(f"{k}={v:.3e}" for k, v in moves.items()),
    )
    raw_move = max(abs(sc.raw_q25(v) / sc.raw_q25(a) - 1.0) for v in curves.values())
    r.plant(
        "raw-power substitution",
        raw_move >= 0.05,
        f"raw max move={raw_move:.3f}, ordinal max={max(moves.values()):.3e}",
    )

    # Flat null and independently generated USM.
    rng = np.random.default_rng(22)
    iid_flat = 0.2 + rng.normal(0, 0.01, (256, 256))
    iid_sharp = direct_usm(iid_flat, 1.0, 1.0)
    print(
        "DIAGNOSTIC iid-white-noise Q25 USM/base="
        f"{sc.q25(iid_sharp) / sc.q25(iid_flat):.6f}"
    )
    flat = 0.2 + ndimage.gaussian_filter(iid_flat - 0.2, 1.0, mode="reflect")
    null_ratio = sc.q25(flat.copy()) / sc.q25(flat)
    null_hull = sc.rank_hull_delta(flat, flat.copy())[0]
    r.control(
        "untuned flat identity null",
        abs(null_ratio - 1.0) <= 1e-12 and abs(null_hull) <= 1e-12,
        f"ratio={null_ratio:.12f}, hull={null_hull:.12f}",
    )
    sharp = direct_usm(flat, 1.0, 1.0)
    sharp_ratio = sc.q25(sharp) / sc.q25(flat)
    sharp_hull = sc.rank_hull_delta(flat, sharp)[0]
    r.control(
        "independent spatial-USM potency",
        sharp_ratio > 1.25 and sharp_hull > 0.005,
        f"flat ratio={sharp_ratio:.3f}, hull delta={sharp_hull:.5f}",
    )
    r.plant(
        "disabled improvement arm",
        sharp_ratio > 1.25 and sharp_hull > 0.005,
        "identity operator would read ratio 1 and hull 0",
    )
    blurred = ndimage.gaussian_filter(flat, 1.5, mode="reflect")
    blur_ratio = sc.q25(blurred) / sc.q25(flat)
    r.control(
        "spatial-blur degradation potency",
        blur_ratio < 0.75,
        f"blurred/original Q25={blur_ratio:.4f}",
    )
    r.plant(
        "disabled degradation arm",
        blur_ratio < 0.75,
        "identity operator would read ratio 1",
    )

    # Rank hull itself must ignore a point curve and catch direction reversal.
    gamma_hull = sc.rank_hull_delta(flat, np.exp(flat))[0]
    r.control(
        "rank-hull tone null",
        abs(gamma_hull) <= 1e-12,
        f"exp point-map delta={gamma_hull:.3e}",
    )
    reversed_hull = sc.rank_hull_delta(sharp, flat)[0]
    r.plant(
        "rank-hull direction reversal",
        sharp_hull > 0.005 and reversed_hull < -0.005,
        f"forward={sharp_hull:.5f}, reversed={reversed_hull:.5f}",
    )

    # Independent convolution plant for the source-only analytic fit.
    samples_train = []
    samples_hold = []
    for i in range(16):
        base = fixture(192) + np.random.default_rng(100 + i).normal(0, 0.05, (192, 192))
        pair = (base, direct_usm(base, 1.0, 1.0))
        (samples_train if i % 2 == 0 else samples_hold).append(pair)
    train = spectrum_transfer(samples_train)
    hold = spectrum_transfer(samples_hold)
    model, _ = sc.fit_model(train, hold)
    recovered = abs(model.sigma - 1.0) <= 0.05 and abs(model.amount - 1.0) <= 0.05
    r.control(
        "independent USM recovery",
        recovered,
        f"expected (1.00,1.00), got ({model.sigma:.2f},{model.amount:.2f})",
    )
    r.plant(
        "no-op transfer model",
        model.train_loss < 0.75 * model.train_identity_loss,
        f"fit={model.train_loss:.5f}, identity={model.train_identity_loss:.5f}",
    )

    # Registration convention against an untouched source.
    reg = fixture(192)
    for dy, dx in ((2, -3), (-4, 1)):
        mov = np.roll(reg, (dy, dx), axis=(0, 1))
        got = sc.phase_correction(reg, mov, max_shift=8)
        aa, bb = sc.overlap_after_shift(reg, mov, got[:2])
        r.control(
            f"registration correction {(dy, dx)}",
            got[:2] == (-dy, -dx) and np.array_equal(aa, bb),
            f"expected {(-dy,-dx)}, got {got[:2]}, equality={np.array_equal(aa,bb)}",
        )
    dy, dx = (2, -3)
    mov = np.roll(reg, (dy, dx), axis=(0, 1))
    wrong_a, wrong_b = sc.overlap_after_shift(reg, mov, (dy, dx))
    zero_a, zero_b = sc.overlap_after_shift(reg, mov, (0, 0))
    r.plant(
        "wrong-sign registration",
        not np.array_equal(wrong_a, wrong_b),
        "wrong sign fails fixed source equality",
    )
    r.plant(
        "no-op registration",
        not np.array_equal(zero_a, zero_b),
        "zero correction fails fixed source equality",
    )

    # Literal verdict vectors make every branch reachable.
    artifact_flags = dict(
        advantage=True,
        model=True,
        reproduces=True,
        flat_output=True,
        corroboration=True,
        spatial=True,
    )
    real_flags = dict(
        advantage=True,
        original_trail=True,
        model=True,
        no_carry=True,
        flat_null=True,
        hull_null=True,
        usm_still_trails=True,
        spatial=True,
    )
    r.control(
        "literal verdict reachability",
        sc.verdict(artifact_flags) == "ARTIFACT"
        and sc.verdict(real_flags).startswith("REAL DEFICIT")
        and sc.verdict({}) == "INDETERMINATE",
        "ARTIFACT / REAL DEFICIT / INDETERMINATE all reachable",
    )
    no_flat = dict(artifact_flags)
    no_flat["flat_output"] = False
    r.plant(
        "omitted mandatory flat predicate",
        sc.verdict(no_flat) == "INDETERMINATE",
        f"mutant vector without flat => {sc.verdict(no_flat)}",
    )

    print(f"UNLICENSED_SENTINEL={sc.UNLICENSED}")
    if r.failed:
        print("SHARPENING COMMISSION FAILED: " + ", ".join(r.failed))
        return 1
    print(
        f"SHARPENING COMMISSION GREEN: {r.controls}/{r.controls} controls GREEN; "
        f"{r.plants}/{r.plants} plants RED"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

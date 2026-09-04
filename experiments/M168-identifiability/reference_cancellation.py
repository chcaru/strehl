# Numerical witness that comparative q cancels a common reference path.

from __future__ import annotations

import math


SCENE_POWER = 3.0
H_CANDIDATE = 0.8
H_COMPARATOR = 0.4
NOISE_POWER_CANDIDATE = 0.09
NOISE_POWER_COMPARATOR = 0.09
REFERENCE_TRANSFERS = (0.4, 0.9)


def q_for_reference(h_reference: float) -> dict[str, float]:
    reference_power = h_reference**2 * SCENE_POWER
    cross_candidate = H_CANDIDATE * h_reference * SCENE_POWER
    cross_comparator = H_COMPARATOR * h_reference * SCENE_POWER
    transfer_candidate = abs(cross_candidate) / reference_power
    transfer_comparator = abs(cross_comparator) / reference_power
    ein_candidate = math.sqrt(NOISE_POWER_CANDIDATE) / transfer_candidate
    ein_comparator = math.sqrt(NOISE_POWER_COMPARATOR) / transfer_comparator
    return {
        "h_reference": h_reference,
        "reference_power": reference_power,
        "transfer_candidate": transfer_candidate,
        "transfer_comparator": transfer_comparator,
        "ein_candidate": ein_candidate,
        "ein_comparator": ein_comparator,
        "q": ein_candidate / ein_comparator,
    }


def main() -> None:
    rows = [q_for_reference(value) for value in REFERENCE_TRANSFERS]
    expected = (
        math.sqrt(NOISE_POWER_CANDIDATE / NOISE_POWER_COMPARATOR)
        * abs(H_COMPARATOR / H_CANDIDATE)
    )

    assert not math.isclose(
        rows[0]["reference_power"], rows[1]["reference_power"]
    )
    for row in rows:
        assert math.isclose(row["q"], expected, rel_tol=0.0, abs_tol=1e-15)

    for row in rows:
        print(
            f"H_R={row["h_reference"]:.1f} "
            f"P_R={row["reference_power"]:.6f} "
            f"T_C={row["transfer_candidate"]:.6f} "
            f"T_B={row["transfer_comparator"]:.6f} "
            f"q={row["q"]:.6f}"
        )
    print(
        "CANCELLED_FORM="
        "sqrt(P_NC/P_NB)*abs(H_B/H_C); no P_S, P_R, or H_R"
    )
    print("PASS: q=0.500000 for both reference transfers")


if __name__ == "__main__":
    main()

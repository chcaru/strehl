# Finite witness for output-only non-identifiability.

from __future__ import annotations

import numpy as np


def main() -> None:
    a_integer = np.array([0, 0, 1, 0, 0], dtype=np.int64)
    a = a_integer.astype(np.float64)
    g = np.array(
        [
            [0.75, 0.25, 0.00, 0.00, 0.00],
            [0.25, 0.50, 0.25, 0.00, 0.00],
            [0.00, 0.25, 0.50, 0.25, 0.00],
            [0.00, 0.00, 0.25, 0.50, 0.25],
            [0.00, 0.00, 0.00, 0.25, 0.75],
        ],
        dtype=np.float64,
    )

    rows, columns = np.indices(g.shape)
    assert np.all(g >= 0.0)
    assert np.allclose(g.sum(axis=1), 1.0, rtol=0.0, atol=0.0)
    assert np.count_nonzero(g[np.abs(rows - columns) > 1]) == 0

    b = g @ a

    # World D: A is faithful and B is signal-degrading blur.
    observed_degradation = np.stack((a, g @ a))
    degradation_label = "prefer A over B"

    # World I: B is faithful and A-B is removable additive artifact.
    artifact = a - b
    observed_improvement = np.stack((b + artifact, b))
    improvement_label = "prefer B over A"

    value_identical = np.array_equal(
        observed_degradation, observed_improvement
    )
    byte_identical = (
        observed_degradation.tobytes() == observed_improvement.tobytes()
    )
    opposite_labels = degradation_label != improvement_label

    assert np.array_equal(b, np.array([0.0, 0.25, 0.5, 0.25, 0.0]))
    assert value_identical
    assert byte_identical
    assert opposite_labels

    print(f"A={a_integer.tolist()}")
    print("G=")
    print(np.array2string(g, precision=2, floatmode="fixed"))
    print(f"B=G@A={b.tolist()}")
    print(f"A-B={artifact.tolist()}")
    print(f"degradation_world_label={degradation_label}")
    print(f"improvement_world_label={improvement_label}")
    print(f"observation_values_identical={value_identical}")
    print(f"observation_bytes_identical={byte_identical}")
    print(f"labels_opposite={opposite_labels}")
    print("PASS: identical observations require opposite rankings")


if __name__ == "__main__":
    main()

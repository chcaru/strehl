"""Apply the frozen current-path identity and bee physics-comparability rules."""

from __future__ import annotations

import json
import sys

import numpy as np

import m82lib as M

M70_ROOT = M.REPO / "experiments" / "M70-through-focus-spectrum"
M70_SRC = M70_ROOT / "src"
sys.path.insert(0, str(M70_SRC))
import m70lib as K  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s10_architecture as S10  # noqa: E402

WINDOWS = (1, 2, 3, 5, 10, 20)
PHYSICS_WINDOWS = WINDOWS[:-1]
IDENTITY_RELATIVE_BAR = 0.001
PHYSICS_SPAN_BAR = 1.05
MIN_TEXTURED = 16


def load_current(stack: str) -> dict:
    path = M.HERE / f"bee-physics-{stack}.npz"
    with np.load(path, allow_pickle=False) as data:
        result = {
            "power": data["power"],
            "level": data["level"],
            "bands": [str(value) for value in data["bands"]],
            "iso": float(data["iso"]),
            "patch": int(data["patch"]),
            "tile": int(data["tile"]),
            "centres": data["centres"],
            "frames": [str(value) for value in data["frames"]],
        }
    expected = [path.name for path in M.stack_files(stack)]
    if result["frames"] != expected:
        raise RuntimeError(f"{stack}: NPZ filenames differ from current directory")
    return result


def one_stack(stack: str, prior: dict) -> dict:
    data = load_current(stack)
    signal, nvar = A5.signal(data)
    textured, _ = A5.classify(data, signal, nvar)
    indices = [index for index, keep in enumerate(textured) if keep]
    response = {}
    prior_response = {}
    relative_error = {}
    for window in WINDOWS:
        bands = []
        for band in K.MID_BANDS:
            j = data["bands"].index(band)
            rows = [S10.gains(signal[:, p, j], window) for p in indices]
            bands.append(A5.med([row[1] for row in rows]))
        value = float(np.mean(bands))
        expected = float(prior[f"avg_vs_avg3_{window}"])
        response[str(window)] = value
        prior_response[str(window)] = expected
        relative_error[str(window)] = abs(value / expected - 1.0)
    return {
        "stack": stack,
        "directory": M.STACKS[stack]["directory"],
        "frames": len(data["frames"]),
        "first": data["frames"][0],
        "last": data["frames"][-1],
        "iso": data["iso"],
        "textured_patches": len(indices),
        "response": response,
        "prior_response": prior_response,
        "identity_relative_error": relative_error,
        "identity_pass": max(relative_error.values()) <= IDENTITY_RELATIVE_BAR,
        "npz_sha256": M.sha256(M.HERE / f"bee-physics-{stack}.npz"),
    }


def self_tests() -> None:
    profile = np.zeros(41, dtype=np.float64)
    profile[20] = 4.0
    profile[19] = profile[21] = 1.0
    for window in WINDOWS:
        matched, average, total = S10.gains(profile, window)
        assert np.isfinite((matched, average, total)).all()
        assert matched >= 1.0
        assert abs(total - matched * average) < 1e-12
    print("M82_BEE_PHYSICS_TESTS=18/18 PASS")


def main() -> None:
    self_tests()
    if "--self-test-only" in sys.argv:
        return
    prior_rows = json.loads(
        (M70_ROOT / "out" / "s10_architecture.json").read_text(encoding="utf-8")
    )
    prior = {row["stack"]: row for row in prior_rows}
    stacks = {stack: one_stack(stack, prior[stack]) for stack in M.BEE_SIBLINGS}
    spans = {}
    for window in WINDOWS:
        values = [stacks[stack]["response"][str(window)] for stack in M.BEE_SIBLINGS]
        spans[str(window)] = max(values) / min(values)
    peaks = {
        stack: max(
            PHYSICS_WINDOWS,
            key=lambda window: stacks[stack]["response"][str(window)],
        )
        for stack in M.BEE_SIBLINGS
    }
    identity_pass = all(row["identity_pass"] for row in stacks.values())
    texture_pass = all(
        row["textured_patches"] >= MIN_TEXTURED for row in stacks.values()
    )
    peak_pass = len(set(peaks.values())) == 1
    span_pass = all(spans[str(window)] <= PHYSICS_SPAN_BAR for window in PHYSICS_WINDOWS)
    physics_pass = identity_pass and texture_pass and peak_pass and span_pass
    output = {
        "source": {
            "m70_commit": "d882b0c",
            "m70_s04_sha256": M.sha256(M70_SRC / "s04_through_focus.py"),
            "m70_s05_sha256": M.sha256(M70_SRC / "s05_analyse.py"),
            "m70_s10_sha256": M.sha256(M70_SRC / "s10_architecture.py"),
            "m70lib_sha256": M.sha256(M70_SRC / "m70lib.py"),
        },
        "registered": {
            "windows": list(WINDOWS),
            "physics_windows": list(PHYSICS_WINDOWS),
            "identity_relative_bar": IDENTITY_RELATIVE_BAR,
            "physics_span_bar": PHYSICS_SPAN_BAR,
            "minimum_textured_patches": MIN_TEXTURED,
        },
        "stacks": stacks,
        "spans": spans,
        "peak_windows": peaks,
        "controls": {
            "identity_pass": identity_pass,
            "texture_pass": texture_pass,
            "same_peak_pass": peak_pass,
            "span_pass": span_pass,
        },
        "p34_equivalent": physics_pass,
        "disposition": "COMPARABLE" if physics_pass else "PREMISE_NOT_ESTABLISHED",
    }
    path = M.HERE / "bee-physics.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for stack, row in stacks.items():
        values = " ".join(
            f"W{window}={row['response'][str(window)]:.6f}" for window in WINDOWS
        )
        print(
            f"{stack}: textured={row['textured_patches']} "
            f"identity={row['identity_pass']} {values}"
        )
    print(f"spans={spans}")
    print(f"peaks={peaks}")
    print(
        f"P34_EQUIVALENT={physics_pass} "
        f"disposition={output['disposition']}"
    )


if __name__ == "__main__":
    main()

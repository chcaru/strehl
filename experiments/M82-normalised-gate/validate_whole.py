"""Fresh whole-plane Python-versus-Rust admission validation on 109MSDCF."""

from __future__ import annotations

import json
import math
import time

import numpy as np

import m82lib as M


def main() -> None:
    stack = "109MSDCF"
    iso = float(M.STACKS[stack]["iso"])
    files = M.stack_files(stack)
    best = None
    winner = None
    black = None
    plane = None
    t0 = time.time()
    for index, path in enumerate(files):
        raw, luma, field, pins, frame_black, frame_plane = M.frame_arrays(
            path, iso, None
        )
        del raw, luma, pins
        if best is None:
            best = np.full(field.shape, -np.inf, dtype=np.float32)
            winner = np.zeros(field.shape, dtype=np.uint16)
            black = frame_black
            plane = frame_plane
        better = field > best
        best[better] = field[better]
        winner[better] = index
        print(f"pass1 {index + 1}/{len(files)} ({time.time() - t0:.1f}s)", flush=True)
    tolerance = np.float32(
        2.0 * math.sqrt(2.0) * float(M.constants()["focus_noise_sd"])
    )
    count = np.zeros(best.shape, dtype=np.uint16)
    for index, path in enumerate(files):
        raw, luma, field, pins, frame_black, frame_plane = M.frame_arrays(
            path, iso, None
        )
        del raw, luma, pins
        if frame_black != black or frame_plane != plane:
            raise RuntimeError("levels or geometry changed")
        admitted = M.admission_mask(best - field, tolerance)
        admitted |= winner == index
        count += admitted
        print(f"pass2 {index + 1}/{len(files)} ({time.time() - t0:.1f}s)", flush=True)
    measured = float(count.mean())
    ladder = json.loads((M.HERE / "ladder-results.json").read_text(encoding="utf-8"))
    rust = next(
        row["mean_n_eff"]
        for row in ladder["stacks"][stack]["rows"]
        if row["gate"] == 2.0
    )
    relative = abs(measured / rust - 1.0)
    result = {
        "stack": stack,
        "gate": 2.0,
        "python_mean_n_eff": measured,
        "rust_mean_n_eff": rust,
        "relative_error": relative,
        "bar": 0.01,
        "pass": relative <= 0.01,
        "frames": len(files),
        "black": black,
        "plane": plane,
        "elapsed_seconds": time.time() - t0,
    }
    (M.HERE / "validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    if not result["pass"]:
        raise SystemExit("whole-plane merge validation failed")


if __name__ == "__main__":
    main()

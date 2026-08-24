"""Parse fresh bee ladders and solve M82's unchanged sigma requests."""

from __future__ import annotations

import json
import sys

import analyse_ladders as A
import m82lib as M


def cli_metadata(path, stack: str) -> dict:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    iso_line = next(line for line in lines if line.startswith("iso "))
    frames_line = next(line for line in lines if line.startswith("frames "))
    iso = float(iso_line.split(":", 1)[1].strip())
    expected_iso = float(M.STACKS[stack]["iso"])
    directory = str(M.STACKS[stack]["directory"])
    expected_path = str(M.CORPUS / directory)
    if iso != expected_iso:
        raise RuntimeError(f"{stack}: CLI ISO {iso} differs from {expected_iso}")
    if not frames_line.endswith(f"from {expected_path}"):
        raise RuntimeError(
            f"{stack}: CLI frames path does not end with current directory"
        )
    return {"cli_iso": iso, "cli_frames_path": expected_path}


def main() -> None:
    M.self_tests()
    if "--self-test-only" in sys.argv:
        return
    binary = json.loads((M.HERE / "binary.json").read_text(encoding="utf-8"))
    output = {
        "requests": list(M.REQUESTS),
        "primary_request": M.PRIMARY_REQUEST,
        "binary": binary,
        "stacks": {},
    }
    for stack in M.BEE_SIBLINGS:
        path = M.HERE / f"bee-ladder-{stack}.log"
        rows = A.parse_ladder(path, stack, binary)
        solves = {
            f"{request:.2f}": M.solve_gate(rows, request)
            for request in M.REQUESTS
        }
        output["stacks"][stack] = {
            "directory": M.STACKS[stack]["directory"],
            "n": M.STACKS[stack]["n"],
            "iso": M.STACKS[stack]["iso"],
            **cli_metadata(path, stack),
            "log_sha256": M.sha256(path),
            "rows": rows,
            "solves": solves,
            "sigma_monotone": True,
        }
        print(
            f"{stack:8} "
            + " ".join(
                f"S{request:.2f}=T{solves[f'{request:.2f}']['gate']:.7f}"
                for request in M.REQUESTS
            )
        )
    (M.HERE / "bee-ladder-results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

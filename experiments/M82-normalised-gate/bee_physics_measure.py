"""Re-run M70's through-focus measurement on one renamed bee directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

import m82lib as M

M70_SRC = M.REPO / "experiments" / "M70-through-focus-spectrum" / "src"
sys.path.insert(0, str(M70_SRC))
import s04_through_focus as S4  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", choices=M.BEE_SIBLINGS, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    stack = args.stack
    cfg = M.STACKS[stack]
    directory = str(cfg["directory"])
    files = M.stack_files(stack)
    print(
        f"logical_stack={stack} directory={directory} frames={len(files)} "
        f"first={files[0].name} last={files[-1].name}",
        flush=True,
    )
    S4.ROOT = str(M.CORPUS)
    S4.OUT = str(M.HERE)
    generated = M.HERE / S4.run_stack(
        directory,
        float(cfg["iso"]),
        tag="-m82",
        nproc=args.workers,
    )
    target = M.HERE / f"bee-physics-{stack}.npz"
    generated.replace(target)
    with np.load(target, allow_pickle=False) as data:
        if data["power"].shape != (int(cfg["n"]), 24, 6):
            raise RuntimeError(f"{stack}: unexpected power shape {data['power'].shape}")
        recorded = [str(name) for name in data["frames"]]
    current = [path.name for path in files]
    if recorded != current:
        raise RuntimeError(f"{stack}: measurement filenames differ from current folder")
    print(f"output={target.name} sha256={M.sha256(target)}", flush=True)


if __name__ == "__main__":
    main()

"""Subtract two gallery runs and say which subjects moved, and which way.

The gallery answers "is this good". This answers "is this getting better",
which is a different question and the one nobody could answer before dated
runs existed.

It exists because of what happened the first time two runs were subtracted:
seventeen of twenty-six subjects had lost sharpness in about two hours, and
nothing in the commit log announced it. Every change in that window was
reasonable and several were reported as improvements on the subject they were
aimed at. The aggregate effect on the library was negative, and it was
invisible to every instrument the project had, because a 6% softening cannot
be seen on a single image -- only against something to compare it with.

Sharpness here is gradient RMS at viewing scale. That is a blunt instrument and
it is meant to be: it is a TRIPWIRE, not a verdict. It says "go and look at
these two pictures", and the pictures decide. It cannot tell a genuine
resolution gain from ringing, and it will read a halo suppression as a loss.
Treat a flagged subject as a question, never as a result.

Usage:
    python scripts/trend.py <new_dir> <old_dir>
    python scripts/trend.py            # latest two under gallery-history

8-bit JPEG through PIL is fine. The rule that bans PIL is about 16-bit RGB
TIFFs, which it silently downconverts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HISTORY = Path(r"C:\dev\strehl-out\gallery-history")

# Below this a subject is unchanged for practical purposes. Above it, someone
# should open the two images side by side.
FLAG = 0.01


def run_time(d: Path) -> str:
    """When a run actually happened, taken from the run's own record.

    Not from the directory name. The first execution of this script reported
    the sharpness regression BACKWARDS -- 17 subjects "sharper" -- because it
    picked the two most recent directories by name, and a hand-named archive
    `2026-08-25-tone-fix` sorts after the timestamped `2026-08-25-1327`. The
    numbers were right and the sign was inverted, which is the most dangerous
    way for an instrument to be wrong: it would have certified a regression as
    an improvement, and only prior knowledge of the true direction caught it.

    RUN.txt is written by the run itself and is authoritative.
    """
    run = d / "RUN.txt"
    if run.exists():
        for line in run.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("gallery run"):
                return line.split(":", 1)[1].strip()
    return d.name


def ordered_runs() -> list[Path]:
    runs = [d for d in HISTORY.glob("*") if d.is_dir() and any(d.glob("*.jpg"))]
    return sorted(runs, key=run_time)


def sharpness(a: np.ndarray) -> float:
    y = a.astype(np.float64).mean(2)
    return float(np.sqrt(np.diff(y, axis=1).var() + np.diff(y, axis=0).var()))


def main() -> int:
    if len(sys.argv) == 3:
        new, old = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        runs = ordered_runs()
        if len(runs) < 2:
            print("need two runs under gallery-history to compare", file=sys.stderr)
            return 2
        new, old = runs[-1], runs[-2]

    print(f"new: {new}   ({run_time(new)})")
    print(f"old: {old}   ({run_time(old)})\n")
    print(f'{"subject":40s} {"sharpness":>10s} {"mean|d|":>9s}   note')
    print("-" * 78)

    softer, sharper, rows = [], [], []
    for f in sorted(new.glob("*.jpg")):
        o = old / f.name
        if not o.exists():
            print(f"{f.stem:40s} {'NEW':>10s}")
            continue
        a = np.asarray(Image.open(f).convert("RGB"))
        b = np.asarray(Image.open(o).convert("RGB"))
        if a.shape != b.shape:
            print(f"{f.stem:40s} {'RESIZED':>10s}")
            continue
        r = sharpness(a) / sharpness(b)
        d = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).max(2).mean())
        rows.append((f.stem, r, d))
        if r < 1 - FLAG:
            softer.append(f.stem)
        elif r > 1 + FLAG:
            sharper.append(f.stem)

    for n, r, d in sorted(rows, key=lambda t: t[1]):
        note = "SOFTER" if r < 1 - FLAG else ("sharper" if r > 1 + FLAG else "")
        print(f"{n:40s} {r:10.4f} {d:9.2f}   {note}")

    print()
    print(f"{len(rows)} subjects compared: {len(softer)} softer, {len(sharper)} sharper.")
    if softer:
        print("\n  !! LOOK AT THESE BEFORE ACCEPTING THE RUN:")
        for n in softer:
            print(f"       {new / (n + '.jpg')}")
            print(f"       {old / (n + '.jpg')}")
        # A library-wide drift is a different and worse finding than one
        # subject moving: it means something landed that nobody scoped.
        if len(softer) > len(rows) / 3:
            print(
                f"\n  !! {len(softer)} of {len(rows)} subjects lost sharpness. That is not a"
                "\n  !! subject-specific regression, it is a change nobody scoped to the"
                "\n  !! library. Bisect it before landing anything else."
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

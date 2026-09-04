#!/usr/bin/env python3
"""Locate operative 2026-09-06 markers introduced by 2026-09-04 commits."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[2]
TARGETS = (
    Path("docs/STATUS.md"),
    Path("docs/OWNER-ACTIONS.md"),
    Path("experiments/ORCH-verify/host-policy-broadcast-2026-09-06.json"),
)


def blame(rel: Path, line_number: int) -> tuple[str, str]:
    output = subprocess.check_output(
        ["git", "-C", str(REPO), "blame", "--line-porcelain", "-L", f"{line_number},{line_number}", "--", str(rel)],
        text=True, encoding="utf-8",
    )
    lines = output.splitlines()
    commit = lines[0].split()[0]
    epoch = int(next(line.split()[1] for line in lines if line.startswith("author-time ")))
    day = datetime.fromtimestamp(epoch).astimezone().date().isoformat()
    return commit[:10], day


def main() -> int:
    found = []
    for rel in TARGETS:
        for line_number, line in enumerate((REPO / rel).read_text(encoding="utf-8").splitlines(), 1):
            if "2026-09-06" not in line:
                continue
            if "were headed" in line:
                continue
            commit, day = blame(rel, line_number)
            found.append((rel, line_number, commit, day, line.strip()))
    print(f"OPERATIVE_2026_09_06_MARKERS={len(found)}")
    for rel, line_number, commit, day, text in found:
        print(f"{rel}:{line_number} introduced={commit} author_date={day} | {text}")
    wrong_day = [item for item in found if item[3] == "2026-09-04"]
    print(f"INTRODUCED_ON_2026_09_04={len(wrong_day)}")
    if len(found) != 15 or len(wrong_day) != 15:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

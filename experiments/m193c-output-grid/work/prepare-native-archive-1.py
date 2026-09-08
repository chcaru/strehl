"""Exact archive of capture outcome and first native release; no execution."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
paths = [p for p in (here / "runtime-capture-1").rglob("*") if p.is_file()]
paths += [here / name for name in (
    "derivative-runtime-1.json", "independent-runtime-capture-1-read.md",
    "independent-native-release-preparation-review.md", "independent-native-release-1-review.md",
    "native-derivative-release-1.json", "next-program-decision.md",
    "work/runtime-capture-1-console.txt", "work/runtime-capture-1-exit.txt",
    "work/runtime-capture-1-outer.json", "work/prepare-native-release-1.py",
    "work/native-prior-work-1.json", "work/native-prior-work-1.md",
    "work/native-adjacent-dependencies-1.json", "work/check-native-prior-reservation-1.py",
    "work/native-prior-reservation-1.json", "work/prepare-native-archive-1.py",
)]
paths += [root / name for name in (
    "AGENTS.md", "docs/research/M193c-output-grid.md", "docs/proposals/2026-09-sota-program.md")]
assert all(p.is_file() for p in paths), [str(p) for p in paths if not p.is_file()]
names = sorted({p.relative_to(root).as_posix() for p in paths})
(here / "work/archive-native-1.nul").write_bytes(b"\0".join(n.encode() for n in names) + b"\0")
print(f"Prepared {len(names)} exact paths; no git or subject execution.")

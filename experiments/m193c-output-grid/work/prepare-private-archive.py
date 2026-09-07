"""Prepare an exact NUL pathspec for this milestone's source and build archive."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
paths = [p for p in here.iterdir() if p.is_file()]
paths += [p for p in (here / "bridge-build-2").rglob("*") if p.is_file()]
paths += [here / "work" / name for name in (
    "bridge-build-2-console.txt", "bridge-build-2-exit.txt",
    "prepare-private-producer-1.py", "prepare-private-campaign-1.py", "prepare-private-archive.py",
)]
paths += [root / name for name in (
    "AGENTS.md", "docs/proposals/2026-09-sota-program.md", "docs/research/M193c-output-grid.md",
)]
names = sorted({p.relative_to(root).as_posix() for p in paths})
assert all((root / name).is_file() for name in names)
(here / "work/archive-private-1.nul").write_bytes(b"\0".join(name.encode("utf8") for name in names) + b"\0")
print(f"Prepared {len(names)} exact archive paths; no git changes or subject execution.")

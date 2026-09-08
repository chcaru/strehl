"""Exact private2 and completed-build3 archive pathspec; no subject execution."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
assert (here / "independent-private-2-release-review.md").is_file()
paths = [path for path in here.iterdir() if path.is_file()]
paths += [path for path in (here / "bridge-build-3").rglob("*") if path.is_file()]
paths += [here / "work" / name for name in (
    "bridge-build-3-console.txt", "bridge-build-3-exit.txt", "bridge-build-3-outer.json",
    "prepare-private-2.py", "prepare-private-archive-2.py",
)]
paths += [root / name for name in (
    "AGENTS.md", "docs/proposals/2026-09-sota-program.md", "docs/research/M193c-output-grid.md")]
names = sorted({path.relative_to(root).as_posix() for path in paths})
assert all((root / name).is_file() for name in names)
(here / "work/archive-private-2.nul").write_bytes(b"\0".join(name.encode("utf8") for name in names) + b"\0")
print(f"Prepared {len(names)} exact archive paths; no git or subject execution.")

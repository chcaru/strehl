"""Archive completed diagnostic evidence only; do not include in-progress variants."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
paths = [p for p in (here / "active-domain-probe-1").rglob("*") if p.is_file()]
paths += [here / name for name in (
    "independent-active-domain-probe-1-read.md", "work/active-domain-probe-1-console.txt",
    "work/active-domain-probe-1-exit.txt", "work/active-domain-probe-1-outer.json",
    "work/independent-active-domain-probe-1-audit.py", "work/archive-domain-probe-outcome-1.py",
)]
paths += [root / name for name in (
    "AGENTS.md", "docs/research/M193c-output-grid.md", "docs/proposals/2026-09-sota-program.md")]
assert all(p.is_file() for p in paths)
names = sorted({p.relative_to(root).as_posix() for p in paths})
(here / "work/archive-domain-probe-outcome-1.nul").write_bytes(b"\0".join(n.encode() for n in names) + b"\0")
print(f"Prepared {len(names)} exact completed-evidence paths.")

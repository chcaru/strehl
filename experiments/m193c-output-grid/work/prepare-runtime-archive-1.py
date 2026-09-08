"""Exact private2 actual evidence and runtime release archive; no subject run."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
assert (here / "independent-runtime-capture-release-review.md").is_file()
paths = [p for p in (here / "private-campaign-2").rglob("*") if p.is_file()]
paths += [here / name for name in (
    "runtime-capture-release-1.json", "independent-runtime-capture-release-review.md",
    "independent-private-campaign-2-read.md", "independent-native-release-preparation-review.md",
)]
paths += [here / "work" / name for name in (
    "private-campaign-2-console.txt", "private-campaign-2-exit.txt", "private-campaign-2-outer.json",
    "private-campaign-2-evidence-read.py", "private-campaign-2-evidence-read.json",
    "private-campaign-2-evidence-read-attempt-1.py", "private-campaign-2-evidence-read-attempt-1.json",
    "private-campaign-2-evidence-read-attempt-2.py", "private-campaign-2-evidence-read-attempt-2.json",
    "prepare-runtime-capture-1.py", "prepare-runtime-archive-1.py",
    "prepare-native-release-1.py", "prepare-native-release-prototype.py",
)]
paths += [root / name for name in (
    "AGENTS.md", "docs/proposals/2026-09-sota-program.md", "docs/research/M193c-output-grid.md")]
assert all(p.is_file() for p in paths), [str(p) for p in paths if not p.is_file()]
names = sorted({p.relative_to(root).as_posix() for p in paths})
(here / "work/archive-runtime-1.nul").write_bytes(b"\0".join(n.encode() for n in names) + b"\0")
print(f"Prepared {len(names)} exact paths; no git or subject execution.")

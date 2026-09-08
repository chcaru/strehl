"""Archive native refusal metadata and frozen diagnostic; keep large payloads local."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
paths = [p for p in (here / "native-derivative-1").rglob("*") if p.is_file()
         and p.suffix.lower() not in (".arw", ".tiff", ".tif")]
paths += [here / name for name in (
    "independent-native-derivative-1-read.md", "active-domain-probe.py",
    "active-domain-probe-preregister.md", "independent-active-domain-probe-source-review.md",
    "independent-active-domain-release-review.md", "active-domain-probe-release-1.json",
    "coverage-run.py", "coverage-run-preregister.md", "independent-coverage-source-review.md",
    "work/native-derivative-1-console.txt", "work/native-derivative-1-exit.txt",
    "work/native-derivative-1-outer.json", "work/prepare-active-domain-probe-1.py",
    "work/active-domain-probe-1-reservation.json", "work/prepare-domain-probe-archive-1.py",
)]
paths += [root / name for name in (
    "AGENTS.md", "docs/research/M193c-output-grid.md", "docs/proposals/2026-09-sota-program.md")]
assert all(p.is_file() for p in paths)
names = sorted({p.relative_to(root).as_posix() for p in paths})
(here / "work/archive-domain-probe-1.nul").write_bytes(b"\0".join(n.encode() for n in names) + b"\0")
print(f"Prepared {len(names)} exact source/metadata paths; original RAW and unverified TIFF remain local.")

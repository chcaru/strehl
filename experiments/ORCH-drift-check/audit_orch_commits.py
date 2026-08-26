"""Audit every ORCH commit for files outside the orchestrator's ownership.

I swept scripts/check-defaults.py into b988a0e5 without noticing. This checks
whether that was a one-off or a pattern.
"""
import subprocess

OWNED_PREFIXES = (
    "docs/research/ORCH-",
    "experiments/ORCH-",
    "docs/captures-needed.md",
    "README.md",
    "AGENTS.md",
    "scripts/corpus_lint.py",
)

log = subprocess.run(
    ["git", "log", "--format=%H\t%s", "--all"],
    capture_output=True, check=True,
).stdout.decode("utf-8", "replace")

orch = []
for line in log.splitlines():
    if "\t" not in line:
        continue
    sha, subj = line.split("\t", 1)
    if subj.startswith("ORCH:") or subj.startswith("ORCH "):
        orch.append((sha, subj))

print("ORCH commits found: %d" % len(orch))
print()

strays_total = 0
for sha, subj in orch:
    files = subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", sha],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", "replace").split()
    strays = [f for f in files if not f.startswith(OWNED_PREFIXES)]
    if strays:
        strays_total += len(strays)
        print("%s  %s" % (sha[:8], subj[:66]))
        for f in strays:
            print("      STRAY: %s" % f)

print()
print("=" * 62)
print("ORCH commits examined : %d" % len(orch))
print("stray files total     : %d" % strays_total)
print("=" * 62)

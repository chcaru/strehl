"""Census: additive-random nulls standing in for position-deterministic treatments.

ORCH queued this after M110 section 26 withdrew item 89, where an inert null built
by `rng.normal(0, rms)` was used as the control for a LATERAL-CA CORRECTION -- a
radial resample, deterministic in position. The null's own radial profile
manufactured the finding.

grep is the census, not the verdict. A random draw is only a hazard when it is
(a) INJECTED into image data and (b) used as the CONTROL for a treatment that is
deterministic in position. Bootstrap resampling, seeded tile selection and
synthetic self-test fixtures are all legitimate and are separated out here.

Read-only. Reports paths and owners; changes nothing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"
RESEARCH = ROOT / "docs" / "research"

DRAW = re.compile(
    r"\b(?:rng|np\.random|random)\.(?P<fn>normal|standard_normal|poisson|uniform|"
    r"randint|integers|choice|shuffle|permutation|random|rand|randn)\b")

# (a) the draw lands IN image data: added to an array, or assigned into a slice.
INJECT = re.compile(
    r"(?:\+\s*(?:rng|np\.random|random)\.)"          # arr + rng.normal(...)
    r"|(?:\+=\s*(?:rng|np\.random|random)\.)"        # arr += rng.normal(...)
    r"|(?:\[[^\]]*\]\s*=\s*[^=]*(?:rng|np\.random|random)\.)")  # arr[...] = ...rng...


def folded_reports():
    """Milestones whose report exists in docs/research -- ORCH's cap."""
    out = set()
    for p in RESEARCH.glob("*.md"):
        m = re.match(r"(M\d+|m\d+)", p.stem)
        if m:
            out.add(m.group(1).upper())
    return out


def milestone_of(path: Path) -> str:
    rel = path.relative_to(EXP)
    m = re.match(r"(M\d+|m\d+)", rel.parts[0])
    return m.group(1).upper() if m else "?"


def classify(line: str, fn: str) -> str:
    if INJECT.search(line):
        return "INJECTION"
    if fn in ("choice", "randint", "integers") and re.search(
            r"boot|resampl|idx|indices|sample", line, re.I):
        return "bootstrap"
    if fn in ("shuffle", "permutation"):
        return "permutation"
    return "other"


def main():
    folded = folded_reports()
    rows = []
    for p in sorted(EXP.rglob("*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = DRAW.search(line)
            if not m:
                continue
            rows.append((p, i, line.strip(), classify(line, m.group("fn"))))

    by_kind = {}
    for _, _, _, k in rows:
        by_kind[k] = by_kind.get(k, 0) + 1
    print("ALL i.i.d. draws under experiments/, by use:")
    for k, v in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"  {k:<12} {v:>5}")
    print(f"  {'TOTAL':<12} {len(rows):>5} in "
          f"{len({r[0] for r in rows})} file(s)\n")

    inj = [r for r in rows if r[3] == "INJECTION"]
    print(f"INJECTION sites -- a draw landing IN image data: {len(inj)} in "
          f"{len({r[0] for r in inj})} file(s)")
    print(f"ORCH's cap: milestones with a report in docs/research "
          f"({len(folded)} folded)\n")

    seen = {}
    for p, i, line, _ in inj:
        seen.setdefault(p, []).append((i, line))
    for p in sorted(seen):
        ms = milestone_of(p)
        tag = "FOLDED" if ms in folded else "unfolded"
        rel = p.relative_to(ROOT).as_posix()
        print(f"[{tag:8}] {ms:<6} {rel}")
        for i, line in seen[p]:
            print(f"             :{i}  {line[:104]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

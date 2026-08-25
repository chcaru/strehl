"""Census stage 2: which INJECTION sites are actually NULLS, and for what treatment.

Stage 1 (null_census.py) found 259 injection sites in 142 files. Most are not the
hazard: a simulator adding shot noise is modelling noise, and a positive control
planting a known effect is meant to be random. The hazard is narrower --

    an i.i.d. draw standing in for a treatment that is DETERMINISTIC IN POSITION.

Two independent discriminators, because ORCH's fleet-wide lesson tonight is that a
form-based screen false-clears:

  NAME      the enclosing def / assignment target / nearest comment says null,
            control, placebo, inert, sham, scramble, decoy.
  STRUCTURE the same file also names a position-deterministic treatment
            (resample, warp, shift, radial, CA, dust, hot pixel, fixed pattern,
            quantise, demosaic, drizzle, interpolate).

Neither is the verdict. Both are printed so every candidate can be read by hand.
Read-only.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"
RESEARCH = ROOT / "docs" / "research"
SELF = {"null_census.py", "null_census2.py"}

INJECT = re.compile(
    r"(?:\+\s*(?:rng|np\.random|random)\.)"
    r"|(?:\+=\s*(?:rng|np\.random|random)\.)"
    r"|(?:\[[^\]]*\]\s*=\s*[^=]*(?:rng|np\.random|random)\.)")

NULLISH = re.compile(
    r"null|control|placebo|inert|sham|scrambl|decoy|shuffl|baseline|surrogate",
    re.I)

# treatments that are deterministic in position -- the class ORCH named
DETERMINISTIC = re.compile(
    r"resampl|warp|remap|shift|radial|\bca\b|chromatic|lateral|dust|hot[_ ]?pix|"
    r"fixed[_ -]?pattern|quantis|quantiz|narrow|demosaic|drizzl|interp|"
    r"distort|vignett|align|homograph|affine", re.I)


def folded():
    out = set()
    for p in RESEARCH.glob("*.md"):
        m = re.match(r"(M\d+|m\d+)", p.stem)
        if m:
            out.add(m.group(1).upper())
    return out


def enclosing_def(lines, idx):
    for j in range(idx, -1, -1):
        m = re.match(r"\s*def\s+(\w+)", lines[j])
        if m:
            return m.group(1)
    return "<module>"


def main():
    fold = folded()
    cand, other = [], []
    for p in sorted(EXP.rglob("*.py")):
        if p.name in SELF:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        ms = re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0])
        ms = ms.group(1).upper() if ms else "?"
        file_det = bool(DETERMINISTIC.search(text))
        for i, line in enumerate(lines):
            if not INJECT.search(line):
                continue
            fn = enclosing_def(lines, i)
            ctx = "\n".join(lines[max(0, i - 4):i + 2])
            name_null = bool(NULLISH.search(fn) or NULLISH.search(ctx))
            rec = (ms, p, i + 1, line.strip(), fn, name_null, file_det)
            (cand if (name_null and file_det) else other).append(rec)

    print(f"injection sites: {len(cand) + len(other)}")
    print(f"  name says NULL *and* file names a position-deterministic "
          f"treatment : {len(cand)}   <- candidates")
    print(f"  everything else (simulator noise, planted positives, "
          f"unrelated)          : {len(other)}\n")

    infold = [c for c in cand if c[0] in fold]
    print(f"candidates in FOLDED milestones (ORCH's cap): {len(infold)} "
          f"in {len({c[1] for c in infold})} file(s)\n")
    print("=" * 78)
    for ms, p, ln, line, fn, _, _ in infold:
        print(f"{ms:<6} {p.relative_to(ROOT).as_posix()}:{ln}  def {fn}()")
        print(f"       {line[:100]}")
    print("=" * 78)

    unf = [c for c in cand if c[0] not in fold]
    if unf:
        print(f"\ncandidates in UNFOLDED milestones (deferred per cap): "
              f"{len(unf)} in {len({c[1] for c in unf})} file(s)")
        for ms, p, ln, _, fn, _, _ in unf:
            print(f"  {ms:<6} {p.relative_to(ROOT).as_posix()}:{ln}  {fn}()")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

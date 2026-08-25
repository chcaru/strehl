"""Census stage 4: excess-over-null by dataflow, tightened on the OUTPUT side.

Stage 3 was sound (it caught the known member) but loose: 227 files, because
"a random value and a clean value reach the same function" also describes every
simulator, bootstrap and planted positive control in the tree.

The tight signature of an excess-over-null is on the output side:

    a CLEAN-derived quantity is subtracted from / divided by / compared against
    a RANDOM-TAINTED quantity.

That is what `ex = x["overshoot_pct"] - nx.get("overshoot_pct")` is in the known
member, and it is what makes the null LOAD-BEARING: the reported number is the
difference, so the null's own structure is inside the headline.

Stage 4 = stage 3's taint analysis + that requirement. Re-commissioned against
the known member; if the tightening drops the seed, the tightening is wrong and
the run aborts.

Read-only. Names files and owners; changes nothing.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"
RESEARCH = ROOT / "docs" / "research"
SELF = {"null_census.py", "null_census2.py", "null_census3.py",
        "null_census4.py"}

DRAW_FNS = {"normal", "standard_normal", "poisson", "uniform", "randint",
            "integers", "random", "rand", "randn", "choice", "permutation",
            "shuffle", "lognormal", "exponential"}


def is_draw(node):
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in DRAW_FNS:
        base = f.value
        while isinstance(base, ast.Attribute):
            base = base.value
        if isinstance(base, ast.Name) and re.search(
                r"rng|random|rs|gen", base.id, re.I):
            return True
    return False


def contains_draw(node):
    return any(is_draw(n) for n in ast.walk(node))


def names_in(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def targets_of(stmt):
    out = set()
    tgts = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
    for t in tgts:
        for n in ast.walk(t):
            if isinstance(n, ast.Name):
                out.add(n.id)
            elif isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
                out.add(n.value.id)
    return out


def taint_of(scope):
    """Fixed-point taint set for one function scope."""
    tainted, origin = set(), {}
    for _ in range(4):
        for stmt in ast.walk(scope):
            if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                if stmt.value is None:
                    continue
                if contains_draw(stmt.value) or (names_in(stmt.value) & tainted):
                    for t in targets_of(stmt):
                        if t not in tainted:
                            tainted.add(t)
                            origin[t] = stmt.lineno
            elif isinstance(stmt, (ast.For, ast.comprehension)):
                it = stmt.iter
                if names_in(it) & tainted or contains_draw(it):
                    tgt = stmt.target
                    for n in ast.walk(tgt):
                        if isinstance(n, ast.Name) and n.id not in tainted:
                            tainted.add(n.id)
                            origin[n.id] = getattr(stmt, "lineno", 0)
    return tainted, origin


def excess_sites(path):
    """[(lineno, snippet)] where clean and tainted quantities are combined."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (SyntaxError, ValueError, OSError):
        return []
    lines = src.splitlines()
    out = []
    scopes = [n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.Module))]
    for scope in scopes:
        tainted, _ = taint_of(scope)
        if not tainted:
            continue
        for node in ast.walk(scope):
            ops = None
            if isinstance(node, ast.BinOp) and isinstance(
                    node.op, (ast.Sub, ast.Div)):
                ops = (node.left, node.right)
            elif isinstance(node, ast.Compare) and len(node.comparators) == 1:
                ops = (node.left, node.comparators[0])
            if not ops:
                continue
            ln_, rn_ = names_in(ops[0]), names_in(ops[1])
            lt, rt = bool(ln_ & tainted), bool(rn_ & tainted)
            if lt == rt:
                continue                       # both or neither: not an excess
            if not (ln_ and rn_):
                continue                       # need a real name on both sides
            ln = getattr(node, "lineno", 0)
            snip = lines[ln - 1].strip() if 0 < ln <= len(lines) else ""
            out.append((ln, snip, sorted((ln_ | rn_) & tainted)[0]))
    # dedupe by line
    seen, ded = set(), []
    for ln, snip, tv in sorted(out):
        if ln not in seen:
            seen.add(ln)
            ded.append((ln, snip, tv))
    return ded


def folded():
    out = set()
    for p in RESEARCH.glob("*.md"):
        m = re.match(r"(M\d+|m\d+)", p.stem)
        if m:
            out.add(m.group(1).upper())
    return out


def main():
    fold = folded()
    hits = {}
    for p in sorted(EXP.rglob("*.py")):
        if p.name in SELF:
            continue
        e = excess_sites(p)
        if e:
            hits[p] = e

    seed = EXP / "M110-sheet" / "ca_overshoot.py"
    ok = seed in hits
    print(f"[{'PASS' if ok else 'FAIL'}] re-commissioning after tightening: "
          f"known member detected = {ok}")
    if not ok:
        print("      the tightening dropped the seed -> the tightening is "
              "wrong, not the corpus. Aborting.")
        return 1
    seedlines = [ln for ln, _, _ in hits[seed]]
    print(f"       seed excess sites: {seedlines[:8]} "
          f"(expect 186, the `x[...] - nx.get(...)` line)\n")

    infold = {p: v for p, v in hits.items()
              if (re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0]) or [None])
              and (re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0]).group(1).upper()
                   if re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0]) else "?") in fold}
    print(f"files with an excess-over-null site: {len(hits)}")
    print(f"  of those, in FOLDED milestones (ORCH's cap): {len(infold)}")
    print(f"  total excess sites in folded files: "
          f"{sum(len(v) for v in infold.values())}\n")

    by_ms = {}
    for p in infold:
        ms = re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0]).group(1).upper()
        by_ms.setdefault(ms, []).append(p)
    for ms in sorted(by_ms):
        print(f"{ms:<7} {len(by_ms[ms])} file(s)")
        for p in sorted(by_ms[ms]):
            print(f"         {p.relative_to(ROOT).as_posix()}  "
                  f"{[ln for ln, _, _ in hits[p]][:5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

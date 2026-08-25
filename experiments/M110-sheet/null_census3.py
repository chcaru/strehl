"""Census stage 3: find null arms by DATAFLOW, not by name.

Stage 2 used a name screen (enclosing def / nearby comment says "null",
"control", "placebo"...). It FAILED ITS OWN COMMISSIONING: the known member,
M110's ca_overshoot.py:162, was cleared, because its `# Inert null:` comment sits
at line 157 and the context window started at 158, and its enclosing function is
called `main`. One line of window decided it. That is the fifth form-based screen
to die on this fleet tonight and it is not to be trusted.

The name-independent signature of "a random draw used as the CONTROL ARM" is
dataflow:

    1. a variable is assigned from an i.i.d. draw            -> tainted
    2. taint propagates through assignments                  -> d_null = ry(fake)
    3. the tainted variable is passed to some f() at argpos k
    4. the SAME f() also receives an UNTAINTED variable at argpos k elsewhere

Step 4 is the arm pair: the same estimator, run once on real data and once on
noise, so the two can be differenced. That is what an excess-over-null is, and it
is visible without any variable ever being named "null".

Commissioned below against the known member. Read-only; changes nothing.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"
RESEARCH = ROOT / "docs" / "research"
SELF = {"null_census.py", "null_census2.py", "null_census3.py"}

DRAW_FNS = {"normal", "standard_normal", "poisson", "uniform", "randint",
            "integers", "random", "rand", "randn", "choice", "permutation",
            "shuffle", "lognormal", "exponential"}

DETERMINISTIC = re.compile(
    r"resampl|warp|remap|shift|radial|chromatic|lateral|dust|hot[_ ]?pix|"
    r"fixed[_ -]?pattern|quantis|quantiz|narrow|demosaic|drizzl|interp|"
    r"distort|vignett|align|homograph|affine|\bca\b|\bcrop\b|jitter", re.I)


def is_draw(node):
    """Call to rng.normal / np.random.standard_normal / ..."""
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in DRAW_FNS:
        base = f.value
        while isinstance(base, ast.Attribute):
            base = base.value
        if isinstance(base, ast.Name) and re.search(
                r"rng|random|rs|generator", base.id, re.I):
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


def analyse(path):
    """Return [(line, callee, argpos, tainted_arg, clean_partner)] for this file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return []

    findings = []
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.Module))]:
        tainted, origin = set(), {}
        # two passes so taint assigned late still marks earlier-declared names
        for _ in range(3):
            for stmt in ast.walk(fn):
                if not isinstance(stmt, (ast.Assign, ast.AugAssign,
                                         ast.AnnAssign)):
                    continue
                if stmt.value is None:
                    continue
                direct = contains_draw(stmt.value)
                via = bool(names_in(stmt.value) & tainted)
                if direct or via:
                    for t in targets_of(stmt):
                        if t not in tainted:
                            tainted.add(t)
                            origin[t] = stmt.lineno
        if not tainted:
            continue
        # calls: (callee, argpos) -> set of arg root names
        slots = {}
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            cf = call.func
            name = cf.attr if isinstance(cf, ast.Attribute) else (
                cf.id if isinstance(cf, ast.Name) else None)
            if not name:
                continue
            for k, arg in enumerate(call.args):
                roots = {n.id for n in ast.walk(arg) if isinstance(n, ast.Name)}
                if roots:
                    slots.setdefault((name, k), []).append((call.lineno, roots))
        for (name, k), uses in slots.items():
            dirty = [(ln, r) for ln, r in uses if r & tainted]
            clean = [(ln, r) for ln, r in uses if not (r & tainted)]
            if dirty and clean:
                ln, roots = dirty[0]
                tv = sorted(roots & tainted)[0]
                findings.append((ln, name, k, tv,
                                 sorted(clean[0][1])[0], origin.get(tv, ln)))
    return findings


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
    scanned = 0
    for p in sorted(EXP.rglob("*.py")):
        if p.name in SELF:
            continue
        scanned += 1
        f = analyse(p)
        if not f:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if not DETERMINISTIC.search(text):
            continue
        hits[p] = f

    print(f"scanned {scanned} python files under experiments/")
    print(f"files where a RANDOM-TAINTED value and a CLEAN value reach the same")
    print(f"estimator at the same argument position, AND the file names a")
    print(f"position-deterministic treatment: {len(hits)}\n")

    # ---- commissioning: the known member must appear ----
    seed = EXP / "M110-sheet" / "ca_overshoot.py"
    ok = seed in hits
    print(f"[{'PASS' if ok else 'FAIL'}] commissioning: known member "
          f"{seed.relative_to(ROOT).as_posix()} detected = {ok}")
    if not ok:
        print("      instrument is not commissioned; do not trust the census")
        return 1
    print()

    for p in sorted(hits, key=lambda q: q.as_posix()):
        ms = re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0])
        ms = ms.group(1).upper() if ms else "?"
        tag = "FOLDED" if ms in fold else "unfold"
        print(f"[{tag}] {ms:<6} {p.relative_to(ROOT).as_posix()}")
        for ln, name, k, tv, cv, org in sorted(hits[p])[:6]:
            print(f"         :{ln}  {name}(arg{k}) <- {tv!r} (drawn :{org})"
                  f"  vs {cv!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

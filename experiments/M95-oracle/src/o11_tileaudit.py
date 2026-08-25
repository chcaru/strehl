"""O11 -- provenance audit of pick_tiles call sites in the trees M95 owns.

ORCH's question, exactly: which scripts RE-SELECT tiles per arm, and which
SELECT ONCE and reuse? A pinned selection cannot differ between arms even in
principle, so it is structurally safe regardless of input precision; a
per-arm selection inherits whatever narrowing its input carried.

This is answered by parsing rather than by reading, because the question is
structural and 35 files is exactly the size where eyeballing goes wrong.

For each call to pick_tiles the audit reports:
  - lexical loop depth at the call site
  - the enclosing function, and whether THAT function is itself called from
    inside a loop (a call at depth 0 inside a helper invoked per arm is a
    re-selection and the depth alone would miss it)
  - the argument expression, so a call inside a loop whose argument does not
    vary with the loop can be recognised as effectively pinned
  - every reader the file uses, for provenance

CLASSIFICATION, decided by the script and not by me afterwards:
  RESELECT  -- any call at loop depth > 0, or in a helper reached from a loop,
               or more than one call site whose arguments differ
  ONCE      -- exactly one reachable selection, at loop depth 0
  REVIEW    -- anything the rules above cannot decide; these get read by hand

PROVENANCE is reported as the set of readers found, not inferred: rawpy on
.ARW is native precision; np.load or tifffile on a path under strehl-out is
another milestone's scratch and inherits its precision.
"""

from __future__ import annotations

import ast
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
EXP = os.path.join(ROOT, "experiments")
OUTD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
MINE = ["M95-resample", "M95-coverage", "M95-demosaic", "M95-kernel",
        "M95-cdiff", "M95-dose"]
LOOPS = (ast.For, ast.AsyncFor, ast.While, ast.comprehension)
READERS = {
    "rawpy.imread": "camera RAW (native)",
    "imread_raw": "camera RAW (native)",
    "tifffile.imread": "TIFF",
    "Image.open": "PIL (NARROWING on 16-bit RGB)",
    "np.load": "npy scratch",
    "np.fromfile": "raw scratch",
}


def parents(tree):
    p = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            p[ch] = node
    return p


def loop_depth(node, par, stop=None):
    d, cur = 0, par.get(node)
    while cur is not None and cur is not stop:
        if isinstance(cur, (ast.For, ast.AsyncFor, ast.While)):
            d += 1
        if isinstance(cur, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            d += 1
        cur = par.get(cur)
    return d


def enclosing_func(node, par):
    cur = par.get(node)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
        cur = par.get(cur)
    return None


def call_name(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        try:
            return ast.unparse(f)
        except Exception:
            return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def audit(path):
    src = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return dict(error=f"SyntaxError line {e.lineno}")
    par = parents(tree)
    lines = src.splitlines()

    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and call_name(n).split(".")[-1] == "pick_tiles"]
    if not calls:
        return None

    # Where is each function DEFINED called from, and at what loop depth?
    fdepth = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            nm = call_name(n).split(".")[-1]
            fdepth.setdefault(nm, []).append(loop_depth(n, par))

    sites = []
    for c in calls:
        fn = enclosing_func(c, par)
        d = loop_depth(c, par, stop=fn)
        outer = 0
        fname = None
        if fn is not None:
            fname = fn.name
            ds = fdepth.get(fname, [])
            outer = max(ds) if ds else -1
        try:
            arg = ast.unparse(c.args[0]) if c.args else ""
        except Exception:
            arg = ""
        sites.append(dict(line=c.lineno, depth=d, func=fname, caller_depth=outer,
                          arg=arg, text=lines[c.lineno - 1].strip()[:110]))

    readers = sorted({v for n in ast.walk(tree) if isinstance(n, ast.Call)
                      for k, v in READERS.items()
                      if call_name(n) == k or call_name(n).endswith("." + k)})
    if "rawpy" in src and "camera RAW (native)" not in readers:
        readers.append("rawpy imported")
    scratch = sorted({s.value for s in ast.walk(tree)
                      if isinstance(s, ast.Constant) and isinstance(s.value, str)
                      and "strehl-out" in s.value})
    arw = any(isinstance(s, ast.Constant) and isinstance(s.value, str)
              and (".ARW" in s.value.upper() or "dev\\macro" in s.value
                   or "dev/macro" in s.value)
              for s in ast.walk(tree))

    eff = [s for s in sites if s["depth"] > 0 or s["caller_depth"] > 0]
    args = {s["arg"] for s in sites}
    if eff:
        cls = "RESELECT"
    elif len(sites) == 1:
        cls = "ONCE"
    elif len(args) == 1:
        cls = "ONCE-EQUIV"
    else:
        cls = "REVIEW"
    return dict(sites=sites, readers=readers, scratch=scratch, arw=arw, cls=cls)


def main() -> int:
    if not os.path.isdir(EXP):
        raise SystemExit(f"COVERAGE FAILURE: experiments dir not found at {EXP}")
    expect = {}
    for tree_name in MINE:
        d = os.path.join(EXP, tree_name, "src")
        if not os.path.isdir(d):
            raise SystemExit(f"COVERAGE FAILURE: {d} does not exist")
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".py") and "pick_tiles" in open(
                    os.path.join(d, fn), encoding="utf-8").read():
                expect[f"{tree_name}/{fn}"] = os.path.join(d, fn)
    print(f"files textually containing pick_tiles in the trees M95 owns: "
          f"{len(expect)}")
    if not expect:
        raise SystemExit("COVERAGE FAILURE: grep says 35, this says 0")

    res, counts = {}, {}
    for tree_name in MINE:
        d = os.path.join(EXP, tree_name, "src")
        print("\n" + "=" * 78)
        print(tree_name)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            r = audit(os.path.join(d, fn))
            if r is None:
                if f"{tree_name}/{fn}" in expect:
                    print(f"  {'TEXT-ONLY':11s} {fn:22s} "
                          f"mentions pick_tiles but never CALLS it "
                          f"(import, def, or comment)")
                    res[f"{tree_name}/{fn}"] = dict(cls="TEXT-ONLY", sites=[],
                                                    readers=[], scratch=[],
                                                    arw=False)
                    counts["TEXT-ONLY"] = counts.get("TEXT-ONLY", 0) + 1
                continue
            key = f"{tree_name}/{fn}"
            res[key] = r
            counts[r["cls"]] = counts.get(r["cls"], 0) + 1
            prov = ("ARW" if r["arw"] else "") + \
                   (" SCRATCH" if r["scratch"] else "")
            print(f"  {r['cls']:11s} {fn:22s} sites={len(r['sites'])} "
                  f"prov=[{prov.strip() or 'none-literal'}] "
                  f"readers={r['readers'] or ['-']}")
            for s in r["sites"]:
                print(f"      L{s['line']:<5d} loopdepth={s['depth']} "
                      f"in={s['func']} callerdepth={s['caller_depth']} "
                      f"arg={s['arg'][:60]}")

    missing = sorted(set(expect) - set(res))
    print("\n" + "=" * 78)
    print(f"COVERAGE: expected {len(expect)} files, audited {len(res)}")
    if missing:
        raise SystemExit(f"COVERAGE FAILURE: not audited {missing}")

    print("SUMMARY over the trees M95 owns:")
    for k in sorted(counts):
        print(f"  {k:11s} {counts[k]}")
    resel = [k for k, v in res.items() if v["cls"] == "RESELECT"]
    rev = [k for k, v in res.items() if v["cls"] == "REVIEW"]
    print(f"\n  RESELECT (exposed pattern): {resel or 'NONE'}")
    print(f"  REVIEW (script cannot decide, read by hand): {rev or 'NONE'}")
    with open(os.path.join(OUTD, "o11_tileaudit.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"\nwrote {os.path.join(OUTD, 'o11_tileaudit.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

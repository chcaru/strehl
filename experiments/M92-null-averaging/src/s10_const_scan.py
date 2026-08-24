"""M92b S10 -- scan every experiment script for hard-coded sensor constants and
check each one against the stacks that script actually reads.

M92 facts 1241-1243 recorded one instance: `ISO = 500` applied to an ISO-160
stack.  A hard-coded sensor constant is a CLASS of defect, so this scans all of
`experiments/` and classifies every instance found:

  MISMATCH   the constant contradicts the EXIF ISO of a stack the file names
  MATCH      the constant agrees with every stack the file names -- still a
             LATENT defect, because nothing prevents the file being pointed at
             another stack, but no number currently in the corpus is wrong
  UNRESOLVED the file names no stack this scanner recognises, so the scanner
             cannot decide; these are listed for manual reading, never silently
             dropped

The distinction matters because the orchestrator asked for the harmless ones to
be named as well as the harmful ones.  A MATCH is reported, not suppressed.

Ground truth comes from `out/s9_iso_truth.json` (EXIF over every frame of every
stack), never from a name convention.

Read-only over the repository.  Writes only to this experiment's out/.
"""
import ast
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402,F401  (adds m57lib/m41lib to sys.path)
import m57lib as M57  # noqa: E402

EXP = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))            # .../experiments
REPO = os.path.dirname(EXP)                 # repository root
assert os.path.isdir(os.path.join(EXP, "m57-shape-metric")), EXP
assert os.path.isfile(os.path.join(REPO, "AGENTS.md")), REPO

# Names the scanner treats as sensor constants. `BLACK`/`WHITE` are rig
# constants rather than per-stack ones and are scanned separately.
SENSOR = {"ISO", "iso", "ISO_", "GAIN", "G", "GAIN_DN_PER_E", "g_dn",
          "RN_E", "RN", "READ_NOISE_E", "rn_e"}
RIG = {"BLACK", "BLACK_LEVEL", "WHITE", "WHITE_LEVEL"}

RIG_TRUTH = {"BLACK": 512.0, "BLACK_LEVEL": 512.0,
             "WHITE": 15360.0, "WHITE_LEVEL": 15360.0}


def const_value(node):
    """Fold a literal or a literal-only arithmetic expression, else None."""
    try:
        return float(ast.literal_eval(node))
    except Exception:
        pass
    try:
        src = ast.unparse(node)
    except Exception:
        return None
    if not re.fullmatch(r"[0-9eE_.+\-*/() ]+", src):
        return None
    try:
        return float(eval(src, {"__builtins__": {}}, {}))  # literals only
    except Exception:
        return None


def scan_file(path):
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target])
        val = node.value
        if val is None:
            continue
        for t in targets:
            # Tuple unpacking hides a constant from a naive scan:
            # `PAD, G, RN_E, ISO = 32, 1.14469, 1.47, 500` assigns ISO = 500
            # but the target is a Tuple, not a Name. m57's s7 does exactly
            # this, so a scanner that skips it under-reports the defect.
            pairs = []
            if isinstance(t, ast.Name):
                pairs = [(t, val)]
            elif (isinstance(t, (ast.Tuple, ast.List))
                    and isinstance(val, (ast.Tuple, ast.List))
                    and len(t.elts) == len(val.elts)):
                pairs = list(zip(t.elts, val.elts))
            for tn, tv in pairs:
                if not isinstance(tn, ast.Name):
                    continue
                if tn.id not in SENSOR and tn.id not in RIG:
                    continue
                v = const_value(tv)
                if v is None:
                    continue
                try:
                    text = ast.unparse(tv)
                except Exception:
                    text = str(v)
                hits.append(dict(name=tn.id, value=v, line=node.lineno,
                                 expr=text))
    return hits


def path_literals(tree):
    """String literals excluding docstrings.

    A stack name inside a module or function docstring is prose describing
    a regime, not a path being opened. `m61-ptc-high-iso/03-power-control.py`
    is a pure synthetic plant whose docstring names `foam`; counting that as
    a stack the file reads produces a false MISMATCH.
    """
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            b = getattr(n, "body", None)
            if (b and isinstance(b[0], ast.Expr)
                    and isinstance(b[0].value, ast.Constant)
                    and isinstance(b[0].value.value, str)):
                docs.add(id(b[0].value))
    return " ".join(n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant)
                    and isinstance(n.value, str) and id(n) not in docs)


def load_truth():
    """(by_name, collisions) from S9's per-frame EXIF ground truth."""
    truth = json.load(open(os.path.join(M92.OUT, "s9_iso_truth.json")))
    capture = {v["name"]: v for k, v in truth.items()
               if k.startswith("capture|")}
    dark = {v["name"]: v for k, v in truth.items() if k.startswith("dark|")}
    collisions = {n: dict(capture=capture[n]["iso"], dark=dark[n]["iso"])
                  for n in set(capture) & set(dark)
                  if capture[n]["iso"] != dark[n]["iso"]}
    by_name = dict(dark)
    by_name.update(capture)          # capture root wins for the ISO check
    return by_name, collisions


def classify(r, by_name):
    nm, v, stacks = r["name"], r["value"], r["stacks"]
    if nm in RIG:
        want = RIG_TRUTH[nm]
        return ("MATCH" if abs(v - want) < 1e-9 else "MISMATCH",
                f"rig constant, AGENTS rig section says {want:g}")
    if not stacks:
        return "UNRESOLVED", "file names no recognised stack"
    if nm in ("ISO", "iso", "ISO_"):
        bad = [s for s in stacks if by_name[s]["iso"] != v]
        if not bad:
            return "MATCH", f"all {len(stacks)} stack(s) are ISO {v:g}"
        return "MISMATCH", (f"ISO {v:g} but "
                            + ", ".join(f"{s}={by_name[s]['iso']}"
                                        for s in bad[:6]))
    if nm in ("G", "GAIN", "GAIN_DN_PER_E", "g_dn"):
        bad = [s for s in stacks
               if abs(M57.gain_dn_per_e(by_name[s]["iso"]) - v) > 1e-4]
        if not bad:
            return "MATCH", f"gain matches all {len(stacks)} stack(s)"
        return "MISMATCH", (f"g={v:.5f} but "
                            + ", ".join(
                                f"{s} needs "
                                f"{M57.gain_dn_per_e(by_name[s]['iso']):.5f}"
                                for s in bad[:4]))
    bad = [s for s in stacks
           if abs(M57.read_noise_e(by_name[s]["iso"]) - v) > 1e-4]
    if not bad:
        return "MATCH", f"read noise matches all {len(stacks)} stack(s)"
    return "MISMATCH", (f"rn_e={v:g} but "
                        + ", ".join(
                            f"{s}(ISO {by_name[s]['iso']}) needs "
                            f"{M57.read_noise_e(by_name[s]['iso']):g}"
                            for s in bad[:4]))


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    truth = json.load(open(os.path.join(M92.OUT, "s9_iso_truth.json")))
    by_name, collisions = load_truth()
    names = sorted(by_name, key=len, reverse=True)

    log("=" * 78)
    log("M92b S10 -- hard-coded sensor constants across experiments/.")
    log(f"  ground truth: {len(truth)} stacks, EXIF over every frame")
    log(f"  canonical: g(iso) = max(iso, {M57.BASE_ISO})/{M57.GAIN_DIVISOR};"
        f" rn(iso) = {M57.RN_E_HIGH} if iso >= {M57.SECOND_BASE_ISO}"
        f" else {M57.RN_E_LOW}")
    log("=" * 78)

    if collisions:
        log("")
        log("  NAME COLLISION ACROSS CAPTURE ROOTS -- a bare stack name does")
        log("  not identify a stack, and the two resolve to different ISOs:")
        for k, v in sorted(collisions.items()):
            log(f"    {k}: D:\\personal\\macro = ISO {v['capture']},"
                f"  D:\\macro-dark-frames = ISO {v['dark']}")

    rows, vendored = [], 0
    for dirpath, dirnames, filenames in os.walk(EXP):
        dirnames[:] = [d for d in dirnames
                       if d not in ("out", "__pycache__", ".git")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, REPO).replace("\\", "/")
            if rel.startswith("experiments/M92-null-averaging"):
                continue
            if "/build-head/" in rel:
                # M62 vendored a whole copy of the repository under
                # experiments/M62-sqrt-n/build-head/. Its hits are duplicates
                # of the originals, counted here and excluded from the tables.
                vendored += len(scan_file(p))
                continue
            hits = scan_file(p)
            if not hits:
                continue
            src = open(p, encoding="utf-8", errors="replace").read()
            lits = path_literals(ast.parse(src))
            used = [nm for nm in names if nm in lits]
            used = [nm for nm in used
                    if not any(nm != o and nm in o for o in used)]
            for h in hits:
                rows.append(dict(file=rel, stacks=used, **h))

    for r in rows:
        r["verdict"], r["why"] = classify(r, by_name)
        r["kind"] = "rig" if r["name"] in RIG else "per-stack"

    log("")
    log(f"  scanned {len({r['file'] for r in rows})} file(s) with at least one"
        f" constant; {len(rows)} instance(s).")
    log(f"  excluded {vendored} instance(s) under"
        f" experiments/M62-sqrt-n/build-head/ -- M62 vendored a whole copy of")
    log("  the repository, so its hits duplicate the originals verbatim.")

    for kind in ("per-stack", "rig"):
        for want in ("MISMATCH", "MATCH", "UNRESOLVED"):
            sel = [r for r in rows
                   if r["verdict"] == want and r["kind"] == kind]
            if not sel:
                continue
            log("")
            log("=" * 78)
            log(f"  {kind.upper()} / {want}: {len(sel)} instance(s)")
            log("=" * 78)
            if kind == "rig":
                log("  Rig constants have no per-stack meaning; a MATCH here is")
                log("  agreement with the AGENTS rig section, nothing more.")
                seen = {}
                for r in sorted(sel, key=lambda r: (r["name"], r["value"])):
                    k = (r["name"], r["value"])
                    seen.setdefault(k, []).append(r["file"])
                for (nm, v), fs in sorted(seen.items()):
                    log(f"  {nm} = {v:g}   in {len(fs)} file(s)")
                    if want == "MISMATCH":
                        for f in fs:
                            log(f"      {f}")
                continue
            for r in sorted(sel, key=lambda r: (r["file"], r["line"])):
                st = ",".join(r["stacks"][:5]) or "-"
                log(f"  {r['file']}:{r['line']}  {r['name']} = {r['expr']}")
                log(f"      stacks: {st}")
                log(f"      -> {r['why']}")

    with open(os.path.join(M92.OUT, "s10_const_scan.json"), "w") as fh:
        json.dump(rows, fh, indent=2, default=float)
    with open(os.path.join(M92.OUT, "s10_const_scan.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote out/s10_const_scan.{{json,log}}  ({len(rows)} instances)")


if __name__ == "__main__":
    main()

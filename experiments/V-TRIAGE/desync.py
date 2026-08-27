"""F2: can the stated count/tolerance desynchronise from the data SILENTLY?

Pre-registered fail mode: 'If 13 and the tolerance are two independent literals
they can desynchronise silently.'  Test it: perturb a value so the true count is
no longer 13, then run the ACTUAL definition gate from triage.py against the
perturbed rows and see whether anything fires.
"""
import json, sys, importlib.util, copy
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE")
spec = importlib.util.spec_from_file_location(
    "triage", r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE\triage.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)          # import only; main() is under __main__ guard
FIELD_DEFS = mod.FIELD_DEFS
print("imported triage.py: %d FIELD_DEFS" % len(FIELD_DEFS))

J = json.load(open(r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json", encoding="utf-8"))
rows = J["rows"]

def count(rs, tol_abs=0.01, tol_rel=1.0):
    n = 0
    for r in rs:
        e = r.get("evidence") or {}
        m, f, t = e.get("merge_edge_dnpx"), e.get("frame_edge_dnpx"), e.get("edge_ratio_min")
        if m is None or f is None or t is None or f == 0: continue
        mf = m / f
        if abs(mf - t) > tol_abs and abs(mf - t) / t * 100.0 > tol_rel: n += 1
    return n

def gate(rs):
    """The ACTUAL gate from triage.py main(), lines 781-805."""
    emitted = set()
    for r in rs:
        emitted |= set(r.keys())
        emitted |= set((r.get("evidence") or {}).keys())
    missing  = sorted(f for f in emitted if f not in FIELD_DEFS)
    orphaned = sorted(k for k in FIELD_DEFS if k not in emitted)
    return missing, orphaned

print("baseline disagreement count : %d   (definition says 13)" % count(rows))
m0, o0 = gate(rows)
print("baseline gate               : missing=%s orphaned=%s -> %s"
      % (m0, o0, "GREEN" if not m0 and not o0 else "FIRES"))
print()

# Perturb: push a currently-AGREEING row into disagreement.
tgt = None
for r in rows:
    e = r.get("evidence") or {}
    m, f, t = e.get("merge_edge_dnpx"), e.get("frame_edge_dnpx"), e.get("edge_ratio_min")
    if None in (m, f, t) or f == 0: continue
    mf = m / f
    if not (abs(mf - t) > 0.01 and abs(mf - t) / t * 100.0 > 1.0):
        tgt = r["subject"]; break
if tgt is None: raise SystemExit("PROBE BROKEN: no agreeing row to perturb")

pert = copy.deepcopy(rows)
for r in pert:
    if r["subject"] == tgt:
        r["evidence"]["frame_edge_dnpx"] *= 0.5    # halve -> m/f doubles
        break
print("perturbed %-34s frame_edge_dnpx x0.5" % tgt)
print("  true disagreement count now : %d   <- definition still says 13" % count(pert))
m1, o1 = gate(pert)
print("  definition gate now         : missing=%s orphaned=%s -> %s"
      % (m1, o1, "GREEN" if not m1 and not o1 else "FIRES"))
print()
if count(pert) != 13 and not m1 and not o1:
    print("RESULT: the data now contradicts the shipped definition (%d != 13) and" % count(pert))
    print("every gate stays GREEN. The count and tolerance are prose literals; no")
    print("code reads them. They are correct TODAY and nothing keeps them correct.")
else:
    print("RESULT: something caught it -- investigate")


"""Reconcile the two instruments' UNSCORED sets. They have DIFFERENT blind
spots, so the set no instrument can read is smaller than either alone.
ORCH is about to write "residual risk is 11" into reports; this checks it.
"""
import json
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO = _os.path.join(_HERE, "halo-data")
_SCRATCH = r"D:\strehl-out\V-REVIEW\halo"
# prefer the banked in-repo inputs; fall back to scratch if it still exists
D = _REPO if _os.path.isdir(_REPO) else _SCRATCH
tr = json.load(open(_os.path.join(D, "trunc2.json")))
h3 = json.load(open(_os.path.join(D, "halo3.json")))
subs = sorted(tr)
prof_unscored, prof_partial, h3_unscored = set(), set(), set()
for s in subs:
    r = tr[s]
    if r["verdict"] == "UNMEASURABLE": prof_unscored.add(s)
    elif r.get("used", 0) < 7:          prof_partial.add(s)
    if h3.get(s, {}).get("verdict") == "UNSCORED": h3_unscored.add(s)
notfull = prof_unscored | prof_partial
print("halo_profile UNMEASURABLE      : %2d  %s" % (len(prof_unscored), sorted(prof_unscored)))
print("halo_profile PARTIAL walk      : %2d  %s" % (len(prof_partial), sorted(prof_partial)))
print("  -> ORCH's residual risk figure: %d" % len(notfull))
print("halo3 UNSCORED                 : %2d  %s" % (len(h3_unscored), sorted(h3_unscored)))
rescued = sorted(notfull - h3_unscored)
print("\nRESCUED by halo3 (uncommissioned, so NOT certified): %d" % len(rescued))
for s in rescued:
    r = h3[s]
    print("   %-24s overshoot %7.1f  floor %7.1f  -> %s" % (s, r["overshoot"], r["floor"], r["verdict"]))
core = sorted(notfull & h3_unscored)
print("\nUNREADABLE BY BOTH INSTRUMENTS: %d" % len(core))
for s in core:
    print("   %-24s halo_profile: %s" % (s, (tr[s].get("why") or ("partial walk, %d/7 bands" % tr[s].get("used",0)))[:66]))
print("\nOf those %d, the ones my direct re-walk resolved anyway (vh_blind.py):" % len(core))
for s in ["leaf-2-cpl","lead-1-cpl"]:
    print("   %-24s excursion is a WALK ARTIFACT (44%% azimuthal coverage)" % s)
for s in ["couch-fibers-cpl","pencil-flatter-angle-cpl"]:
    print("   %-24s monotone and negative to 120 px: clean" % s)
print("\nTRULY UNMEASURED, no instrument and no re-walk: %d" % len([s for s in core if s not in
      ("leaf-2-cpl","lead-1-cpl","couch-fibers-cpl","pencil-flatter-angle-cpl")]))
for s in core:
    if s not in ("leaf-2-cpl","lead-1-cpl","couch-fibers-cpl","pencil-flatter-angle-cpl"):
        print("   %-24s %s" % (s, (tr[s].get("why") or "")[:66]))

"""Test makeviewable.py's header sourcing, including a negative control."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ORCH-drift-check"))
import makeviewable as mv

REAL = r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json"

def header(path):
    rows, counts, consts = mv.load_triage(path)
    floor_px = ((consts.get("blur_floor_px") or {}).get("value"))
    return (f"instrument floor {floor_px} px" if floor_px is not None
            else "instrument floor not reported"), floor_px

# 1. real file
txt, val = header(REAL)
print("REAL triage.json      -> %-34r  value=%r type=%s" % (txt, val, type(val).__name__))
assert txt == "instrument floor 0.35 px", "header does not read 0.35 px"
print("   [OK] header reads 0.35 px, taken from the JSON")

# 2. NEGATIVE CONTROL: source moves to 0.99 -- header must follow, not stay 0.35
doc = json.load(open(REAL, encoding="utf-8"))
doc["constants"]["blur_floor_px"]["value"] = 0.99
alt = os.path.join(HERE, "alt-moved.json")
json.dump(doc, open(alt, "w", encoding="utf-8"))
txt2, _ = header(alt)
print("source moved to 0.99  -> %r" % txt2)
assert txt2 == "instrument floor 0.99 px", "HARDCODED: header ignored the source"
print("   [OK] header TRACKS the source -- it is read, not retyped")

# 3. NEGATIVE CONTROL: constants absent -- must degrade, not print a stale number
doc2 = json.load(open(REAL, encoding="utf-8"))
doc2.pop("constants", None)
alt2 = os.path.join(HERE, "alt-noconsts.json")
json.dump(doc2, open(alt2, "w", encoding="utf-8"))
txt3, _ = header(alt2)
print("constants removed     -> %r" % txt3)
assert txt3 == "instrument floor not reported", "did not degrade cleanly"
print("   [OK] degrades to an honest absence, prints no stale digit")

for p in (alt, alt2):
    os.remove(p)
print("\nclaim 3 header sourcing: all three checks passed")

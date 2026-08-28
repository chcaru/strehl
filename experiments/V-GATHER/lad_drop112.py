"""Drop 112MSDCF from ladder.json so its failed e1 arm can be re-rendered.

The whole subject is re-run rather than the single arm, deliberately: the five
arms that DID succeed are then rendered and measured a second time by the same
pipeline, so the re-run is also an independent replication of every number the
subject contributed. The first-run values are printed here and compared after.
"""
import io
import json
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ladder.json")
doc = json.load(io.open(P, encoding="utf-8"))
sub = "112MSDCF"
if sub not in doc:
    raise SystemExit("%s not present -- nothing to drop" % sub)
prev = {k: v.get("median") for k, v in doc[sub]["arms"].items()}
json.dump({sub: prev}, io.open(os.path.join(os.path.dirname(P),
                                            "ladder-112-firstrun.json"), "w",
                               encoding="utf-8"), indent=1)
print("first-run medians preserved for comparison:")
for k, v in prev.items():
    print("  %-8s %s" % (k, ("%+.6f%%" % (100 * v)) if v is not None else "REFUSED"))
del doc[sub]
json.dump(doc, io.open(P, "w", encoding="utf-8"), indent=1)
print("dropped %s from ladder.json" % sub)

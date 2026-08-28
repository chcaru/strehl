import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
b = json.load(open(os.path.join(HERE, "vr_baseline.json")))
print("top-level keys:", list(b.keys()))
print("arm:", b.get("arm"))
print("gate_rule:", json.dumps(b.get("gate_rule"), indent=2))
subs = b["subjects"]
print("n subjects:", len(subs), sorted(subs))
k = "foam"
print("\nexample subject %r:" % k)
print(json.dumps(subs[k], indent=2)[:1200])

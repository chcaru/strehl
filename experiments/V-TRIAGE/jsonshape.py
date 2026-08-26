import json
d = json.load(open(r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json", encoding="utf-8"))
print("top-level keys:", sorted(d.keys()))
print("has 'fields'   :", "fields" in d, "->", len(d.get("fields", {})), "definitions")
print("has 'constants':", "constants" in d, "->", sorted(d.get("constants", {}).keys()))
print("rows:", len(d["rows"]))
r = d["rows"][0]
print("\nrow keys      :", sorted(r.keys()))
print("evidence keys :", sorted((r.get("evidence") or {}).keys()))
emitted = set()
for r in d["rows"]:
    emitted |= set(r.keys()); emitted |= set((r.get("evidence") or {}).keys())
print("\nunion of emitted fields:", len(emitted))
print("defined                :", len(d["fields"]))
print("undefined (emitted-defined):", sorted(emitted - set(d["fields"])))
print("orphaned  (defined-emitted):", sorted(set(d["fields"]) - emitted))
print("\nblur_floor_px constant  :", d["constants"]["blur_floor_px"])

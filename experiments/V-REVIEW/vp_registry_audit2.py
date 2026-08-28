"""Confirm the 9 code-only switches are absent from the ENTIRE sidecar (not just
the registry block), across ALL 26 delivered masters, and determine whether each
is read on a runtime path or only under cfg(test)."""
import re, pathlib, glob, os

NINE = ["STREHL_DEFECT", "STREHL_DEFECT_ARM", "STREHL_DEFECT_HOT_FLOOR",
        "STREHL_DEFECT_MAP", "STREHL_FULLRES_GATHER", "STREHL_GATE_FLOOR",
        "STREHL_GATE_FLOOR_SCALE", "STREHL_HULL", "STREHL_PYRAMID_WEIGHT_DUMP"]
CRATES = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl\crates")

sidecars = sorted(glob.glob(r"C:\dev\strehl-out\acceptance\SHIP-V3\*.provenance.txt"))
print(f"sidecars examined: {len(sidecars)}")
present_anywhere = {n: 0 for n in NINE}
for s in sidecars:
    t = open(s, encoding="utf-8-sig").read()
    for n in NINE:
        if n in t:
            present_anywhere[n] += 1
print("\n--- appears ANYWHERE in sidecar (count of 26 masters) ---")
for n in NINE:
    print(f"  {n:30s} {present_anywhere[n]:2d}/26")

print("\n--- read on a runtime path? (env::var call sites, excluding tests/) ---")
for n in NINE:
    sites = []
    for f in CRATES.rglob("*.rs"):
        rel = str(f.relative_to(CRATES))
        body = f.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(body.splitlines(), 1):
            if n in line and "env::var" in line:
                kind = "TEST" if ("tests\\" in rel or "/tests/" in rel) else "RUNTIME"
                sites.append(f"{kind} {rel}:{i}")
    # also const-declaration sites feeding a var() elsewhere
    print(f"  {n:30s} {sites if sites else '(read via named const; see decl)'}")

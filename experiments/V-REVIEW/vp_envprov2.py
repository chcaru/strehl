"""RE-ASK: does the .provenance.txt SIDECAR record env-var merge switches?

My first pass checked the TIFF ImageDescription (619 chars, colorimetry only)
and concluded provenance was blind. That was the wrong artifact: each master
carries a ~14.8 KB `<name>.provenance.txt` sidecar. This re-asks against it.
"""
import os, re

ENVS = ["STREHL_HULL", "STREHL_GATE_FLOOR_SCALE", "STREHL_PYRAMID_WEIGHT_DUMP",
        "STREHL_MEAN_COARSE"]
f = r"C:\dev\strehl-out\acceptance\SHIP-V3\109MSDCF--SHIP-V3.tiff.provenance.txt"
txt = open(f, encoding="utf-8-sig").read()
print(f"{os.path.basename(f)}: {len(txt)} chars, {txt.count(chr(10))+1} lines\n")

for e in ENVS:
    print(f"  contains {e}: {e in txt}")
print(f"  contains 'STREHL_' at all: {'STREHL_' in txt}")
print(f"  occurrences of 'env': {len(re.findall(r'(?i)\benv', txt))}")
print(f"  occurrences of 'hull': {len(re.findall(r'(?i)hull', txt))}")

print("\n--- lines mentioning env / hull / environment ---")
for i, line in enumerate(txt.splitlines(), 1):
    if re.search(r"(?i)\benv|hull|environ", line):
        print(f"  {i:4d}: {line.strip()[:160]}")

print("\n--- first 40 lines (shape of the record) ---")
for i, line in enumerate(txt.splitlines()[:40], 1):
    print(f"  {i:4d}: {line[:150]}")

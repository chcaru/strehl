"""REGISTRY COMPLETENESS AUDIT.

The provenance sidecar prints "RESOLVED SWITCH STATE (N registry switches; M set)"
and justifies listing unset switches: "an omitted line is indistinguishable from a
switch nobody considered." That is a COMPLETENESS CLAIM. It is true only if the
registry enumerates every env var the code actually reads.

merge_cmd.rs:2521 records that a registry/code disagreement has already cost this
project a real defect (+1415 DN of hidden background artifact), so this is not a
hypothetical failure mode.

Method: set-difference between
  A = switch names printed in a delivered master's provenance sidecar
  B = every "STREHL_*" string literal appearing in crates/
Partitioned output; counts sum.
"""
import re, pathlib, sys

PROV = pathlib.Path(r"C:\dev\strehl-out\acceptance\SHIP-V3"
                    r"\109MSDCF--SHIP-V3.tiff.provenance.txt")
CRATES = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl\crates")

txt = PROV.read_text(encoding="utf-8-sig")
m = re.search(r"RESOLVED SWITCH STATE \((\d+) registry switches; (\d+) set\)", txt)
claimed_n, claimed_set = int(m.group(1)), int(m.group(2))

# names printed in the registry block: "  STREHL_FOO   = (unset) [..]"
registry = set(re.findall(r"^\s{2}(STREHL_[A-Z0-9_]+)\s*=", txt, re.M))
print(f"provenance header claims : {claimed_n} registry switches, {claimed_set} set")
print(f"names actually printed   : {len(registry)}")
print(f"header matches printed   : {claimed_n == len(registry)}")

# every STREHL_* literal in the code, with where it is declared
incode = {}
for f in CRATES.rglob("*.rs"):
    body = f.read_text(encoding="utf-8", errors="replace")
    for name in re.findall(r'"(STREHL_[A-Z0-9_]+)"', body):
        incode.setdefault(name, set()).add(str(f.relative_to(CRATES)))

# build-time / not runtime switches
BUILD_ONLY = {"STREHL_BUILD_ID"}

print(f"\nSTREHL_* literals in crates/: {len(incode)}")
missing = sorted(set(incode) - registry)
extra   = sorted(registry - set(incode))
both    = sorted(registry & set(incode))

print(f"\n--- PARTITION ---")
print(f"  in BOTH registry and code      : {len(both)}")
print(f"  in CODE but NOT in registry    : {len(missing)}   <-- invisible to provenance")
print(f"  in REGISTRY but not as literal : {len(extra)}")
print(f"  sum vs union                   : "
      f"{len(both)+len(missing)+len(extra)} == {len(registry | set(incode))}")

if missing:
    print("\n--- CODE-ONLY (a render using these records nothing) ---")
    for n in missing:
        tag = "  [build-time only]" if n in BUILD_ONLY else ""
        print(f"  {n:32s} {sorted(incode[n])}{tag}")
if extra:
    print("\n--- REGISTRY-ONLY (declared but no literal; read via const?) ---")
    for n in extra:
        print(f"  {n}")

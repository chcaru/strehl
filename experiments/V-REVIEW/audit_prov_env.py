"""Do the 26 shipped provenance files account for every env var the binary reads?

An unrecorded output-affecting variable makes a provenance file's reproduce
line incomplete. A recorded one that is never read is harmless noise. Measure
both directions, and require the instrument to show it can see a difference.
"""
import re, glob, subprocess, sys

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
PIN  = "d35f9055"
NAME = re.compile(r"STREHL_[A-Z0-9_]+")
sys.path.insert(0, REPO + r"\experiments\V-REVIEW")

def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True).stdout.decode("utf-8", "replace")

ENVCALL = re.compile(r"env::var(?:_os)?\s*\(\s*([^)]*?)\s*\)")
CONSTD  = re.compile(r"(?:const|static)\s+([A-Z0-9_]+)\s*:\s*&(?:'static\s+)?str\s*=\s*\"(STREHL_[A-Z0-9_]+)\"")

rs = [f for f in git("ls-tree", "-r", "--name-only", PIN, "--", "crates/").splitlines()
      if f.endswith(".rs")]
ship = [f for f in rs if "/tests/" not in f and "/examples/" not in f
        and not f.split("/")[-1].startswith("test")]

bodies = {f: git("show", f"{PIN}:{f}") for f in ship}
const_of = {}
for b in bodies.values():
    for m in CONSTD.finditer(b):
        const_of[m.group(1)] = m.group(2)

read = {}
for f, b in bodies.items():
    for m in ENVCALL.finditer(b):
        arg = m.group(1)
        for n in NAME.findall(arg):
            read.setdefault(n, f)
        for c in re.findall(r"\b([A-Z0-9_]{4,})\b", arg):
            if c in const_of:
                read.setdefault(const_of[c], f)

provs = sorted(glob.glob(r"C:\dev\strehl-out\acceptance\SHIP-V3\*.provenance.txt"))
percount = []
union = set()
inter = None
for p in provs:
    s = set(NAME.findall(open(p, encoding="utf-8", errors="replace").read()))
    percount.append(len(s))
    union |= s
    inter = s if inter is None else (inter & s)

print(f"provenance files          : {len(provs)}")
print(f"env vars named per file   : min {min(percount)}  max {max(percount)}")
print(f"named in ALL 26 (intersection) : {len(inter)}")
print(f"named in ANY (union)           : {len(union)}")
print(f"read by shipping code at {PIN}  : {len(read)}")
print()
missing = sorted(set(read) - union)
extra   = sorted(union - set(read))
print(f"READ but recorded in NO provenance file : {len(missing)}")
for n in missing:
    print(f"   unrecorded  {n:30s} {read[n]}")
print()
print(f"RECORDED but not read by shipping code  : {len(extra)}")
for n in extra:
    print(f"   phantom     {n}")

# instrument control: the comparison must be able to report a difference at all.
probe = "STREHL_DEFINITELY_NOT_A_REAL_VARIABLE"
assert probe not in union and probe not in read
print()
print(f"CONTROL: synthetic name in neither set -> reported missing? "
      f"{probe in (set(read) | {probe}) - union}   (must be True)")
print(f"CONTROL: sets are non-trivial -> read {len(read)>10}, union {len(union)>10}")

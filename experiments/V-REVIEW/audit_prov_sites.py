"""For each unrecorded env var, list EVERY file that reads it.

The earlier pass used setdefault and therefore reported one site per variable,
which hides a variable read on both a live and a dead path.
"""
import re, subprocess
REPO = r"C:\dev\blog\death-of-software\projects\strehl"
PIN = "d35f9055"
NAME = re.compile(r"STREHL_[A-Z0-9_]+")
ENVCALL = re.compile(r"env::var(?:_os)?\s*\(\s*([^)]*?)\s*\)")
CONSTD = re.compile(r"(?:const|static)\s+([A-Z0-9_]+)\s*:\s*&(?:'static\s+)?str\s*=\s*\"(STREHL_[A-Z0-9_]+)\"")

def git(*a):
    return subprocess.run(["git","-C",REPO,*a],capture_output=True).stdout.decode("utf-8","replace")

rs=[f for f in git("ls-tree","-r","--name-only",PIN,"--","crates/").splitlines() if f.endswith(".rs")]
bodies={f:git("show",f"{PIN}:{f}") for f in rs}
const_of={}
for b in bodies.values():
    for m in CONSTD.finditer(b): const_of[m.group(1)]=m.group(2)

sites={}
for f,b in bodies.items():
    for m in ENVCALL.finditer(b):
        arg=m.group(1)
        for n in NAME.findall(arg): sites.setdefault(n,set()).add(f)
        for c in re.findall(r"\b([A-Z0-9_]{4,})\b",arg):
            if c in const_of: sites.setdefault(const_of[c],set()).add(f)

TARGET=["STREHL_DEFECT","STREHL_DEFECT_ARM","STREHL_DEFECT_HOT_FLOOR","STREHL_DEFECT_MAP",
        "STREHL_FULLRES_GATHER","STREHL_GATE_FLOOR","STREHL_GATE_FLOOR_SCALE",
        "STREHL_PYRAMID_WEIGHT_DUMP"]
for n in TARGET:
    print(f"{n}")
    for f in sorted(sites.get(n,())): print(f"      {f}")

print()
print("=== which module does Command::Stack dispatch to at HEAD? ===")
main=bodies.get("crates/strehl-cli/src/main.rs","")
for i,l in enumerate(main.splitlines(),1):
    if "Command::Stack" in l or ("Stack" in l and "run" in l):
        print(f"  main.rs:{i}: {l.strip()[:150]}")

import os, re, json
os.chdir(r"C:\dev\blog\death-of-software\projects\strehl")
cls = json.load(open(r"C:\dev\strehl-out\M117\corpus_cls.json"))
inwin = [r for r in cls if r["cls"]=="IN-WINDOW"]
rows=[]
for r in inwin:
    p = "docs/research/" + r["file"]
    t = open(p,"rb").read().decode("utf-8","replace")
    flat = re.sub(r"\s+"," ",t)
    consumed  = len(re.findall(r"ON \(sidecar\)", flat))          # actually read a cache entry
    override  = len(re.findall(r"sidecar-override", flat))
    solved    = len(re.findall(r"ON \(solved\)", flat))
    off       = len(re.findall(r"alignment\s*: OFF|STREHL_ALIGN\s*=\s*0", flat))
    invokes   = len(re.findall(r"strehl(?:\.exe)? stack\b|\$exe stack\b|exe\s+stack\b", flat))
    herm      = r["cachedir"]
    rows.append((r["file"], invokes, consumed, override, solved, off, herm, r["warpmap"]))

print(f"{'report':40s} {'stackInv':>8s} {'ON(sidecar)':>11s} {'override':>8s} {'ON(solved)':>10s} {'ALIGN=0':>7s} {'CACHEDIR':>8s} {'WARPMAP':>7s}")
cA=cB=cC=0
for f,i,c,o,s,off,h,w in sorted(rows):
    print(f"{f[:40]:40s} {i:8d} {c:11d} {o:8d} {s:10d} {off:7d} {h:8d} {w:7d}")
print()
never = [x for x in rows if x[1]==0]
consumed = [x for x in rows if x[2]>0]
print(f"in-window reports that never invoke `strehl stack` at all : {len(never)}")
for x in never: print("   ", x[0])
print(f"in-window reports that record ON (sidecar) -- a real cache CONSUMPTION: {len(consumed)}")
for x in consumed: print("   ", x[0])

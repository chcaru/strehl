import subprocess, pathlib, numpy as np, tifffile, itertools
BIN = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SUB = r"D:\personal\macro\109MSDCF"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\exp3")

def run(tag, extra):
    o = OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r = subprocess.run([BIN,"stack",SUB,"--out",str(o),"--srgb"]+extra, capture_output=True)
    if r.returncode!=0 or not o.exists():
        print("  RENDER FAILED %s rc=%d" % (tag, r.returncode)); return None
    return o

print("=== DETERMINISM ARM: same flags twice. If this differs, every null above is unreadable. ===")
d1 = run("det1", ["--exposure=3"]); d2 = run("det2", ["--exposure=3"])
D1 = tifffile.imread(str(d1)); D2 = tifffile.imread(str(d2))
det = np.array_equal(D1,D2)
print("  --exposure=3 run twice, identical pixels: %s" % det)
if not det:
    n=int(np.count_nonzero(D1.astype(np.int64)-D2.astype(np.int64)))
    print("  RENDERER IS NONDETERMINISTIC: %d samples (%.2f%%) differ between identical runs" % (n,100.0*n/D1.size))

print("\n=== SWEEP: which exposure values produce distinct images? ===")
vals = ["-6","-3","-1","0","1","2","2.60","3","6"]
arr={}
for v in vals:
    o = run("sw"+v.replace(".","p").replace("-","m"), ["--exposure=%s" % v])
    if o is None: continue
    a = tifffile.imread(str(o)); arr[v]=a
    print("  --exposure=%-5s mean DN %12.4f   max %5d   clipped-at-65535 %.3f%%" % (
        v, a.mean(), int(a.max()), 100.0*np.count_nonzero(a==65535)/a.size))

print("\n=== pairwise identity matrix (T = bit-identical pixels) ===")
ks=[v for v in vals if v in arr]
print("        " + "".join("%7s" % k for k in ks))
for i in ks:
    row=""
    for j in ks:
        row += "%7s" % ("T" if np.array_equal(arr[i],arr[j]) else "-")
    print("  %5s %s" % (i,row))

print("\n=== distinct output groups ===")
groups=[]
for v in ks:
    placed=False
    for g in groups:
        if np.array_equal(arr[v],arr[g[0]]): g.append(v); placed=True; break
    if not placed: groups.append([v])
for n,g in enumerate(groups,1):
    print("  group %d: %s" % (n, ", ".join(g)))
print("  => %d distinct images from %d exposure settings" % (len(groups), len(ks)))

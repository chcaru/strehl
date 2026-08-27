import subprocess, hashlib, pathlib, sys, numpy as np, tifffile, time
BIN = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SUB = r"D:\personal\macro\109MSDCF"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\exp3"); OUT.mkdir(parents=True, exist_ok=True)

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest().upper()

def run(tag, extra):
    o = OUT / (tag + ".tiff")
    if o.exists(): o.unlink()
    cmd = [BIN, "stack", SUB, "--out", str(o), "--srgb"] + extra
    t=time.time()
    r = subprocess.run(cmd, capture_output=True)
    log = (r.stdout+r.stderr).decode("utf8","replace")
    exp = [l.strip() for l in log.splitlines() if "exposure" in l.lower()]
    print("  [%s] rc=%d  %.1fs  %s" % (tag, r.returncode, time.time()-t, o.name))
    for l in exp: print("      LOG: " + l[:110])
    if r.returncode != 0:
        print("      FAIL: " + log[-500:]); return None
    print("      sha: " + sha(o)[:16])
    return o

print("REPRODUCING ORCH's TEST: 109MSDCF, 22 frames, --srgb, +3 vs -3 stops, pin 9b05d0b7")
a = run("plus3",  ["--exposure=3"])
b = run("minus3", ["--exposure=-3"])
if a is None or b is None: sys.exit(1)

print("\n=== FILE-HASH GAUGE (ORCH's) ===")
sa, sb = sha(a), sha(b)
print("  +3 sha : " + sa[:16])
print("  -3 sha : " + sb[:16])
print("  hashes differ: %s   <-- this is what ORCH measured" % (sa != sb))

print("\n=== PIXEL GAUGE (decoded arrays, tifffile) ===")
A = tifffile.imread(str(a)); B = tifffile.imread(str(b))
print("  shapes: %s %s   dtype %s %s" % (A.shape, B.shape, A.dtype, B.dtype))
eq = np.array_equal(A, B)
print("  np.array_equal(A,B) : %s" % eq)
print("  samples             : %d" % A.size)
d = (A.astype(np.int64) - B.astype(np.int64))
nz = int(np.count_nonzero(d))
print("  samples differing   : %d  (%.4f%%)" % (nz, 100.0*nz/A.size))
print("  mean DN  +3 / -3    : %.4f / %.4f" % (A.mean(), B.mean()))
print("  commanded gain ratio: 8.000 / 0.125 = 64.000x")
print("  observed  mean ratio: %.7f" % (A.mean()/B.mean()))
if nz: print("  max |delta|         : %d" % int(np.abs(d).max()))

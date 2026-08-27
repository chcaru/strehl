import subprocess, hashlib, pathlib, re, sys, numpy as np, tifffile
BIN = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SUB = r"D:\personal\macro\109MSDCF"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\exp3")

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest().upper()

def run(tag, extra):
    o = OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r = subprocess.run([BIN,"stack",SUB,"--out",str(o),"--srgb"]+extra, capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    line=[l.strip() for l in log.splitlines() if "exposure" in l.lower()]
    if r.returncode!=0 or not o.exists():
        print("      RENDER FAILED rc=%d  %s" % (r.returncode, log.strip().splitlines()[-1][:160] if log.strip() else ""))
        return None, (line[0] if line else "")
    return o, (line[0] if line else "")

A = tifffile.imread(str(OUT/"plus3.tiff"))

print("=== CONTROL: can the pixel gauge see a difference on THESE files at all? ===")
c,_ = run("ctl", ["--exposure=3","--pyramid-exponent","4.0"])
if c is None:
    print("  CONTROL COULD NOT RUN - refusing to report the null"); sys.exit(1)
C = tifffile.imread(str(c))
nz=int(np.count_nonzero(A.astype(np.int64)-C.astype(np.int64)))
print("  plus3 vs plus3+pyramid-exponent=4.0 (proven-potent flag)")
print("  np.array_equal      : %s   <-- MUST be False or the gauge is blind" % np.array_equal(A,C))
print("  samples differing   : %d (%.2f%%)" % (nz, 100.0*nz/A.size))
if np.array_equal(A,C):
    print("  GAUGE IS BLIND - null is unreadable"); sys.exit(1)
print("  => gauge is potent on these exact files.")

print("\n=== MECHANISM: what differs between the +3 and -3 files, if not pixels? ===")
tags={}
for tag in ("plus3","minus3"):
    with tifffile.TiffFile(str(OUT/(tag+".tiff"))) as tf:
        d={}
        for pg in tf.pages:
            for t in pg.tags.values():
                v=t.value
                if isinstance(v,bytes): v=v.decode("utf8","replace")
                d[t.name]=str(v)
        tags[tag]=d
ka,kb=tags["plus3"],tags["minus3"]
diffs=sorted([k for k in set(ka)|set(kb) if ka.get(k)!=kb.get(k)])
print("  differing TIFF tags : %s" % (diffs if diffs else "NONE"))
for k in diffs:
    for la,lb in zip(ka.get(k,"").split("\n"), kb.get(k,"").split("\n")):
        if la!=lb:
            print("    +3 | "+la.strip()[:94]); print("    -3 | "+lb.strip()[:94])

print("\n=== ORCH ITEM 3: does the --auto-exposure reproduce line reproduce? ===")
a,line = run("auto", ["--auto-exposure"])
if a is None: sys.exit(1)
print("  auto     log : " + line[:112])
m=re.search(r"([+-]?\d+\.\d+)\s*stops", line); stops=m.group(1) if m else None
print("  provenance tells the user to hand back: --exposure=%s" % stops)
b,line2 = run("explicit", ["--exposure=%s" % stops])
if b is None: sys.exit(1)
print("  explicit log : " + line2[:112])
sa,sb=sha(a),sha(b)
print("  auto sha %s   explicit sha %s" % (sa[:16], sb[:16]))
print("  CONTRACT image_out.rs:617 'get the SAME file' -> %s" % ("HOLDS" if sa==sb else "VIOLATED (bytes differ)"))
X=tifffile.imread(str(a)); Y=tifffile.imread(str(b))
print("  same pixels auto vs explicit : %s" % np.array_equal(X,Y))
print("  same pixels auto vs +3 stops : %s  <- every exposure yields one image" % np.array_equal(X,A))

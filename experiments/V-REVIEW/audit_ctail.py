import subprocess, pathlib, numpy as np, tifffile, os
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\sweep")
def run(tag,extra):
    o=OUT/(tag+".tiff"); m=OUT/(tag+"_map.tiff")
    for p in (o,m):
        if p.exists(): p.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb",
                      "--merge","pyramid","--confidence-map",str(m)]+extra,capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    if o.exists():
        try: os.remove(o)
        except Exception: pass
    return (m if (r.returncode==0 and m.exists()) else None), log

m,log=run("c_base",[])
print("=== baseline confidence map: %s ===" % ("written" if m else "FAILED"))
if m is None:
    print(log[-400:]); raise SystemExit(1)
base=tifffile.imread(str(m)); print("  shape %s dtype %s" % (base.shape,base.dtype))

print("\n=== POTENCY CONTROL: does the map respond to a flag that should move it? ===")
ok=False
for ctl,args in (("--pyramid-gate 8.0",["--pyramid-gate","8.0"]),("--pyramid-bands 3",["--pyramid-bands","3"])):
    m2,_=run("c_ctl",args)
    if m2 is None: print("  %-20s FAILED" % ctl); continue
    B=tifffile.imread(str(m2)); n=int(np.count_nonzero(B!=base))
    print("  %-20s moves map by %.4f%%" % (ctl,100.0*n/base.size))
    if n: ok=True
    try: os.remove(m2)
    except Exception: pass
print("  map responsive: %s" % ok)
if not ok:
    print("  MAP IS DEAD -> a null on --confidence-tail would be UNREADABLE. Stopping."); raise SystemExit(1)

print("\n=== SWEEP --confidence-tail across its range, on pyramid ===")
groups=[]
for v in ["0.02","0.10","0.25","0.35","0.50","0.90"]:
    mm,lg=run("c"+v.replace(".","p"),["--confidence-tail",v])
    if mm is None:
        print("  tail=%-5s FAILED: %s" % (v,[l for l in lg.splitlines() if l.strip()][-1][:70])); continue
    X=tifffile.imread(str(mm)); n=int(np.count_nonzero(X!=base))
    print("  tail=%-5s map samples moved vs default: %.4f%%" % (v,100.0*n/X.size))
    for g in groups:
        if np.array_equal(X,g[1]): g[0].append(v); break
    else: groups.append([[v],X])
    try: os.remove(mm)
    except Exception: pass
print("  distinct maps across the settings that ran: %d" % len(groups))
for g in groups: print("    group: %s" % ", ".join(g[0]))
try: os.remove(m)
except Exception: pass

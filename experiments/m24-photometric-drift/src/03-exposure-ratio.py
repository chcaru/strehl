import numpy as np, rawpy, glob, os, exifread
BLACK=512
print("=== R9 probe 3: does the measured level jump MATCH the EXIF exposure ratio? ===")
print("    coffee-bean changes exposure mid-stack. If the level ratio between the two")
print("    exposure groups equals the exposure ratio, the drift is quantitatively explained")
print("    and per-frame gain normalisation is exactly the right correction.\n")
fs=sorted(glob.glob(os.path.join(r"C:\dev\macro\test\coffee-bean","*.ARW")))
grp=[];lev=[]
for f in fs[::2]:
    with open(f,'rb') as fh: t=exifread.process_file(fh,details=False)
    e=str(t.get('EXIF ExposureTime'))
    with rawpy.imread(f) as rr:
        g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
    grp.append(e); lev.append(g.mean())
grp=np.array(grp); lev=np.array(lev)
us=sorted(set(grp.tolist()))
print(f"  frames sampled: {len(fs[::2])} of {len(fs)}")
idx=np.arange(len(grp))
for u in us:
    m=grp==u
    n=int(m.sum()); a,b=idx[m].min(),idx[m].max()
    print(f"    exposure {u:>5}: {n:>3} frames, sampled indices {a}-{b}, mean level {lev[m].mean():8.1f} DN")
def val(s):
    a,b=s.split('/'); return float(a)/float(b)
if len(us)==2:
    e0,e1=val(us[0]),val(us[1])
    l0,l1=lev[grp==us[0]].mean(), lev[grp==us[1]].mean()
    print(f"\n    EXIF exposure ratio  {us[0]} / {us[1]} = {e0/e1:.4f}   ({abs(np.log2(e0/e1)):.3f} EV)")
    print(f"    MEASURED level ratio                   = {l0/l1:.4f}")
    print(f"    agreement: {100*(l0/l1)/(e0/e1):.1f}% of the predicted ratio")
    print(f"\n    NOTE the confound: the two exposure groups are also different FOCUS ranges")
    print(f"    (indices {idx[grp==us[0]].min()}-{idx[grp==us[0]].max()} vs {idx[grp==us[1]].min()}-{idx[grp==us[1]].max()}),")
    print(f"    so scene content differs between them. This is a consistency check, not a")
    print(f"    clean isolation -- but a large mismatch would have falsified the explanation.")

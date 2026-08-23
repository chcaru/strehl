import numpy as np, rawpy, glob, os, exifread
BLACK=512
print("=== R9 probe: does this corpus have per-frame photometric drift? ===")
print("    The review says the merge's forward model needs per-frame gain+offset, or the")
print("    Wiener gate misreads exposure drift as signal. First question: is there any drift?")
print("    Focus change redistributes light but conserves it, so a trend in level is drift.\n")
def probe(name,path,sub=1,nmax=40):
    fs=sorted(glob.glob(os.path.join(path,"*.ARW")))[::sub][:nmax]
    with open(fs[0],'rb') as fh: t=exifread.process_file(fh,details=False)
    lv=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        lv.append(np.mean(g))
    lv=np.array(lv); rel=lv/lv.mean()
    x=np.arange(len(lv))
    sl=np.polyfit(x,rel,1)[0]
    # frame-to-frame jitter, robust to the slow trend
    jit=np.std(np.diff(rel))
    print(f"  {name:>14} n={len(fs):>3}  ISO {str(t.get('EXIF ISOSpeedRatings')):>5} exp {str(t.get('EXIF ExposureTime')):>7}")
    print(f"      mean level {lv.mean():8.1f} DN   range {rel.min():.4f}-{rel.max():.4f} "
          f"(= {(rel.max()-rel.min())*100:5.2f}% peak-to-peak)")
    print(f"      linear trend {sl*len(lv)*100:+6.2f}% over the stack   frame-to-frame jitter {jit*100:5.3f}%")
    # is the p-p spread bigger than shot-noise on the mean? sigma_mean is tiny, so any spread is real
    return rel
for n,p,s2 in (("109MSDCF",r"C:\dev\macro\test\109MSDCF",1),
               ("119MSDCF",r"C:\dev\macro\test\119MSDCF",1),
               ("coffee-bean",r"C:\dev\macro\test\coffee-bean",3),
               ("112MSDCF",r"D:\personal\macro\112MSDCF",2),
               ("coffee-bubbles",r"D:\personal\macro\coffee-bubbles",1)):
    try: probe(n,p,s2)
    except Exception as e: print(f"  {n}: FAILED {e}")
    print()

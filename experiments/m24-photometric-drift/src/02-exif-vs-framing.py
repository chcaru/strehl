import numpy as np, rawpy, glob, os, exifread
BLACK=512
print("=== R9 probe 2: is the drift EXPOSURE, or is it focus breathing changing the framing? ===")
print("    Confound (rule 17): breathing changes magnification, so the frame samples different")
print("    scene content, moving the mean WITHOUT any exposure change.")
print("    Decisive test A: does EXIF exposure/ISO/aperture actually vary frame to frame?")
print("    Decisive test B: a true global gain moves a small CENTRAL roi as much as the full")
print("    frame; a framing change moves the full frame much more than the centre.\n")
for name,path,sub in (("coffee-bean",r"C:\dev\macro\test\coffee-bean",3),
                      ("coffee-bubbles",r"D:\personal\macro\coffee-bubbles",1),
                      ("112MSDCF",r"D:\personal\macro\112MSDCF",2)):
    fs=sorted(glob.glob(os.path.join(path,"*.ARW")))[::sub][:40]
    tags=[]
    for f in fs:
        with open(f,'rb') as fh: t=exifread.process_file(fh,details=False)
        tags.append((str(t.get('EXIF ExposureTime')),str(t.get('EXIF ISOSpeedRatings')),
                     str(t.get('EXIF FNumber')),str(t.get('EXIF BrightnessValue'))))
    uniq=sorted(set(tags))
    print(f"  --- {name} ({len(fs)} frames) ---")
    print(f"    TEST A: distinct (exposure, ISO, FNumber) combinations across the stack: {len(set(t[:3] for t in tags))}")
    for u in sorted(set(t[:3] for t in tags)): print(f"       {u}")
    full=[];cen=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        full.append(g.mean())
        h,w=g.shape; cen.append(g[h//2-300:h//2+300, w//2-300:w//2+300].mean())
    full=np.array(full)/np.mean(full); cen=np.array(cen)/np.mean(cen)
    pf=(full.max()-full.min())*100; pc=(cen.max()-cen.min())*100
    r=np.corrcoef(full,cen)[0,1]
    print(f"    TEST B: full-frame p-p {pf:5.2f}%   central-600px-roi p-p {pc:5.2f}%   ratio {pc/max(pf,1e-9):5.2f}")
    print(f"            correlation between the two level curves: {r:+.3f}")
    v = "GLOBAL GAIN (centre tracks full frame)" if (r>0.8 and pc/pf>0.6) else \
        ("FRAMING/CONTENT (centre moves much less, or uncorrelated)" if pc/pf<0.6 or r<0.4 else "mixed / inconclusive")
    print(f"            verdict: {v}\n")

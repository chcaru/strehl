import numpy as np, tifffile, warnings
from PIL import Image
warnings.simplefilter("ignore")
P = r"C:\dev\strehl-out\V-HIGHLIGHT\u-bee-3-cpl.tiff"
clean = tifffile.imread(P); pil = np.array(Image.open(P))

# locate a genuinely busy and a genuinely flat block of the SAME size
g = clean[:,:,1].astype(np.float64); B = 256
h, w = g.shape[0]//B, g.shape[1]//B
sd = np.array([[g[y*B:(y+1)*B, x*B:(x+1)*B].std() for x in range(w)] for y in range(h)])
by, bx = np.unravel_index(np.argmax(sd), sd.shape)
fy, fx = np.unravel_index(np.argmin(sd), sd.shape)
print("busy block at (%d,%d) sd=%.1f   flat block at (%d,%d) sd=%.1f" % (by*B,bx*B,sd.max(), fy*B,fx*B,sd.min()))

# ANCHOR: at full frame the rule must fire, else this whole test is void
if not (len(np.unique(clean)) > 1000 and len(np.unique(pil)) < 300):
    raise SystemExit("ANCHOR FAIL: rule does not even fire at full frame")
print("anchor ok: full frame clean=%d pil=%d -> rule fires\n" % (len(np.unique(clean)), len(np.unique(pil))))

print("ORCH's rule: 'thousands' = clean, 'a couple of hundred at most' = PIL-damaged")
print("%-6s %-6s %10s %10s   %-28s" % ("region","N","clean uq","PIL uq","verdict on the CLEAN array"))
for tag,(oy,ox) in (("busy",(by*B,bx*B)), ("flat",(fy*B,fx*B))):
    for n in (8,16,32,64,128,256,1024,4096):
        c = clean[oy:oy+n, ox:ox+n]; p = pil[oy:oy+n, ox:ox+n]
        if c.shape[0] < n: continue
        cu, pu = len(np.unique(c)), len(np.unique(p))
        v = "OK (thousands)" if cu >= 1000 else ("*** MISREAD AS PIL-DAMAGED ***" if cu <= 300 else "ambiguous 300..1000")
        print("%-6s %-6d %10d %10d   %-28s" % (tag, n, cu, pu, v))

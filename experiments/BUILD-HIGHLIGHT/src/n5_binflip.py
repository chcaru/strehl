import numpy as np, tifffile, l2_falsecolour as L
def bin2(a):
    h,w,_=a.shape; h-=h%2; w-=w%2
    return a[:h,:w].reshape(h//2,2,w//2,2,3).mean(axis=(1,3))
out={}
for nm,path in [("single","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/L1-single-demo.tif"),
                ("stack ","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/L3-stack-demo.tif")]:
    img=tifffile.imread(path).astype(np.float32)/65535.0
    out[(nm,"native")]=L.stats(img)["H_highfreq_chroma"]
    b=bin2(img); del img
    s=L.stats(b); out[(nm,"binned")]=s["H_highfreq_chroma"]
    print("  %s native H=%.4f   binned H=%.4f  (binned shape %s)"%(nm,out[(nm,"native")],out[(nm,"binned")],s["shape"]))
    del b
print()
for mode in ("native","binned"):
    a,b=out[("single",mode)],out[("stack ",mode)]
    print("  %-6s : single %.4f -> stack %.4f   %+.1f%%   %s"%(mode,a,b,100*(b/a-1),"stack WORSE" if b>a else "stack BETTER"))

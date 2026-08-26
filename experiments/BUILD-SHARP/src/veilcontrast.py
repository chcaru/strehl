import numpy as np, tifffile
R = r"C:\dev\strehl-out\BUILD-SHARP\veil"
def load(s,a): return tifffile.imread(rf"{R}\{s}\{a}\linear-srgb.tif").astype(np.float32)
print(f"{'subject':<22}{'arm':>4}{'p1':>9}{'p5':>9}{'p50':>9}{'p95':>9}{'p99':>9}{'gradRMS':>10}{'p95-p5':>9}")
res={}
for s in ("flower-bud-alone-cpl","109MSDCF","coffee-bean","couch-fibers-cpl"):
    row={}
    for a in ("A","B"):
        x = load(s,a).mean(axis=2)
        q = np.percentile(x,[1,5,50,95,99])
        gy = np.diff(x,axis=0); gx = np.diff(x,axis=1)
        g = np.sqrt((gy**2).mean()+(gx**2).mean())
        row[a]=(q,g)
        print(f"{s:<22}{a:>4}{q[0]:9.0f}{q[1]:9.0f}{q[2]:9.0f}{q[3]:9.0f}{q[4]:9.0f}{g:10.1f}{q[3]-q[1]:9.0f}")
        del x
    (qa,ga),(qb,gb)=row["A"],row["B"]
    print(f"{'':<22}{'d%':>4}"+''.join(f"{100*(qb[i]-qa[i])/qa[i]:8.2f}%" for i in range(5))
          +f"{100*(gb-ga)/ga:9.2f}%"+f"{100*((qb[3]-qb[1])-(qa[3]-qa[1]))/(qa[3]-qa[1]):8.2f}%")
    print()

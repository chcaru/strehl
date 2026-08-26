import numpy as np
rng = np.random.default_rng(7)
def decompose(sig, levels):
    bands, cur = [], sig.astype(np.float64)
    for _ in range(levels):
        lo = np.convolve(cur, np.ones(5)/5.0, mode="same"); bands.append(cur-lo); cur = lo
    bands.append(cur); return bands
def merge(frames, levels, expo):
    dec = [decompose(f, levels) for f in frames]; out=[]
    for b in range(levels+1):
        p = np.array([np.abs(d[b]).mean()**expo for d in dec])
        p = p/p.sum() if p.sum()>0 else np.ones(len(frames))/len(frames)
        out.append(sum(p[k]*dec[k][b] for k in range(len(frames))))
    return np.sum(out, axis=0)
print(f"{'exponent':>9} {'violating px':>14} {'rate':>8} {'worst excursion':>17}")
print("-"*54)
for expo in [0.0, 1, 2, 4, 8, 16]:
    v=t=0; worst=0.0
    for _ in range(150):
        n=512; base=np.cumsum(rng.normal(0,1,n)); fr=[]
        for k in range(8):
            w=np.exp(-((np.arange(n)-k*n/8)**2)/(2*(n/12)**2))
            sm=np.convolve(base,np.ones(9)/9.0,mode="same")
            fr.append(w*base+(1-w)*sm+rng.normal(0,0.05,n))
        fr=np.array(fr); out=merge(fr,5,expo)
        lo,hi=fr.min(axis=0),fr.max(axis=0); eps=1e-9
        v+=int(((out<lo-eps)|(out>hi+eps)).sum()); t+=n
        span=np.maximum(hi-lo,1e-12)
        worst=max(worst,float(np.maximum((lo-out)/span,(out-hi)/span).max()))
    tag = "  <- uniform mean (control)" if expo==0.0 else ("  <- pyramid fine bands" if expo==8 else "")
    print(f"{expo:>9} {v:>14,} {100*v/t:>7.2f}% {worst:>17.3f}{tag}")

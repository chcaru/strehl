import sys, numpy as np, tifffile, pathlib

# ---- sensor constants, read from crates/strehl-core/src/noise.rs (read-only) ----
G_MEAS   = 0.221113      # DN/e- measured green gain, ISO 100
RN_E_HI  = 1.47          # e- read noise, high-conversion-gain
BLACK    = 512.0
WHITE    = 15360.0
K_TIFF   = 65535.0/(WHITE-BLACK)   # TIFF DN per raw DN above black

def sigma_raw(S_raw, g=G_MEAS, rn_e=RN_E_HI):
    """model: var = g*S + (RN_e*g)^2, S in raw DN above black."""
    return np.sqrt(np.maximum(g*S_raw, 0.0) + (rn_e*g)**2)

def sigma_pred_tiff(S_tiff, nsamp=1.0):
    """predicted sigma in TIFF DN for a green sample that averages nsamp raw greens."""
    return sigma_raw(S_tiff/K_TIFF)*K_TIFF/np.sqrt(nsamp)

# ---- sigma_std: correlation-independent, quadratic detrended ----
def sigma_std(t):
    h,w = t.shape
    yy,xx = np.mgrid[0:h,0:w]
    y = (yy-(h-1)/2)/max(h,1); x = (xx-(w-1)/2)/max(w,1)
    B = np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],-1).reshape(-1,6).astype(np.float64)
    Q,_ = np.linalg.qr(B)
    v = t.reshape(-1).astype(np.float64)
    r = v - Q@(Q.T@v)
    dof = v.size - 6
    return float(np.sqrt(max((r*r).sum(),0.0)/dof))

def tiles(img, box, step):
    h,w = img.shape
    out=[]
    for y in range(0,h-box+1,step):
        for x in range(0,w-box+1,step):
            out.append((y,x,img[y:y+box,x:x+box]))
    return out

# ------------------- COMMISSION -------------------
def commission():
    rng = np.random.default_rng(11)
    print("="*70); print("COMMISSION"); print("="*70)
    ok=True
    # 1. model predicts synthetic shot+read noise it was given
    for S_raw in (200.0, 1000.0, 4000.0):
        e = S_raw/G_MEAS
        n = rng.poisson(e, (256,256)).astype(np.float64)*G_MEAS \
            + rng.normal(0, RN_E_HI*G_MEAS, (256,256))
        m = sigma_std(n); p = sigma_raw(S_raw)
        good = abs(m/p-1) < 0.03
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  synth shot+read S={S_raw:7.0f}  meas {m:8.4f}  model {p:8.4f}  ratio {m/p:.4f}")
    # 2. averaging n samples must give the 1/sqrt(n) prediction
    for nsamp in (2, 16):
        S_raw = 4000.0; e = S_raw/G_MEAS
        acc = np.zeros((256,256))
        for _ in range(nsamp):
            acc += rng.poisson(e,(256,256)).astype(np.float64)*G_MEAS + rng.normal(0,RN_E_HI*G_MEAS,(256,256))
        acc/=nsamp
        m = sigma_std(acc); p = sigma_raw(S_raw)/np.sqrt(nsamp)
        good = abs(m/p-1) < 0.04
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  averaged n={nsamp:3d}  meas {m:8.4f}  model {p:8.4f}  ratio {m/p:.4f}")
    # 3. NULL: model must NOT match a signal with no noise at all
    flat = np.full((256,256), 4000.0)
    m = sigma_std(flat)
    good = m < 1e-6
    ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  NULL noiseless field -> sigma {m:.3e} (must be ~0)")
    # 4. TIFF-DN round trip
    S_t = 4000.0*K_TIFF
    good = abs(sigma_pred_tiff(S_t) - sigma_raw(4000.0)*K_TIFF) < 1e-9
    ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  TIFF-DN scaling round trip  (k={K_TIFF:.4f})")
    print(f"  --> {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return ok

def load_green(p):
    a = tifffile.imread(p)
    assert a.dtype==np.uint16, a.dtype
    assert a.ndim==3 and a.shape[2]==3, a.shape
    return a[:,:,1].astype(np.float64)

if __name__ == "__main__":
    commission()
    if len(sys.argv) < 2: sys.exit(0)
    path = sys.argv[1]
    nsamp = float(sys.argv[2]) if len(sys.argv)>2 else 1.0
    label = pathlib.Path(path).name
    g = load_green(path)
    BOX, STEP = 64, 256
    ts = tiles(g, BOX, STEP)
    print()
    print("="*70)
    print(f"{label}   nsamp={nsamp}   ({g.shape[1]}x{g.shape[0]})")
    print("="*70)
    rows=[]
    for (y,x,t) in ts:
        mu = float(t.mean())
        if mu < 300 or mu > 60000: continue
        rows.append((mu, sigma_std(t), y, x))
    rows = np.array([(r[0],r[1]) for r in rows])
    print(f"  {len(rows)} tiles of {BOX}x{BOX}")
    edges = [300,1000,2000,4000,8000,16000,32000,60000]
    print(f"  {'signal bin':>16} {'ntile':>6} {'meas sigma':>11} {'model 1-frame':>14} {'meas/model':>11} {'implied n':>10}")
    for lo,hi in zip(edges[:-1],edges[1:]):
        m = (rows[:,0]>=lo)&(rows[:,0]<hi)
        if m.sum()<4: continue
        sub = rows[m]
        # flattest 25% within the bin -- rank rule, no threshold
        k = max(3, int(0.25*len(sub)))
        idx = np.argsort(sub[:,1])[:k]
        s = sub[idx]
        mu = float(s[:,0].mean()); sg = float(np.median(s[:,1]))
        pred = float(sigma_pred_tiff(mu, nsamp))
        print(f"  {lo:7d}-{hi:7d} {int(m.sum()):6d} {sg:11.3f} {pred:14.3f} {sg/pred:11.4f} {1.0/max(sg/pred,1e-9)**2:10.2f}")

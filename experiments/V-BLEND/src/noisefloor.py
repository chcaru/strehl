"""V-BLEND noise floor instrument. Independent of ORCH's flatnoise/rho code.

Two estimators, deliberately:
  sigma_std : std of the tile after removing a fitted QUADRATIC surface. Exact
              for any noise, white or spatially correlated. This is the real
              per-pixel noise magnitude.
  sigma_hf  : Immerkaer high-frequency estimator. Correct ONLY for white noise;
              it UNDER-reports correlated noise. (Commissioned: on 3x3-box
              smoothed noise of true sigma 30 it reads 6.65.)

Their ratio is the instrument that matters here:
  sigma_std / sigma_hf  ~= 1.0  -> the noise is WHITE  (e.g. quiet by AVERAGING)
                        >> 1.0  -> the noise is CORRELATED (quiet by SMOOTHING)
That distinguishes "flat because n frames were averaged" from "flat because it
was low-passed", which is the whole question in Claim 2.
"""
import sys
import numpy as np
import tifffile

BOX = 64
DS  = 8

def load_green(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype} for {path}"
    assert a.ndim == 3 and a.shape[2] == 3, f"expected HxWx3, got {a.shape}"
    return a[:, :, 1].astype(np.float32)

def tiles(img, box=BOX):
    h, w = img.shape
    ny, nx = h // box, w // box
    t = img[:ny*box, :nx*box].reshape(ny, box, nx, box).transpose(0, 2, 1, 3)
    return t.reshape(ny*nx, box, box)

def _basis(box):
    y, x = np.mgrid[0:box, 0:box].astype(np.float64)
    y = (y-(box-1)/2)/box; x = (x-(box-1)/2)/box
    B = np.stack([np.ones_like(x), x, y, x*x, x*y, y*y], 0).reshape(6, -1)
    Q, _ = np.linalg.qr(B.T)          # orthonormal columns
    return Q.astype(np.float32)

_Q = {}
def sigma_std(t):
    """std after projecting out a quadratic surface; correlation-independent."""
    box = t.shape[1]
    if box not in _Q: _Q[box] = _basis(box)
    Q = _Q[box]
    f = t.reshape(t.shape[0], -1)
    r = f - (f @ Q) @ Q.T
    dof = f.shape[1] - Q.shape[1]
    return np.sqrt((r*r).sum(axis=1)/dof)

def immerkaer(t):
    c = (t[:, :-2, :-2] + t[:, :-2, 2:] + t[:, 2:, :-2] + t[:, 2:, 2:]
         - 2*(t[:, :-2, 1:-1] + t[:, 2:, 1:-1] + t[:, 1:-1, :-2] + t[:, 1:-1, 2:])
         + 4*t[:, 1:-1, 1:-1])
    n = c.shape[1]*c.shape[2]
    return np.sqrt(np.pi/2) * np.abs(c).sum(axis=(1, 2)) / (6.0*n)

def mad_diag(t):
    d = t[:, 1:, 1:] - t[:, :-1, :-1]
    m = np.median(d, axis=(1, 2), keepdims=True)
    return np.median(np.abs(d-m), axis=(1, 2)) / (np.sqrt(2.0)*0.6745)

def structure_index(t, sig):
    n = t.shape[0]; b = t.shape[1]//DS
    d = t.reshape(n, b, DS, b, DS).mean(axis=(2, 4))
    s = sigma_std(d.astype(np.float32))
    return np.where(sig > 0, s/np.maximum(sig/float(DS), 1e-9), np.inf)

def measure(path):
    g = load_green(path)
    t = tiles(g)
    out = dict(mean=t.mean(axis=(1, 2)), std=sigma_std(t), hf=immerkaer(t),
               mad=mad_diag(t))
    out["ratio"] = out["std"]/np.maximum(out["hf"], 1e-9)
    out["si"] = structure_index(t, out["std"])
    out["n"] = t.shape[0]
    del g, t
    return out

if __name__ == "__main__":
    p = sys.argv[1]
    o = measure(p)
    flat = o["si"] < 1.5
    print(f"file          : {p}")
    print(f"tiles         : {o['n']} of {BOX}x{BOX};  structureless {int(flat.sum())} "
          f"({100.0*flat.mean():.2f}%)  rule: structure index < 1.5")
    print()
    print("  signal bin (DN)     ntile   sigma_std   sigma_hf   std/hf   struct")
    edges = np.array([0, 500, 1000, 2000, 4000, 8000, 16000, 32000, 65536])
    for i in range(len(edges)-1):
        m = flat & (o["mean"] >= edges[i]) & (o["mean"] < edges[i+1])
        if m.sum() < 4:
            print(f"  {edges[i]:6d}-{edges[i+1]:6d}  {int(m.sum()):8d}   (too few)"); continue
        print(f"  {edges[i]:6d}-{edges[i+1]:6d}  {int(m.sum()):8d}   "
              f"{np.median(o['std'][m]):9.3f}  {np.median(o['hf'][m]):9.3f}  "
              f"{np.median(o['ratio'][m]):6.3f}  {np.median(o['si'][m]):6.3f}")
    print()
    print(f"OVERALL structureless: sigma_std {np.median(o['std'][flat]):.3f}  "
          f"sigma_hf {np.median(o['hf'][flat]):.3f}  std/hf {np.median(o['ratio'][flat]):.3f}")
    if len(sys.argv) > 2:
        np.savez(sys.argv[2], **{k: v for k, v in o.items() if k != "n"})
        print(f"saved -> {sys.argv[2]}")

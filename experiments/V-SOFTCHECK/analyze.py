"""Compute every arm from the cached prepass. Nothing here reads a source image
except the master, and only for the nulls."""
import os, sys, numpy as np, softcheck as S
from scipy import ndimage

def load(subj, gauge="lin", T=128):
    return dict(np.load(os.path.join(S.ROOT, "cache", f"{subj}--{gauge}--T{T}.npz")))

def ratio(mv, bv, sel, shape, ntot, ci=True):
    ok = sel & (bv > 0) & np.isfinite(bv) & np.isfinite(mv)
    n = int(ok.sum())
    if n == 0:
        return dict(n=0, dropped=int(sel.sum()), median=float("nan"), agg=float("nan"),
                    frac_gt1=float("nan"), p10=float("nan"), p90=float("nan"), ci=None)
    r = mv[ok] / bv[ok]
    return dict(n=n, dropped=int(sel.sum() - n), median=float(np.median(r)),
                agg=float(mv[ok].sum() / bv[ok].sum()), frac_gt1=float((r > 1).mean()),
                p10=float(np.percentile(r, 10)), p90=float(np.percentile(r, 90)),
                ci=(S.block_ci(r, ok, tuple(shape), ntot) if ci else None))

def arms(c, m_plant="none", f_key="none", idx=None, sel_q=0.50, ci=True, band="mid"):
    nt = len(c["m_lo"]); shape = tuple(c["shape"]); cn = float(c["c_noise"])
    lo = c["m_lo"]; sel = lo >= np.quantile(lo, sel_q) if sel_q > 0 else np.ones(nt, bool)
    fm = c[f"f_mid_{f_key}"]; fh = c[f"f_hi_{f_key}"]
    if idx is not None: fm = fm[idx]; fh = fh[idx]
    m_mid = c[f"m_mid_{m_plant}"]; m_hi = c[f"m_hi_{m_plant}"]
    res = {}
    res["NOSUB"] = ratio(m_mid, fm.max(0), sel, shape, nt, ci)
    res["SUB"]   = ratio(m_mid - cn*m_hi, (fm - cn*fh).max(0), sel, shape, nt, ci)
    res["FINE"]  = ratio(m_hi, fh.max(0), sel, shape, nt, False)
    flat = ~sel
    res["NOSUB_flat"] = ratio(m_mid, fm.max(0), flat, shape, nt, False)
    res["SUB_flat"]   = ratio(m_mid - cn*m_hi, (fm - cn*fh).max(0), flat, shape, nt, False)
    return res

def line(tag, r, extra=""):
    def f(a):
        s = f"{a['median']:.4f}"
        return s + (f" [{a['ci'][0]:.4f},{a['ci'][1]:.4f}]" if a["ci"] else " " * 17)
    return (f"{tag:36s} NOSUB {f(r['NOSUB'])}   SUB {f(r['SUB'])}   "
            f"FINE {r['FINE']['median']:.4f}   n={r['NOSUB']['n']} dropSUB={r['SUB']['dropped']} {extra}")

def noise_null(subj, gauge, T, c, kind, seed=11, scale=1.0):
    """NULL whose true ratio is 1.000 BY CONSTRUCTION.

    kind="identical": reference members and numerator are all the master.
                      Pure plumbing check; must read exactly 1.0000.
    kind="noised":    draw N+1 i.i.d. noised copies of the master.  Copy 0 is
                      the NUMERATOR, copies 1..N are the reference.  Numerator
                      and every reference member are draws from ONE
                      distribution, so the only thing that can move the reading
                      is the order statistic over N draws.  Per-tile noise is
                      set so each copy's top-band energy matches the real
                      frames' MEDIAN top-band energy -- the copies are then at
                      least as noisy as the real bracket, making this an UPPER
                      BOUND on the real inflation.
    """
    d = os.path.join(S.ROOT, gauge, subj)
    M = S.load_luma(os.path.join(d, "master.tiff"), gauge)
    oy = c["oy"]; ox = c["ox"]; shape = tuple(c["shape"]); N = int(c["N"])
    Tt = int(c["T"]); rng = np.random.default_rng(seed); smap = None
    if kind == "noised":
        med = np.median(c["f_hi_none"], axis=0)
        sig = scale * np.sqrt(np.maximum(med, 0) / S.G_HI).reshape(shape)
        smap = ndimage.zoom(sig, (M.shape[0]/sig.shape[0], M.shape[1]/sig.shape[1]),
                            order=1).astype(np.float32)
        smap = np.pad(smap, [(0, max(0, M.shape[i]-smap.shape[i])) for i in range(2)],
                      mode="edge")[:M.shape[0], :M.shape[1]]
    fm = np.zeros((N+1, len(oy))); fh = np.zeros((N+1, len(oy)))
    for k in range(N+1):
        F = M if smap is None else M + smap*rng.standard_normal(M.shape).astype(np.float32)
        fm[k] = S.tile_means(S.dog(F, S.S_MID)**2, oy, ox, Tt)
        fh[k] = S.tile_means(S.dog(F, S.S_HI)**2,  oy, ox, Tt)
    cc = dict(c)
    cc["m_mid_null"], cc["m_hi_null"] = fm[0], fh[0]
    cc["f_mid_null"], cc["f_hi_null"] = fm[1:], fh[1:]
    return arms(cc, "null", "null"), (float(np.median(smap)) if smap is not None else 0.0)

if __name__ == "__main__":
    subj = sys.argv[1]; gauge = sys.argv[2] if len(sys.argv) > 2 else "lin"
    T = int(sys.argv[3]) if len(sys.argv) > 3 else 128
    c = load(subj, gauge, T); N = int(c["N"]); nt = len(c["m_lo"])
    print(f"=== {subj} / {gauge} / T={T} / N={N} frames / {nt} tiles / c_noise={float(c['c_noise']):.5f}")
    print(f"GAUGE  master/mean-frame tile LEVEL = {np.median(c['m_lv']/c['f_lv'].mean(0)):.5f}"
          f"   master/mean-frame TOP-BAND = {np.median(c['m_hi_none']/c['f_hi_none'].mean(0)):.4f}"
          f"   master/max-frame TOP-BAND = {np.median(c['m_hi_none']/c['f_hi_none'].max(0)):.4f}")
    print(f"REG    rms px median {np.median(c['reg_rms']):.2f} max {c['reg_rms'].max():.2f}"
          f"  n>4px: {(c['reg_rms']>4).sum()}/{N}")
    print()
    print("--- COMMISSIONING -----------------------------------------------------------------")
    base = arms(c); print(line("BASELINE (real, no plant)", base))
    for pn in ("blur040","blur070","blur100"): print(line(f"  MASTER {pn}   [must FALL]", arms(c, m_plant=pn)))
    for pn in ("sharp030","sharp060"):         print(line(f"  MASTER {pn}  [must RISE]", arms(c, m_plant=pn)))
    for pn in ("blur040","blur070"):           print(line(f"  REF    {pn}   [must RISE]", arms(c, f_key=pn)))
    print(line("  REF    sharp030  [must FALL]", arms(c, f_key="sharp030")))
    print(line("  PLACEBO gain1.70 both [NO MOVE]", arms(c, m_plant="gain170", f_key="gain170")))
    print(line("  PLACEBO frame shuffle [NO MOVE]", arms(c, idx=np.random.default_rng(3).permutation(N))))
    print()
    print("--- NULL: true ratio is 1.000 BY CONSTRUCTION -------------------------------------")
    r0, _ = noise_null(subj, gauge, T, c, "identical"); print(line("  null A: N identical masters", r0))
    for sc in (0.5, 1.0, 1.5):
        r1, sg = noise_null(subj, gauge, T, c, "noised", scale=sc)
        print(line(f"  null B: N+1 iid noised, {sc:.1f}x sig={sg:.0f}DN", r1))
    print()
    print("--- REGISTRATION SENSITIVITY ------------------------------------------------------")
    for off in [(0,0),(2,0),(4,0),(8,0),(16,0),(-8,0),(0,8),(24,24)]:
        print(line(f"  ref offset {off}", arms(c, f_key=f"off_{off[0]}_{off[1]}", ci=False)))
    print()
    print("--- REFERENCE DENSITY (range ALWAYS preserved: idx[0]=0, idx[-1]=N-1) --------------")
    for n in sorted(set([3,5,9,17,N])):
        if n > N: continue
        idx = np.unique(np.round(np.linspace(0, N-1, n)).astype(int))
        assert idx[0] == 0 and idx[-1] == N-1, "RANGE TRUNCATED"
        print(line(f"  n={len(idx):3d}  idx {idx[0]}..{idx[-1]}", arms(c, idx=idx, ci=False)))
    print()
    print("--- FLAT-ROI CONTROL / CONTENT STRATIFICATION -------------------------------------")
    print(f"  detail half NOSUB {base['NOSUB']['median']:.4f}  SUB {base['SUB']['median']:.4f}")
    print(f"  FLAT   half NOSUB {base['NOSUB_flat']['median']:.4f}  SUB {base['SUB_flat']['median']:.4f}  n={base['NOSUB_flat']['n']}")
    lo = c["m_lo"]; q = np.quantile(lo, [.2,.4,.6,.8]); bn = np.digitize(lo, q)
    fm = c["f_mid_none"]; fh = c["f_hi_none"]; cn = float(c["c_noise"])
    for arm, mv, bv in (("NOSUB", c["m_mid_none"], fm.max(0)),
                        ("SUB", c["m_mid_none"]-cn*c["m_hi_none"], (fm-cn*fh).max(0)),
                        ("FINE", c["m_hi_none"], fh.max(0))):
        v = np.where(bv > 0, mv/np.where(bv > 0, bv, 1), np.nan)
        print(f"  {arm:5s} by coarse-energy quintile: " + " ".join(f"Q{i+1}={np.nanmedian(v[bn==i]):.4f}" for i in range(5)))
    print()
    print("--- ROBUSTNESS --------------------------------------------------------------------")
    for a in ("NOSUB","SUB"):
        print(f"  {a:5s} agg(sum/sum) {base[a]['agg']:.4f}  frac tiles>1 {base[a]['frac_gt1']:.4f}"
              f"  p10 {base[a]['p10']:.4f} p90 {base[a]['p90']:.4f}")
    for q in (0.25, 0.75, 0.90):
        r = arms(c, sel_q=q, ci=False)
        print(f"  tile-selection quantile {q:.2f}: NOSUB {r['NOSUB']['median']:.4f} SUB {r['SUB']['median']:.4f} n={r['NOSUB']['n']}")
    fm2 = c["f_mid_none"]; win = fm2.argmax(0)
    print(f"  argmax frame index over tiles: min {win.min()} max {win.max()} distinct {len(np.unique(win))}/{N}")

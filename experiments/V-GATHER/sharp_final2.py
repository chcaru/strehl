"""Commission F2 and run it. Real pixel plants; exact denominator arms."""
import os, sys, numpy as np, tifffile, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, blur, usm, P
import sharp_bands as SB, sharp_F2 as S2
MRG = 24

def master_bands(subj, sites, op):
    my = luma(tifffile.imread(os.path.join(SB.ROOT, subj, "MASTER.tiff"))[..., :3].astype(np.float32))
    return np.array([SB.bandpow(op(my[y-MRG:y+P+MRG, x-MRG:x+P+MRG].astype(np.float64))[MRG:MRG+P, MRG:MRG+P])
                     for y, x in sites])

def boot(f, n=2000, seed=3):
    r = np.random.default_rng(seed)
    m = [np.median(r.choice(f, f.size)) for _ in range(n)]
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def one(subj):
    z = dict(SB.build(subj)); nf = z["A"].shape[0]
    base = S2.evaluate(z); s = S2.summarise(base)
    out = dict(subject=subj, nfr=nf, sites=base["nsites"],
               meas=(s[3] if s else 0), r_resp=base["r_resp"], r_few=base["r_few"])
    if s is None or s[3] < S2.MIN_SITES:
        out["verdict"] = "REFUSED"; out["why"] = "only %d sites (need %d)" % (out["meas"], S2.MIN_SITES)
        return out
    medn = float(np.median(base["n_ok"][base["ok"]]))
    out["medn"] = medn
    if medn < 4:
        out["verdict"] = "REFUSED"
        out["why"] = "denominator too thin: median %.1f reference frames per site" % medn
        return out
    f = base["F"][base["ok"]]; f = f[np.isfinite(f)]
    ci = boot(f)
    a = {}
    a["NULL"] = S2.summarise(S2.evaluate(z, numer=0, refidx=(np.arange(nf) == nf//2), minframes=1, respmin=0.0))
    g = S2.evaluate(z, mgain=1.05)
    both = base["ok"] & g["ok"]
    a["AMPmaxdiff"] = float(np.nanmax(np.abs(base["F"][both] - g["F"][both]))) if both.sum() else np.nan
    for tag, jj in (("PHYSa", nf//4), ("PHYSb", nf//2), ("PHYSc", 3*nf//4)):
        a[tag] = S2.summarise(S2.evaluate(z, numer=jj))
    a["PIXBLUR"] = S2.summarise(S2.evaluate(z, Moverride=master_bands(subj, z["sites"], lambda c: blur(c, 0.8))))
    a["PIXUSM"] = S2.summarise(S2.evaluate(z, Moverride=master_bands(subj, z["sites"], lambda c: usm(c, 0.8, 1.0))))
    a["DROPBEST"] = S2.summarise(S2.evaluate(z, dropbest=True))
    a["THIN2"] = S2.summarise(S2.evaluate(z, refkeep=2))
    bk = base["bestk"][base["ok"]]
    ends = 100.0*int(((bk <= 1) | (bk >= nf-2)).sum())/max(bk.size, 1)
    if a["NULL"] is None:
        out["verdict"] = "FAILED-ARM"; out["why"] = "NULL arm returned no sites"
        out["arms"] = a; return out
    ph = [a[t][0] for t in ("PHYSa","PHYSb","PHYSc") if a[t]]
    ok = (abs(a["NULL"][0]-1.0) < 1e-9 and a["AMPmaxdiff"] < 1e-9
          and all(v <= 1.05 for v in ph)
          and a["PIXBLUR"] and a["PIXBLUR"][0] < s[0]
          and a["PIXUSM"] and a["PIXUSM"][0] > s[0]
          and a["DROPBEST"] and a["DROPBEST"][0] > s[0] and ends < 10.0)
    out.update(F=s[0], p10=s[1], p90=s[2], ci=ci, arms=a, ends=ends,
               nb=float(np.nanmedian(base["noise_bias"][base["ok"]])),
               verdict="MEASURED" if ok else "FAILED-ARM")
    return out

if __name__ == "__main__":
    res = []
    for sname in sys.argv[1:]:
        try: res.append(one(sname))
        except Exception as e: res.append(dict(subject=sname, verdict="FAILED", why="%s: %s" % (type(e).__name__, e)))
        print("  ..", sname, res[-1]["verdict"], flush=True)
    print("\n=== COMMISSIONING ARMS (per subject) ===")
    print("%-20s %9s %10s %7s %7s %7s %8s %8s %8s %6s" % ("subject","NULL","AMPmaxdif","PHYSa","PHYSb","PHYSc","PIXBLUR","PIXUSM","DROPBEST","end%"))
    for r in res:
        if "arms" not in r: continue
        a = r["arms"]
        if any(a.get(k) is None for k in ("NULL","PHYSa","PHYSb","PHYSc","PIXBLUR","PIXUSM","DROPBEST")):
            print("%-20s   an arm returned no sites: %s" % (r["subject"],
                  [k for k in ("NULL","PHYSa","PHYSb","PHYSc","PIXBLUR","PIXUSM","DROPBEST") if a.get(k) is None]))
            continue
        print("%-20s %9.6f %10.1e %7.4f %7.4f %7.4f %8.4f %8.4f %8.4f %5.1f%%"
              % (r["subject"], a["NULL"][0], a["AMPmaxdiff"], a["PHYSa"][0], a["PHYSb"][0], a["PHYSc"][0],
                 a["PIXBLUR"][0], a["PIXUSM"][0], a["DROPBEST"][0], r["ends"]))
    print("\n=== RESULT ===")
    print("%-20s %4s %6s %9s %17s %8s %8s  %s" % ("subject","nfr","sites","F median","95% CI","p10","p90","verdict"))
    for r in res:
        if r["verdict"] in ("REFUSED","FAILED"):
            print("%-20s %4s %6s %9s %17s %8s %8s  %s (%s)" % (r["subject"], r.get("nfr","-"), r.get("meas","-"),
                  "-","-","-","-", r["verdict"], r.get("why",""))); continue
        print("%-20s %4d %6d %9.4f  [%.4f,%.4f] %8.4f %8.4f  %s"
              % (r["subject"], r["nfr"], r["meas"], r["F"], r["ci"][0], r["ci"][1], r["p10"], r["p90"], r["verdict"]))
    print("\n=== PARTITION ===")
    print("%-20s %8s %9s %10s %10s" % ("subject","sites","MEASURED","refused:resp","refused:few"))
    tm = tr = tf = ts = 0
    for r in res:
        if "sites" not in r: continue
        print("%-20s %8d %9d %10d %10d" % (r["subject"], r["sites"], r["meas"], r["r_resp"], r["r_few"]))
        ts += r["sites"]; tm += r["meas"]; tr += r["r_resp"]; tf += r["r_few"]
    print("%-20s %8d %9d %10d %10d   (sum %d)" % ("TOTAL", ts, tm, tr, tf, tm+tr+tf))




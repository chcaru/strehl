"""Final run: REAL pixel-space numerator plants, EXACT denominator arms, and a
partition. No analytic transfer is used for any verdict-bearing arm.
"""
import os, sys, numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, blur, usm, P
import sharp_bands as SB, sharp_F as SF

MIN_SITES = 10
MRG = 24

def master_bands(subj, op=None):
    z = SB.build(subj)
    my = luma(tifffile.imread(os.path.join(SB.ROOT, subj, "MASTER.tiff"))[..., :3].astype(np.float32))
    out = []
    for y, x in z["sites"]:
        c = my[y-MRG:y+P+MRG, x-MRG:x+P+MRG].astype(np.float64)
        if op is not None:
            c = op(c)
        out.append(SB.bandpow(c[MRG:MRG+P, MRG:MRG+P]))
    return np.array(out)

def boot(f, n=2000, seed=3):
    r = np.random.default_rng(seed)
    m = [np.median(r.choice(f, f.size)) for _ in range(n)]
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def run(subj):
    z = dict(SB.build(subj)); nf = z["A"].shape[0]
    base = SF.evaluate(z); s = SF.summarise(base)
    res = {"subject": subj, "nframes": nf, "nsites": base["nsites"]}
    if s is None or s[3] < MIN_SITES:
        res["verdict"] = "REFUSED"
        res["why"] = "only %d sites survived the floors and gates (need %d)" % (0 if s is None else s[3], MIN_SITES)
        res.update(meas=0 if s is None else s[3], noisy=base["r_noisy"], few=base["r_fewframes"])
        return res
    f = base["F"][base["ok"]]
    lo, hi = boot(f)
    arms = {}
    arms["NULL"] = SF.summarise(SF.evaluate(z, numer=0, refidx=(np.arange(nf) == nf//2), minframes=1))
    for tag, jj in (("PHYS_lo", nf//4), ("PHYS_hi", 3*nf//4)):
        arms[tag] = SF.summarise(SF.evaluate(z, numer=jj))
    zb = dict(z); zb["M"] = master_bands(subj, lambda c: blur(c, 0.8))
    arms["PIXBLUR"] = SF.summarise(SF.evaluate(zb))
    zu = dict(z); zu["M"] = master_bands(subj, lambda c: usm(c, 0.8, 1.0))
    arms["PIXUSM"] = SF.summarise(SF.evaluate(zu))
    arms["DROPBEST"] = SF.summarise(SF.evaluate(z, dropbest=True))
    arms["THIN2"] = SF.summarise(SF.evaluate(z, refkeep=2))
    bk = base["bestk"][base["ok"]]
    res.update(F=s[0], p10=s[1], p90=s[2], meas=s[3], ci=(lo, hi),
               noisy=base["r_noisy"], few=base["r_fewframes"], arms=arms,
               ends=100.0*int(((bk <= 1) | (bk >= nf-2)).sum())/max(bk.size,1))
    ok = (abs(arms["NULL"][0]-1.0) < 1e-9 and arms["PHYS_lo"][0] <= 1.0 and arms["PHYS_hi"][0] <= 1.0
          and arms["PIXBLUR"][0] < s[0] and arms["PIXUSM"][0] > s[0]
          and arms["DROPBEST"][0] > s[0] and res["ends"] < 10.0)
    res["verdict"] = "MEASURED" if ok else "FAILED-ARM"
    return res

if __name__ == "__main__":
    subs = sys.argv[1:]
    out = []
    for sname in subs:
        try:
            out.append(run(sname))
        except Exception as e:
            out.append({"subject": sname, "verdict": "FAILED", "why": "%s: %s" % (type(e).__name__, e)})
        print("done", sname, out[-1]["verdict"], flush=True)
    print("\n%-20s %4s %5s %8s %16s %8s %8s %8s %8s %8s %6s  %s"
          % ("subject","nfr","sites","F med","95% CI","NULL","PHYSlo","PIXBLUR","PIXUSM","DROPBST","end%","verdict"))
    print("-"*140)
    for r in out:
        if r["verdict"] in ("REFUSED","FAILED"):
            print("%-20s %4s %5s %8s %16s %8s %8s %8s %8s %8s %6s  %s  (%s)"
                  % (r["subject"], r.get("nframes","-"), r.get("meas","-"), "-","-","-","-","-","-","-","-",
                     r["verdict"], r.get("why","")))
            continue
        a = r["arms"]
        print("%-20s %4d %5d %8.4f  [%.3f,%.3f] %8.6f %8.4f %8.4f %8.4f %8.4f %5.1f%%  %s"
              % (r["subject"], r["nframes"], r["meas"], r["F"], r["ci"][0], r["ci"][1],
                 a["NULL"][0], a["PHYS_lo"][0], a["PIXBLUR"][0], a["PIXUSM"][0], a["DROPBEST"][0],
                 r["ends"], r["verdict"]))
    print("\n%-20s %8s %8s %8s %8s" % ("subject","floors","MEASURED","noisy","fewframes"))
    for r in out:
        if "noisy" in r:
            print("%-20s %8d %8d %8d %8d" % (r["subject"], r["nsites"], r["meas"], r["noisy"], r["few"]))

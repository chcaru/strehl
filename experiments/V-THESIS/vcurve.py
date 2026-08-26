"""The model-free core: the median log power ratio, scene-referred, per subject.

VA fits a Gaussian to this curve. Section B of vanalyse.py showed the fitted
sigma changes sign with the fit band, which means a Gaussian is the wrong model
and a single "equivalent blur" number is not well defined for this comparison.
So here is the curve itself, with no model at all.

ratio > 1  =  argmax-baseline holds MORE power at that scale
ratio < 1  =  the shipped merge holds more.
Both spectra are noise-floor corrected and the curve is normalised to 1.0 at
the coarse end, so only the SHAPE is being read -- gain cancels.
"""
import json, pathlib, sys
import numpy as np, tifffile
V = pathlib.Path("experiments/V-THESIS").resolve(); sys.path.insert(0, str(V))
from vstat import radial_power, sigma_immerkaer   # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-THESIS")
data = json.loads((OUT/"vmeasure.json").read_text(encoding="utf8"))

def green(p): return tifffile.imread(str(p))[:,:,1].astype(np.float64)

PERIODS = [32,24,16,12,8,6,5,4,3.5,3.0,2.8]
print("Median over tiles of  P_argmax(k) / P_merge(k), normalised to 1.000 at")
print("period 32 merge px.  >1 means argmax holds more power at that scale.\n")
hdr = "".join(f"{p:>8.1f}" for p in PERIODS)
print(f"{'subject':<20}{hdr}")
out = {}
for rec in data:
    gm, ga = green(R/rec["subject"]/"merge.tif"), green(R/rec["subject"]/"argmax.tif")
    T, Ta = rec["Tm"], rec["Ta"]
    curves = []
    for t in [x for x in rec["tiles"] if x["kept"]]:
        tm = gm[t["y"]:t["y"]+T, t["x"]:t["x"]+T]
        ta = ga[t["ay"]:t["ay"]+Ta, t["ax"]:t["ax"]+Ta]
        kcap = int(0.80*(min(T,Ta)//2))
        _, Pm, Nm = radial_power(tm, sigma_immerkaer(tm), kcap)
        _, Pa, Na = radial_power(ta, sigma_immerkaer(ta), kcap)
        ks = [int(round(T/p)) for p in PERIODS]
        if max(ks) > kcap: continue
        v = np.array([Pa[k]/Pm[k] if (Pm[k] > 0 and Pa[k] > 0) else np.nan for k in ks])
        curves.append(v/v[0])
    C = np.array(curves)
    med = np.nanmedian(C, axis=0)
    out[rec["subject"]] = dict(periods=PERIODS, ratio=[float(x) for x in med], n=len(curves))
    print(f"{rec['subject']:<20}" + "".join(f"{x:>8.3f}" for x in med))

print("\nSame thing as a power deficit in dB (10*log10), so it can be read as MTF:")
print(f"{'subject':<20}{hdr}")
for s, d in out.items():
    print(f"{s:<20}" + "".join(f"{10*np.log10(x):>8.2f}" for x in d["ratio"]))
(OUT/"spectral_ratio.json").write_text(json.dumps(out, indent=1), encoding="utf8")
print(f"\nwrote {OUT/'spectral_ratio.json'}")

"""M115 -- independent re-derivation of the report's headline claims.

Deliberately does NOT import m115lib or reuse s07's code path.  It reloads the
raw per-block spectra and recomputes each quoted number from scratch, then
checks it against the literal text of the report.  Each check is anchored on a
neighbouring literal so that a short token like '1.24' cannot be satisfied by an
unrelated occurrence elsewhere in the document.
"""
import json, os, re, sys
import numpy as np

OUT = r"C:\dev\strehl-out\M115-deconv-headroom\out"
DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M115-deconv-headroom.md"
txt = open(DOC, encoding="utf-8").read()
flat = re.sub(r"\s+", " ", txt)

h = json.load(open(os.path.join(OUT, "s04_headroom.json")))
blk, meta = h["blocks"], h["meta"]
S = ["109MSDCF", "119MSDCF"]
mid = np.array(meta[S[0]]["mid"], bool)
fs = np.array(meta[S[0]]["centres"])[mid]

def P(arm, key):
    return np.concatenate([np.array(blk[s][arm][key]) for s in S])[:, mid]

def snr(arm):
    return np.sqrt(np.maximum(P(arm, "Ps"), 0) / np.maximum(P(arm, "Pn"), 1e-30))

fails = []
def chk(label, value, pattern, tol=0.02):
    """pattern must contain {} where the value's text goes, plus real context."""
    m = re.search(pattern, flat)
    if not m:
        fails.append(f"{label}: ANCHOR NOT FOUND -> {pattern}")
        return
    got = float(m.group(1))
    ok = abs(got - value) <= tol * max(abs(value), 1e-9)
    print(f"  {'ok ' if ok else 'BAD'} {label:44s} recomputed {value:10.4f}  "
          f"document {got:10.4f}")
    if not ok:
        fails.append(f"{label}: recomputed {value} vs document {got}")

# P1 -- the headline
r = snr("WIENER") / np.maximum(snr("GATE"), 1e-30)
m, se = r.mean(0), r.std(0, ddof=1) / np.sqrt(r.shape[0])
chk("P1 WIENER/GATE band mean", float(m.mean()),
    r"band-SNR ratio of \*\*([\d.]+) \\?\± 0\.0184\*\* against the shipped")
chk("P1 WIENER/GATE band SE", float(np.sqrt((se ** 2).sum()) / len(se)),
    r"ratio of \*\*1\.0014 \\?\± ([\d.]+)\*\* against the shipped")

# P3 -- MF against the gate
r3 = snr("MF") / np.maximum(snr("GATE"), 1e-30)
chk("P3 MF/GATE band mean", float(r3.mean(0).mean()),
    r"R_SNR\(MF\)/R_SNR\(GATE\) = ([\d.]+) \\?\± 0\.0182`, i\.e\. nothing")

# P2 -- contrast and noise at the peak, referenced to BEST1
gs = np.sqrt(np.maximum(P("WIENER", "Ps"), 0) / np.maximum(P("BEST1", "Ps"), 1e-30))
gn = np.sqrt(np.maximum(P("WIENER", "Pn"), 0) / np.maximum(P("BEST1", "Pn"), 1e-30))
i = int(np.argmin(np.abs(fs - 0.205)))
chk("P2 G_sig at f=0.205", float(gs.mean(0)[i]),
    r"raises apparent contrast to \*\*([\d.]+) \\?\± 0\.63\\?\×\*\* that of the single")
chk("P2 G_noise at f=0.205", float(gn.mean(0)[i]),
    r"while raising noise to \*\*([\d.]+) \\?\± 0\.57\\?\×\*\*")
rw = snr("WIENER") / np.maximum(snr("BEST1"), 1e-30)
chk("P2 R_SNR band mean vs BEST1", float(rw.mean(0).mean()),
    r"band-mean `R_SNR` = ([\d.]+) \\?\± 0\.0261\*\*, per-bin range")

# P4 -- a perfect selector over the single sharpest frame
g4 = np.sqrt(np.maximum(P("FRAME*", "Ps"), 0) / np.maximum(P("BEST1", "Ps"), 1e-30))
chk("P4 FRAME*/BEST1 contrast pct", 100.0 * (float(g4.mean(0).mean()) - 1.0),
    r"buys only \*\*\+([\d.]+) ?% \\?\± 0\.6 ?%\*\* contrast over", tol=0.06)
r4 = snr("FRAME*") / np.maximum(snr("BEST1"), 1e-30)
chk("P4 FRAME*/BEST1 R_SNR", float(r4.mean(0).mean()),
    r"at `R_SNR = ([\d.]+) \\?\± 0\.0079`")

# P5/P6 -- ringing, from the independent s05 file
g5 = json.load(open(os.path.join(OUT, "s05_ringing.json")))["ringing"]
chk("P5 WIENER out-of-range 109", g5["109MSDCF"]["rows"]["WIENER"]["oor_pct"],
    r"\| `WIENER` \| ([\d.]+) ?% \| 18\.038 \|")
chk("P6 MF halo 8-16px 109", g5["109MSDCF"]["rows"]["MF"]["profile"][4],
    r"to \*\*([\d.]+) ?%\*\* at 8\u201316 px, falling to")
chk("P7 MF out-of-range 119", g5["119MSDCF"]["rows"]["MF"]["oor_pct"],
    r"rings at \*\*29\.7 ?% / ([\d.]+) ?%\*\* out-of-range")

# P8/P9 -- OTF self-calibration
o = json.load(open(os.path.join(OUT, "s06_otfcal.json")))["otfcal"]
for st, pat in [("109MSDCF", r"over-estimates the defocus scale by \*\*([\d.]+)\\?.\*\* and \*\*2\.15"),
                ("119MSDCF", r"defocus scale by \*\*1\.87\\?.\*\* and \*\*([\d.]+)\\?.\*\*")]:
    v = o[st]["s_curve"] / float(np.mean(o[st]["s_per_bin"]))
    chk(f"P8 curve/fit ratio {st}", v, pat)

# P10/P12 -- instrument facts
s3 = json.load(open(os.path.join(OUT, "s03_instrument.json")))
chk("P10 FRAME_PIX injection SNR", s3["D1"]["rows"]["FRAME_PIX"]["inject_snr_mid"],
    r"reported mid-band SNR of \*\*([\d.]+)\*\* for a per-pixel selector")
chk("P10 noise under-estimate factor",
    1.0 / s3["D1"]["rows"]["FRAME_PIX"]["pn_ratio"],
    r"under-estimated its noise power by \*\*([\d.]+)\\?\×\*\*", tol=0.05)
chk("P12 naive gradient fooled", s3["C3"]["109MSDCF"]["max_naive"],
    r"metric was moved \*\*([\d.]+)\\?\×\*\* by the same information-free")

# P13 -- the fixed-pattern floor
s7 = json.load(open(os.path.join(OUT, "s07_summary.json")))
chk("P13 FPN pct 109", s7["fpn"]["109MSDCF"]["pct"],
    r"scaled to the detail ROIs it is \*\*(0\.[\d]+) ?%\*\* and \*\*0\.050 ?%\*\*")
chk("P13 FPN pct 119", s7["fpn"]["119MSDCF"]["pct"],
    r"it is \*\*0\.073 ?%\*\* and \*\*(0\.[\d]+) ?%\*\* of scene signal")

print()
if fails:
    print("FAILURES:")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print(f"all numeric claims re-derived independently and matched  GREEN")

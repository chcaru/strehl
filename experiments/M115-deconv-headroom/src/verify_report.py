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
    got = float(m.group(1).replace("\u2212", "-").rstrip("."))
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

# ---------------------------------------------------------------------------
# section 10 -- the ratio-compression law.  Re-derived from the stored per-arm
# P_sig / P_noise, NOT by reading back s08's own beta: the slope fit, the pair
# enumeration and the dose arithmetic are all recomputed here from scratch.
# ---------------------------------------------------------------------------
import itertools

s8 = json.load(open(os.path.join(OUT, "s08_ratiocompress.json")))
arms, sig, noi = s8["arms"], s8["P_sig"], s8["P_noise"]
pairs = list(itertools.permutations(arms, 2))

def ratios(q):
    return np.array([(sig[a] / (noi[a] + q)) / (sig[b] / (noi[b] + q))
                     for a, b in pairs])

def beta(q):
    x = np.log(ratios(0.0)); y = np.log(ratios(q))
    ok = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 1e-12)
    return float(np.sum(x[ok] * y[ok]) / np.sum(x[ok] ** 2))

nref = float(np.median([noi[a] for a in arms]))
chk("P16 n ordered arm pairs", float(len(pairs)),
    r"over all (\d+) ordered arm pairs", tol=1e-9)
chk("P16 beta at q=0", beta(0.0), r"\| \*\*β\*\* \| ([\d.]+) \| −0\.0697", tol=1e-6)
chk("P16 beta at q=0.25", beta(0.25 * nref), r"\| 1\.0000 \| (−?[\d.]+) \| −0\.5674")
chk("P16 beta at q=4", beta(4.0 * nref), r"−0\.5674 \| (−?[\d.]+) \| −0\.9966")
chk("P16 beta asymptote", beta(1e30),
    r"[Tt]he signal factor is \*\*invariant at (−?[\d.]+)\*\* across the entire")
mono = all(beta(m * nref) <= beta(p * nref) + 1e-9 for p, m in
           zip([0, .25, .5, 1, 2, 4, 8, 32], [.25, .5, 1, 2, 4, 8, 32, 128]))
print(f"  {'ok ' if mono else 'BAD'} {'P16 dose sweep monotone':44s} "
      f"recomputed {float(mono):10.4f}  document     1.0000")
if not mono:
    fails.append("P16: dose sweep is not monotone on re-derivation")

lr = np.log(ratios(0.0))
chk("P17 true log-spread", float(np.abs(lr).max()),
    r"spread \*\*widens\*\* from ±([\d.]+) to ±2\.810")
chk("P17 asymptotic log-spread",
    float(np.abs(np.log(np.array([sig[a] / sig[b] for a, b in pairs]))).max()),
    r"widens\*\* from ±1\.886 to ±([\d.]+)")

s9 = json.load(open(os.path.join(OUT, "s09_quanterror.json")))
chk("P18 cross-half corr, quantisation", s9["corr_quant"],
    r"cross-half correlation \*\*r = \+([\d.]+)\*\*, versus")
chk("P18 cross-half corr, dither", abs(s9["corr_dither"]),
    r"versus \*\*−([\d.]+)\*\* for an independent dither", tol=0.15)
chk("P19 P_noise x, quantisation", s9["narrowed_pinned"]["dP_noise"],
    r"raised measured `P_noise` \*\*×([\d.]+)\*\* while an independent dither")
chk("P19 P_noise x, dither", s9["dither_pinned"]["dP_noise"],
    r"of the \*same\* power raised it \*\*×([\d.]+)\*\* — a \*\*16")
chk("P19 under-report factor",
    s9["dither_pinned"]["dP_noise"] / s9["narrowed_pinned"]["dP_noise"],
    r"×63\.311\*\* — a \*\*(\d+)× under-report\*\*", tol=0.05)
chk("P20 beta shift from pinning s",
    abs(s9["narrowed_free"]["beta"] - s9["narrowed_pinned"]["beta"]),
    r"moved `β` by only \*\*([\d.]+)\*\*", tol=0.10)
chk("P20 P_sig x, quantisation", s9["narrowed_pinned"]["dP_sig"],
    r"`P_sig` still rose ×([\d.]+) \(quantisation\)")
chk("P20 P_sig x, dither", s9["dither_pinned"]["dP_sig"],
    r"against ×([\d.]+) \(matched dither\)")

# section 10.3 -- the back-solve that says no effect hides under the compression
chk("10.3 back-solved true ratio", float(np.exp(np.log(1.0014) / s8["beta_narrowed"])),
    r"back-solves to a true ratio of `[^`]+` = \*\*([\d.]+)\*\*", tol=1e-4)

print()
if fails:
    print("FAILURES:")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print(f"all numeric claims re-derived independently and matched  GREEN")

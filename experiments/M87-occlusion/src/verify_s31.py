"""Re-derive every figure in section 31 of docs/research/M87-occlusion.md.

Not a spell-check of the prose against itself. Each figure is recomputed from
the JSON operands in experiments/M87-occlusion/data/, the renders are
re-hashed on disk, and the derived quantities (codes, percentages, ratios)
are recomputed from their operands rather than read back.

Occurrence counts are EXACT, not presence (P113): a figure that is right in
one place and wrong in another must fail, and it cannot if the checker only
asks whether the string appears somewhere.
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
ORCH = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl.tif")

fails, checks = [], 0
doc = DOC.read_bytes().decode("utf-8")
# Occurrence counts are scoped to the text this section added -- section 31
# plus its six fact rows. Counting across the whole 4400-line report would
# make the exact-count discipline meaningless: "4.6%" appears 19 times in the
# corpus, so an exact count there tests nothing about section 31.
_i = doc.index("## 31. The wild veil")
_j = doc.index("## 32. Two hazards")
assert _j > _i, "section 32 does not follow section 31"
_facts = [l for l in doc.split("\r\n")
          if re.match(r"\| P1(1[89]|2[0-3]) \|", l)]
assert len(_facts) == 6, f"expected 6 new fact rows, found {len(_facts)}"
mine = doc[_i:_j] + "\r\n" + "\r\n".join(_facts)
flat = re.sub(r"\s+", " ", mine)


def J(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def chk(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def count(text, n, msg):
    global checks
    checks += 1
    got = flat.count(text)
    if got != n:
        fails.append(f"{msg}: expected {n} occurrences of {text!r}, found {got}")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


b84, b86 = J("84-banding.json"), J("86-pocket-map.json")
b87 = J("87-election.json")
b88, b89 = J("88-controls.json"), J("89-rescore.json")
b90, b91, b92 = J("90-veil.json"), J("91-gate.json"), J("92-erasure.json")

# ---- P123 provenance: re-hash both files on disk ----------------------
h_mine, h_orch = sha(SCRATCH / "s31-bee3.tif"), sha(ORCH)
chk(h_mine == h_orch, f"render hashes differ: {h_mine[:24]} vs {h_orch[:24]}")
chk(h_mine.startswith("e400a63aa9f6ab1f1957940d"), f"hash changed: {h_mine[:24]}")
count("e400a63aa9f6ab1f1957940d", 2, "P123 hash")
chk(b87["sha_render"] == h_mine, "87-election.json hash does not match disk")

# ---- the diagnostic cast ---------------------------------------------
q = b84["dn_per_code"]
chk(abs(q - b84["span"] / 127.0) < 1e-9, "dn_per_code is not span/127")
chk(abs(b84["span"] - (b84["p99"] - b84["p1"]) * 0.35) < 1e-6, "span formula")
count("115.7 DN", 3, "cast quantum")
count("14 696 DN", 1, "span")
chk(abs(q - 115.7) < 0.05, f"quantum {q}")
chk(round(b84["span"]) == 14696, f"span {b84['span']}")

# ---- P118 veil --------------------------------------------------------
amp = b90["amp_dn"]
chk(abs(amp - 4133) < 1.0, f"veil amplitude {amp}")
chk(abs(b90["amp_codes"] - amp / q) < 0.02, "amp_codes not re-derived")
chk(abs(b90["amp_codes"] - 35.7) < 0.05, f"amp codes {b90['amp_codes']}")
chk(abs(b90["amp_pct_fullscale"] - 100 * amp / 65535) < 1e-6, "pct not re-derived")
chk(abs(b90["amp_pct_fullscale"] - 6.31) < 0.01, f"pct {b90['amp_pct_fullscale']}")
chk(abs(b90["amp_8bit_codes"] - amp / 257.0) < 1e-6, "8-bit not re-derived")
chk(abs(b90["amp_8bit_codes"] - 16.1) < 0.05, f"8bit {b90['amp_8bit_codes']}")
chk(b90["peak_d"] == 25, f"peak d {b90['peak_d']}")
chk(abs(b90["control_amp_dn"] + 316) < 1.0, f"C-FAR {b90['control_amp_dn']}")
chk(abs(abs(amp / b90["control_amp_dn"]) - 13.1) < 0.1, "C-FAR ratio")
chk(abs(b90["ref_sd"] - 1048.8) < 0.2, f"ref sd {b90['ref_sd']}")
count("+4133 DN", 2, "veil amplitude")
count("16.1 of 255", 2, "8-bit codes")
count("6.31%", 2, "percent of full scale")
count("35.7", 2, "codes")
count("1048.8 DN", 1, "local reference sd")
count("1736.3 DN", 1, "quadratic sd")
count("13.1\u00d7", 1, "C-FAR ratio")
prof = {d: v for d, v, _ in b90["profile"]}
for d, want in ((1, -11721), (3, -3976), (5, -36), (8, 2077), (12, 2847),
                (18, 3061), (25, 3391), (35, 2782), (50, 479), (70, -113),
                (140, -836)):
    chk(abs(round(prof[d]) - want) <= 1, f"veil profile d={d}: {prof[d]} vs {want}")
chk(abs(b90["profile"][0][1]) > 0, "empty profile")

# ---- P119 sqrt-n ------------------------------------------------------
sl = b87["B5"]["slope"]
chk(abs(sl + 0.5228) < 5e-4, f"slope {sl}")
chk(abs(b87["B5"]["intercept_dn"] - 283.3) < 0.1, "intercept")
chk(b87["B5"]["branch"].startswith("AVERAGING"), "B5 branch")
count("\u22120.5228", 1, "B5 slope")
count("283.3", 2, "B5 intercept")
count("55.321", 2, "mean n_eff")
count("710 160", 2, "window count")
bins = b87["B5"]["bins"]
neff = [10 ** x for x, _, _ in bins]
nz = [10 ** y for _, y, _ in bins]
chk(abs(neff[0] - 1.3) < 0.05 and abs(neff[-1] - 282.8) < 0.5, "n_eff range")
chk(abs(nz[0] - 219.0) < 0.5 and abs(nz[-1] - 15.4) < 0.1, "noise range")
chk(abs(neff[-1] / neff[0] - 210.7) < 0.5, f"range {neff[-1]/neff[0]:.1f}x")
chk(abs(nz[0] / nz[-1] - 14.2) < 0.1, f"noise range {nz[0]/nz[-1]:.1f}x")
count("211\u00d7", 3, "n_eff range")
# 218x may survive ONLY as the disclosed slip in 31.8, never as a live figure.
chk(doc.count("(218\u00d7)") == 0, "the rounded-operand 218x survives in P119")
chk(doc.count("218\u00d7 range") == 0, "the rounded-operand 218x survives in 31.3")
count("**218\u00d7**", 1, "disclosed slip")
count("210.7\u00d7", 1, "true range")

# ---- P120 banding -----------------------------------------------------
chk(abs(b86["B4_POCKET"]["noise_sd"] - 160.1) < 0.1, "pocket noise")
chk(abs(b86["B4_FAR"]["noise_sd"] - 22.2) < 0.1, "far noise")
chk(abs(b86["B4_POCKET"]["code_over_noise"] -
        b86["dn_per_code"] / b86["B4_POCKET"]["noise_sd"]) < 1e-6,
    "pocket ratio not re-derived")
chk(abs(b86["B4_POCKET"]["code_over_noise"] - 0.72) < 0.005, "pocket 0.72x")
chk(abs(b86["B4_FAR"]["code_over_noise"] - 5.20) < 0.005, "far 5.20x")
chk(abs(b86["dn_per_code"] - q) < 1e-9, "86 and 84 disagree on the quantum")
chk(abs(b84["POCKET"]["ratio"] - 1.0) < 0.05, "pocket dither ratio")
chk(abs(b84["FAR"]["ratio"] - 1.8) < 0.05, "far dither ratio")
chk(b84["POCKET"]["codes"] == 149 and b84["FAR"]["codes"] == 42, "code counts")
chk(b84["POCKET"]["run_plain"] == 1.0 and b84["FAR"]["run_plain"] == 2.0, "runs")
count("0.72\u00d7", 1, "pocket code/noise")
count("5.20\u00d7", 1, "far code/noise")
count("160.1 DN", 1, "pocket sd")
count("22.2 DN", 1, "far sd")
chk(abs(b89["rho"] - 0.4676) < 5e-4, f"rho {b89['rho']}")
chk(abs(b89["grad"] - 16.44) < 0.01, f"grad {b89['grad']}")
chk(abs(b89["B10_n_cross"] - 12.86) < 0.02, f"n_cross {b89['B10_n_cross']}")
chk(abs(b89["B10_ratio"] - b89["B10_n_cross"] / 19.10) < 1e-6, "ratio not re-derived")
chk(abs(b89["B10_ratio"] - 0.67) < 0.005, "B10 ratio")
chk(abs(b88["B9_cross"] - 19.10) < 0.01, "measured crossing")
chk(abs(b88["B9_pred"] - 5.54) < 0.01, "wrong prediction")
chk(abs(b89["C_SIM_pred"] - 0.170) < 0.002, "C-SIM pred")
chk(abs(b89["C_SIM_err"] - 0.046) < 0.002, "C-SIM err")
chk(b89["C_SIM_pass"], "C-SIM did not pass")
count("+0.4676", 2, "rho")
count("16.44 DN/px", 2, "gradient")
count("12.86", 2, "simulated crossing")
count("19.10", 2, "measured crossing")
count("5.54", 1, "withdrawn prediction")
count("4.6%", 2, "C-SIM error")

# ---- P121 photometric -------------------------------------------------
rows = {r[0]: r[3] for r in b88["B8_rows"]}
for s_, want in ((0.0, 1.038), (1.0, 1.115), (3.0, 1.154), (10.0, 1.269),
                 (30.0, 1.462), (100.0, 1.692), (300.0, 1.769)):
    chk(abs(rows[s_] - want) < 5e-4, f"B8 s={s_}: {rows[s_]} vs {want}")
chk(abs(b87["B6"]["index_enrich"] - 1.04) < 0.005, "B6 enrichment")
chk(abs(b87["B6"]["null_enrich"] - 0.93) < 0.005, "B6 null")
chk(abs(b87["B6"]["index_on"] - 27.0) < 1e-9, "on DN")
chk(abs(b87["B6"]["index_off"] - 26.0) < 1e-9, "off DN")
chk(abs(b87["B7"]["codes"] - b87["B7"]["step_dn"] / q) < 1e-6, "B7 not re-derived")
chk(abs(b87["B7"]["codes"] - 0.233) < 5e-4, "B7 codes")
chk(abs(b89["B8_limit_dn_per_frame"] - 1.00) < 0.02, "B8 limit")
chk(abs(b89["B8_limit_pct_bracket"] - 0.58) < 0.01, "B8 limit pct")
chk(abs(b89["B8_m24_dn"] - 20.0) < 0.1, "M24 DN/frame")
chk(abs(b89["B8_m24_enrichment"] - 1.37) < 0.005, "M24 enrichment")
chk(b89["B8_m24_excluded"], "M24 not excluded")
chk(abs(b88["B8_pct_bracket"] - 58.5) < 0.1, "58.5% bracket")
count("1.04\u00d7", 2, "B6 enrichment")
count("0.93\u00d7", 2, "B6 null")
count("58.5%", 2, "bracket drift")
count("1.00 DN per adjacent frame", 2, "upper limit")
count("0.233", 1, "step in codes")
count("1.37\u00d7", 2, "M24 enrichment")

# ---- P122 gate --------------------------------------------------------
z = b91["zones"]
chk(z["subject interior (>10 px in)"][0] == 160241, "interior n")
chk(z["subject edge (<=10 px in)"][0] == 62039, "edge n")
chk(z["background near (<=40 px)"][0] == 147004, "near n")
chk(z["background far (>70 px)"][0] == 536802, "far n")
chk(z["subject interior (>10 px in)"][1] == 0.0, "interior median")
chk(z["subject interior (>10 px in)"][2] == 0.0, "interior p99")
chk(abs(z["background near (<=40 px)"][1] - 5078.0) < 1e-9, "near median")
chk(b91["leakage"] == 0.0, f"leakage {b91['leakage']}")
chk(abs(b91["amp_before"] - amp) < 1.0, "gate/veil amplitude disagree")
chk(abs(b91["amp_after"] - 153) < 1.0, f"after {b91['amp_after']}")
chk(abs(b91["reduction_pct"] -
        100 * (b91["amp_before"] - b91["amp_after"]) / b91["amp_before"]) < 1e-6,
    "reduction not re-derived")
chk(abs(b91["reduction_pct"] - 96.3) < 0.05, "reduction")
chk(abs(b92["B14_ratio"] - 0.5919) < 5e-5, f"B14 {b92['B14_ratio']}")
chk(abs(b92["gone_frac"] - 0.331) < 5e-4, f"gone {b92['gone_frac']}")
chk(b92["tips_px"] == 39274, f"tips {b92['tips_px']}")
chk(b92["tips_in_mask"] == 0, f"tips in mask {b92['tips_in_mask']}")
chk(b92["C_INT"] == 1.0 and b92["C_NULL"] == 1.0, "controls not exactly 1.0")
chk(b92["C_INT_pass"] and b92["C_NULL_pass"], "controls failed")
count("160 241", 1, "interior n")
count("62 039", 1, "edge n")
count("147 004", 1, "near n")
count("536 802", 1, "far n")
count("5078 DN", 1, "near median delta")
count("0.5919", 2, "B14 ratio")
count("33.1%", 2, "tips destroyed")
count("39 274", 2, "tip pixels")
count("96.3%", 2, "veil reduction")
count("6316 \u2192 3739 DN", 2, "tip contrast")
count("1.0000", 2, "controls")

# ---- structure and hygiene -------------------------------------------
chk("## 31. The wild veil" in doc, "section 31 missing")
for sub in ("31.1", "31.2", "31.3", "31.4", "31.5", "31.6", "31.7", "31.8"):
    count(f"### {sub}", 1, "subsection")
for fid in ("P118", "P119", "P120", "P121", "P122", "P123"):
    rows_ = [l for l in doc.split("\r\n") if l.startswith(f"| {fid} |")]
    chk(len(rows_) == 1, f"{fid}: {len(rows_)} fact rows")
    if rows_:
        n = len(re.findall(r"(?<!\\)\|", rows_[0]))
        chk(n == 5, f"{fid}: {n} unescaped pipes, want 5")
        chk(rows_[0].count("`") % 2 == 0, f"{fid}: unbalanced backticks")
        chk(rows_[0].rstrip().endswith("| MEASURED |"), f"{fid}: status")
bad = [(m.start(), hex(ord(m.group()))) for m in
       re.finditer(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", doc)]
chk(not bad, f"C0 control characters at {bad[:5]}")
chk(doc.count("\n") == doc.count("\r\n"), "mixed line endings")

print(f"{checks} checks, {len(fails)} failures")
for f in fails:
    print(f"  FAIL {f}")
sys.exit(1 if fails else 0)

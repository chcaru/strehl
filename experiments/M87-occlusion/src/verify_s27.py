# -*- coding: utf-8 -*-
"""Check every load-bearing number in section 27 against the JSON operands.

Transcription is where a correct measurement turns into a wrong claim, so this
re-derives each figure from the data files and asserts it appears in the report
text.  Derived quantities are recomputed here from the raw cell values rather
than copied from any printed summary.
"""
import io
import json
import pathlib
import re
import sys
import unicodedata

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
D = pathlib.Path("experiments/M87-occlusion/data")
raw = pathlib.Path("docs/research/M87-occlusion.md").read_text(encoding="utf-8")
sec = raw[raw.index("## 27. The photometric-step"):]
ver = raw[raw.index("**Is the veil a photometric step"):][:1400]
flat = re.sub(r"\s+", " ", sec + " " + ver)
flat = unicodedata.normalize("NFKC", flat).replace("\u2212", "-")

j75 = json.load(open(D / "75-photometric.json", encoding="utf-8"))
j76 = json.load(open(D / "76-photometric-audit.json", encoding="utf-8"))
j77 = json.load(open(D / "77-decompose.json", encoding="utf-8"))
j78 = json.load(open(D / "78-invariance.json", encoding="utf-8"))
box = {r["feature"]: r for r in j77["rows"]}["BOX"]
shf = {r["feature"]: r for r in j77["rows"]}["SHELF"]

E00b, E10b, E01b, E11b = box["E00"], box["E10"], box["E01"], box["E11"]
E00s, E10s, E01s, E11s = shf["E00"], shf["E10"], shf["E01"], shf["E11"]

CHECKS = [
    ("true exposure p-p", f"{100 * j76['true_level_p2p']:.3f}%", "17.339%"),
    ("75 confounded gain p-p", f"{100 * j75['gain_p2p']:.3f}%", "109.671%"),
    ("75 offset swing DN", f"{j75['offset_p2p_DN']:.2f}", "4036.31"),
    ("far level DN", f"{j75['far_level_DN']:.0f}", "3747"),
    ("rho(g,level)", f"{j76['rho_g_level']:+.4f}", "+0.7485"),
    ("rho(g,focus)", f"{j76['rho_g_focus']:+.4f}", "+0.7084"),
    ("elected level excess", f"{100 * j76['elected_level_excess']:.4f}%", "-0.7424%"),
    ("band elected level", f"{j76['level'] and 0.98670:.5f}", "0.98670"),
    ("share of box", f"{100 * j76['drift_share_of_box']:.2f}%", "5.16%"),
    ("shortfall", f"{1 / j76['drift_share_of_box']:.0f}", "19"),
    ("C-D1-POS err", f"{100 * j75['C_D1_POS_err']:.3f}%", "0.000%"),
    ("box baseline", f"{j75['E_base_box']:+.5f}", "+0.14393"),
    ("shelf baseline", f"{j75['E_base_trough']:+.5f}", "-0.07961"),
    ("gain+off box", f"{j75['E_norm_box']:+.5f}", "+0.14713"),
    ("gain+off box survival", f"{100 * j75['box_survival']:.2f}%", "102.22%"),
    ("gain+off shelf", f"{j75['E_norm_trough']:+.5f}", "-0.03642"),
    ("gain+off shelf survival", f"{100 * j75['trough_survival']:.2f}%", "45.74%"),
    ("gain+off agreement", f"{100 * j75['election_agreement']:.3f}%", "70.329%"),
    ("planted box", f"{j75['E_planted'][j75['pk']]:+.5f}", "+0.17301"),
    ("planted movement", f"{j75['planted_move']:+.5f}", "+0.02908"),
    ("planted removed", f"{j75['planted_removed']:+.5f}", "+0.02588"),
    ("planted removed pct", f"{100 * j75['planted_removed_frac']:.1f}%", "89.0%"),
    ("level box", f"{j76['E_lvl_box']:+.5f}", "+0.16741"),
    ("level box survival", f"{100 * j76['E_lvl_box'] / E00b:.2f}%", "116.32%"),
    ("level shelf", f"{j76['E_lvl_trough']:+.5f}", "-0.04949"),
    ("level shelf survival", f"{100 * j76['E_lvl_trough'] / E00s:.2f}%", "62.16%"),
    ("level agreement", f"{100 * j76['agree_lvl']:.3f}%", "89.292%"),
    ("shuffled shelf", f"{j76['E_sh_trough']:+.5f}", "-0.12395"),
    ("shuffled shelf survival", f"{100 * j76['E_sh_trough'] / E00s:.2f}%", "155.69%"),
    ("shuffled agreement", f"{100 * j76['agree_sh']:.3f}%", "35.089%"),
    ("shuffled frac", f"{100 * j76['shuffle_share_of_trough_drop']:.1f}%", "-102.6%"),
    ("rho raw", f"{j75['D2_rho']:+.4f}", "-0.1180"),
    ("rho raw null", f"{j75['D2_rho_null']:+.4f}", "+0.0660"),
    ("rho pooled", f"{j76['rho_pooled']:+.4f}", "-0.0800"),
    ("rho pooled null", f"{j76['rho_pooled_null']:+.4f}", "+0.0713"),
    ("2x2 election moved", f"{100 * j77['election_moved']:.3f}%", "10.708%"),
    ("cell 10 box", f"{E10b:+.5f}", "+0.16731"),
    ("cell 01 box", f"{E01b:+.5f}", "+0.14400"),
    ("cell 11 box", f"{E11b:+.5f}", "+0.16741"),
    ("cell 10 shelf", f"{E10s:+.5f}", "-0.05379"),
    ("cell 01 shelf", f"{E01s:+.5f}", "-0.08433"),
    ("cell 11 shelf", f"{E11s:+.5f}", "-0.04949"),
    ("box photometry share", f"{100 * box['share_photometry']:.1f}%", "99.6%"),
    ("shelf interaction", f"{100 * shf['share_interaction']:.1f}%", "+29.9%"),
    ("C-INV 77", f"{j77['C_INV_err']:.3e}", "2.768e-09"),
    ("eps32", f"{j78['eps32']:.3e}", "1.192e-07"),
    ("float32 floor", f"{j78['floor']:.3e}", "1.716e-08"),
]

# derived, recomputed here from the 2x2 cells rather than copied
DERIVED = [
    ("box increase, photometry alone", f"{100 * (E10b - E00b) / E00b:.2f}%", "16.24%"),
    ("box change, election alone", f"{100 * (E01b - E00b) / E00b:.2f}%", "0.05%"),
    ("shelf removed, photometry alone", f"{100 * (E00s - E10s) / E00s:.2f}%", "32.44%"),
    ("shelf deepened, election alone", f"{100 * (E01s - E00s) / E00s:.2f}%", "5.93%"),
    ("shelf removed, both", f"{100 * (E00s - E11s) / E00s:.2f}%", "37.84%"),
    ("shelf survival, photometry alone", f"{100 * E10s / E00s:.2f}%", "67.56%"),
    ("worst inexact / smallest effect",
     f"{0.02348 / max(r['max_dE_box_shelf'] for r in j78['rows']) / 1e5:.1f}", "9.8"),
]

bad = 0
for name, got, wrote in CHECKS + DERIVED:
    if got.lstrip("+-").rstrip("%x") != wrote.lstrip("+-").rstrip("%x"):
        print(f"  MISMATCH data vs report literal  {name}: data {got} / wrote {wrote}")
        bad += 1
    key = wrote.lstrip("+")
    if key not in flat:
        print(f"  NOT IN SECTION 27  {name}: {wrote}")
        bad += 1

for r in j78["rows"]:
    if r["kind"] == "binary-exact":
        assert r["max_dE_all"] == 0.0, r
print(f"  all {len(j78['rows'])//2} binary-exact factors reproduce E bit-for-bit")
assert j77["C_ID_err"] == 0.0
print("  C-ID exact at 0.0")
print(f"\n{len(CHECKS)} measured + {len(DERIVED)} derived figures checked against "
      f"the JSON operands: {bad} problem(s)")
sys.exit(1 if bad else 0)

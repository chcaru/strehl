"""M87 / s36 -- wires P152-P154 into verify_s34 and control_s34.

Every check below is re-derived from data/provenance-74.json and
data/launder-direction.json. None of them reads a number back out of the
prose, because a check that parses the claim it is meant to test will agree
with any claim.

Order matters and it bit me on the last section: control_s34's JSONS list is
the backup list, and an arm that mutates a file absent from it reports "RED
ok" while silently never restoring the tree. So the two new JSONs are
appended to JSONS BEFORE any arm referencing them exists.
"""
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent
V = SRC / "verify_s34.py"
C = SRC / "control_s34.py"

V_ANCHOR = '    print(f"\\nverify_s34: {checks[0]} checks, {len(fails)} failures")'

V_BLOCK = '''
    # ---- P152-P154: provenance and the laundering direction --------------
    pv = json.loads((DATA / "provenance-74.json").read_text(encoding="utf-8"))
    ld = json.loads((DATA / "launder-direction.json").read_text(encoding="utf-8"))
    p152 = next(l for l in raw.split("\\r\\n") if l.startswith("| P152 |"))
    p153 = next(l for l in raw.split("\\r\\n") if l.startswith("| P153 |"))
    p154 = next(l for l in raw.split("\\r\\n") if l.startswith("| P154 |"))

    ck(pv["R2"]["overlap"] == [],
       "P152: headline source closure does not touch ship-delta.npy")
    ck(f"**{pv['R1']['arrays']['bee3-leg-luma.npy']['levels_slice']}**" in p152,
       "P152 quotes the luma level count from the artefact")
    ck(f"**{pv['R1']['arrays']['bee3-leg-sel.npy']['levels_slice']}**" in p152,
       "P152 quotes the sel level count from the artefact")
    ck(pv["reader"]["rawpy"] and not pv["reader"]["pil"],
       "P152: m87lib reads via rawpy and contains no Image.open")
    ck(pv["R1"]["arrays"]["bee3-leg-luma.npy"]["levels_slice"] > 256,
       "P152: the level count actually exceeds what 8 bits can hold")

    ck(f"**{pv['R3']['true_max_delta']}**" in p153,
       "P153 quotes the recomputed true delta")
    ck(f"**{pv['R3']['factor']:.1f}x**" in p153,
       "P153 quotes the amplitude factor")
    ck(abs(pv["R3"]["factor"] - 65535.0 / 255.0) < 0.05,
       "P153: the factor really is the 16-to-8 quantisation ratio")
    ck(f"**{100 * pv['R4']['true_changed_frac']:.3f}%**" in p153,
       "P153 quotes the true changed-pixel fraction")
    ck(f"**{pv['R4']['ratio']:.3f}x**" in p153,
       "P153 quotes the changed-fraction ratio")
    ck(pv["R4"]["ratio"] < 1.1,
       "P153: the fraction ratio is small, which is what makes it a retraction")

    ck(f"**{ld['Q1']['ratio']:.4f}x**" in p154, "P154 quotes its own Q1 ratio")
    ck(f"**{ld['registered']['m120_ratio']:.4f}x**" in p154,
       "P154 quotes M120's ratio for comparison")
    ck(ld["Q1"]["ratio"] > 1.0, "P154: Q1 really did find band-pass inflation")
    ck(ld["Q2"]["pass"] is False,
       "P154: Q2 is recorded as FAILED, not quietly dropped")
    ck("FAIL" in p154, "P154 says FAIL in the row")
    ck(abs(ld["Q2"]["v_true"]) < abs(ld["Q2"]["v_laundered"]),
       "P154: the merge veil really did deepen under laundering")
    ck(abs(ld["Q2"]["f0_laundered"]) < abs(ld["Q2"]["f0_true"]),
       "P154: frame 0 really did move toward zero, i.e. the arms disagree")
    ck(f"6.6810%" in p154 and f"7.4718%" in p154,
       "P154 quotes both merge values")
    ck(0.5 * ld["Q3"]["quantum_dn"] / ld["Q2"]["far_dn"] * 100 < 1.0,
       "P154: half a quantum is under 1 pp, the bound the row claims")
    ck(p154.rstrip().rstrip("|").rsplit("|", 1)[-1].strip() == "MEASURED",
       "P154's STATUS CELL is MEASURED")
    ck(p152.rstrip().rstrip("|").rsplit("|", 1)[-1].strip() == "MEASURED",
       "P152's STATUS CELL is MEASURED")

'''

C_JSONS_OLD = '         "110-crosscheck.json"]'
C_JSONS_NEW = ('         "110-crosscheck.json",\n'
               '         "provenance-74.json", "launder-direction.json"]')


def main():
    v = V.read_text(encoding="utf-8")
    if V_ANCHOR not in v:
        sys.exit("VERIFIER ANCHOR NOT FOUND -- refusing to guess")
    if v.count(V_ANCHOR) != 1:
        sys.exit("VERIFIER ANCHOR NOT UNIQUE (%d)" % v.count(V_ANCHOR))
    if "P152-P154" in v:
        sys.exit("already wired -- refusing to double-insert")
    v = v.replace(V_ANCHOR, V_BLOCK + V_ANCHOR, 1)
    V.write_text(v, encoding="utf-8")
    print(f"verify_s34.py: P152-P154 block inserted")

    c = C.read_text(encoding="utf-8")
    if c.count(C_JSONS_OLD) != 1:
        sys.exit("JSONS ANCHOR NOT UNIQUE (%d) -- backups would silently "
                 "not happen" % c.count(C_JSONS_OLD))
    c = c.replace(C_JSONS_OLD, C_JSONS_NEW, 1)
    C.write_text(c, encoding="utf-8")
    print("control_s34.py: provenance-74.json and launder-direction.json "
          "registered for backup")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import io, sys

V = "vh_verify.py"
ANCHOR = 'print("checks run : %d" % checks)'

ADD = '''# --- SECTION 6 partition. It previously read "clean 14 / UNSCORED 8", which
# --- credited halo3's rescues; halo3 FAILED its commission, so it cannot move a
# --- subject out of UNSCORED. Every row below is RE-DERIVED from trunc2.json,
# --- and the withdrawn split carries a negative pin so it cannot drift back.
FLAGGED = ("flat-on-ruler-cpl", "tweezers-cpl", "lavendar-cpl", "119MSDCF")
_full = [k for k, v in tr.items()
         if v["verdict"] != "UNMEASURABLE" and v.get("used", 0) == 7]
ck(len([k for k in _full if k not in FLAGGED]) == 11,
   "clean full-7-band-walk count is no longer 11")
ck(sorted(k for k in _full if k in FLAGGED) == sorted(FLAGGED),
   "the four false positives no longer all walk a full 7 bands")
ck(len([k for k, v in tr.items()
        if v["verdict"] != "UNMEASURABLE" and v.get("used", 0) < 7]) +
   sum(1 for v in tr.values() if v["verdict"] == "UNMEASURABLE") == 11,
   "residual risk re-derived from trunc2.json is no longer 11 subjects")
for anchor, n in (
    ("| clean, full 7-band walk | **11** |", "section 6 clean row"),
    ("| clean but BLIND beyond 32-50 px, not a pass | **4** |", "section 6 blind row"),
    ("| UNMEASURABLE, per-subject reason in section 2 | **7** |", "section 6 unmeasurable row"),
    ("**Residual risk is 11 subjects UNSCORED**", "section 6 residual-risk statement"),
    ("**`halo3` failed its own commission (section 4), so it cannot move any subject\\nout of UNSCORED**",
     "section 6 retraction rationale"),
):
    ck(norm(anchor) in rs, "residual report dropped or altered: %s" % n)
ck(norm("| clean | **14** |") not in rs,
   "the withdrawn 'clean 14' partition row has reappeared")
ck(norm("| UNSCORED, per-subject reason in section 2 | **8** |") not in rs,
   "the withdrawn 'UNSCORED 8' partition row has reappeared")

'''

t = io.open(V, encoding="utf-8").read()
if t.count(ANCHOR) != 1:
    sys.exit("ANCHOR NOT FOUND (%d) -- nothing written" % t.count(ANCHOR))
io.open(V, "w", newline="\n", encoding="utf-8").write(t.replace(ANCHOR, ADD + ANCHOR, 1))
print("added section-6 pins to", V)

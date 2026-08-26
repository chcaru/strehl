"""Their published headline, beside what their own chain reports on data where
the truth is KNOWN and the only difference is the rescale.

If the real-subject pattern is indistinguishable from the zero-blur control
pattern, their chain cannot tell "no difference" from "a rescale".
If it is also indistinguishable from the 0.4 px control, it cannot tell
"no difference" from "a real 0.4 px merge advantage" either.
"""
import json, pathlib
import numpy as np

BT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
STATS = ["S1_norm", "S2_f50", "S3_acf"]


def med(rec):
    return {k: float(np.median([t[f"{k}_blur_px"] for t in rec["tiles"]])) for k in STATS}


def show(title, path, only=None):
    d = json.loads((BT / path).read_text(encoding="utf8"))
    print(f"\n--- {title} ---")
    print(f"{'subject':<24}{'S1_norm':>10}{'S2_f50':>10}{'S3_acf':>10}   sign agreement")
    for r in d:
        if only and r["subject"] not in only:
            continue
        m = med(r)
        sgn = {np.sign(v) for v in m.values() if abs(v) > 1e-9}
        agree = "all agree" if len(sgn) <= 1 else "*** DISAGREE ***"
        print(f"{r['subject']:<24}" + "".join(f"{m[k]:>+10.3f}" for k in STATS) + f"   {agree}")


show("their published headline: six real subjects, real 2-7% rescale",
     "blureq-subjects.json")
show("their own control, both arms on ONE grid (rescale switched off)",
     "blureq-controls.json")
show("V-THESIS control: SAME source subject, truth known, real 6.6% rescale",
     "blureq-vctrl.json")

print("\n=== the comparison that decides it ===")
subj = json.loads((BT / "blureq-subjects.json").read_text(encoding="utf8"))
vc = {r["subject"]: med(r) for r in json.loads((BT / "blureq-vctrl.json").read_text(encoding="utf8"))}
real = np.array([[med(r)[k] for k in STATS] for r in subj])
print(f"real subjects, range over six      S1 [{real[:,0].min():+.3f},{real[:,0].max():+.3f}]  "
      f"S2 [{real[:,1].min():+.3f},{real[:,1].max():+.3f}]  S3 [{real[:,2].min():+.3f},{real[:,2].max():+.3f}]")
for nm, lab in (("VCTRL-s-blur0.0", "TRUTH 0.0 px, rescale only"),
                ("VCTRL-s-blur0.4", "TRUTH +0.4 px merge advantage")):
    m = vc[nm]
    inside = [k for k in STATS if real[:, STATS.index(k)].min() <= m[k] <= real[:, STATS.index(k)].max()]
    print(f"{lab:<34} S1 {m['S1_norm']:+.3f}  S2 {m['S2_f50']:+.3f}  S3 {m['S3_acf']:+.3f}"
          f"   -> lands inside the real-subject range on: {', '.join(inside) if inside else 'none'}")

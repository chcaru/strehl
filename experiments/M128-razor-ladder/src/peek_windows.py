"""List census windows with their gate outcomes, passing ones first.

The early half-width sweeps used a hand-placed ROI. Any claim about whether
the primary reduction works on this subject has to be made on a segment the
census certifies, or it is a claim about ROI placement instead.
"""
import json
import sys

for path in sys.argv[1:]:
    d = json.load(open(path))
    ws = d["windows"]
    npass = sum(1 for w in ws if w["pass"])
    print(f"== {path}")
    print(f"   {d['which']} row0 {d['row0']} nrow {d['nrow']} win {d['win']} "
          f"stride {d['stride']}  ceiling hits {d['n_at_ceiling']}  "
          f"{npass}/{len(ws)} windows pass")
    print(f"   gates: {json.dumps(d['gates'])}")
    hdr = (f"   {'col0':>6} {'ncol':>5} {'yield':>6} {'contr':>7} {'hi':>7} "
           f"{'rms1':>6} {'rms3':>6} {'clipf':>6} {'ang':>7}  pass  fails")
    print(hdr)
    for w in sorted(ws, key=lambda w: (not w["pass"], -w["yield"])):
        print(f"   {w['col0']:6d} {w['ncol']:5d} {w['yield']:6.3f} "
              f"{w['contrast_dn']:7.0f} {w['hi_dn']:7.0f} {w['rms1']:6.3f} "
              f"{w['rms3']:6.3f} {w['clip_frac']:6.3f} {w['angle_deg']:+7.3f}  "
              f"{'Y' if w['pass'] else '.':>4}  {','.join(w['fails'])}")

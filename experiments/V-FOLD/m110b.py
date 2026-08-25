import json
d=json.load(open(r"C:\dev\strehl-out\M110-sheet\ca_overshoot_default_vs_ca.json"))
for subj in d:
    if not isinstance(d[subj],dict): continue
    print("#"*80); print(subj, " keys:", list(d[subj].keys()))
    for key in ("overshoot_real","overshoot_inert_null"):
        if key in d[subj]:
            print("--",key)
            for r in d[subj][key]:
                print("   r %.1f-%.1f n=%-8d flip%%=%-7s grew%%=%-7s over%%=%-7s beyond=%s" % (r["r_lo"],r["r_hi"],r["n"],r["flip_pct"],r["grew_pct"],r["overshoot_pct"],r["beyond_support"]))
    if "width_profile" in d[subj]:
        print("-- width_profile")
        for r in d[subj]["width_profile"]:
            print("   dist=%d n=%-8d off=%-9s on=%-9s delta%%=%s lev8=%s" % (r["dist_px"],r["n"],r["abs_ry_off_dn"],r["abs_ry_on_dn"],r["delta_pct"],r["delta_levels8"]))
    for k,v in d[subj].items():
        if k not in ("overshoot_real","overshoot_inert_null","width_profile"):
            print("--",k,"=",str(v)[:400])

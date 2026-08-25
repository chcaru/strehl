import json
d = json.load(open(r"C:\dev\strehl-out\M113-ca\c10_rings.json"))
def walk(o, path=""):
    if isinstance(o, dict):
        ks = list(o.keys())
        if "eps_sd" in ks:
            r = o.get("rbar", o.get("r", o.get("r_lo","?")))
            print("  %-34s rbar=%-8s eps=%+.6e  eps_sd=%.6e = %6.1f ppm  n=%s"
                  % (path, r, o.get("eps",float("nan")), o["eps_sd"],
                     o["eps_sd"]*1e6, o.get("n","?")))
        for k in ks: walk(o[k], path+"/"+k)
    elif isinstance(o, list):
        for i,v in enumerate(o): walk(v, path+"[%d]"%i)
print("TOP-LEVEL KEYS:", list(d.keys()))
print()
walk(d)

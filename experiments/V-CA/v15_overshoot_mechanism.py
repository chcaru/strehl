import json, numpy as np
d = json.load(open(r"C:\dev\strehl-out\M113-ca\c10_rings.json"))
SHIPPED = -704.5
print("shipped eps_r = %.1f ppm  (optics.rs:319)\n" % SHIPPED)
print("%-18s %10s %10s %12s %12s" % ("subject","off ppm","on ppm","applied ppm","vs shipped"))
for sub in d:
    off = d[sub]["off"]["eps_global"]*1e6
    on  = d[sub]["on"]["eps_global"]*1e6
    applied = on - off                 # correction moves eps by this much
    print("%-18s %+10.1f %+10.1f %12.1f %11.1f%%"
          % (sub, off, on, applied, 100*(applied-abs(SHIPPED))/abs(SHIPPED)))
print()
print("KEY: residual 'on' should be ~0 if the coefficient matches the subject.")
for sub in d:
    off = d[sub]["off"]["eps_global"]*1e6
    on  = d[sub]["on"]["eps_global"]*1e6
    print("  %-18s residual %+7.1f ppm = %5.1f%% of the aberration it started with"
          % (sub, on, 100*on/abs(off)))
print()
print("scene-to-scene spread in the UNCORRECTED aberration:")
offs = [d[s]["off"]["eps_global"]*1e6 for s in d]
print("  %s  ->  spread %.1f%% of the smaller" % (
      ", ".join("%s %+.1f"%(s,d[s]["off"]["eps_global"]*1e6) for s in d),
      100*(max(map(abs,offs))-min(map(abs,offs)))/min(map(abs,offs))))
print()
print("per-ring residual after correction (positive = OVERSHOOT past zero):")
for sub in d:
    rows = d[sub]["on"]["rows"]
    print("  "+sub)
    for r in rows:
        print("    rbar %.3f  n=%4d  residual %+7.1f ppm +/- %.1f"
              % (r["rbar"], r["n"], r["eps"]*1e6, r["eps_sd"]*1e6))

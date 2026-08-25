import math
# RU1: one ROI, one stack. Instrument floor for this ROI:
floor_ru1 = 0.3858970166225601
r_ru1, r_diff = 30.441454828260458, 14.11
print("quadrature subtraction check: sqrt(30.4415^2 - 14.11^2) = %.3f" % math.sqrt(r_ru1**2 - r_diff**2))
tot = 34.78
for name, v in [("optics",r_ru1),("diffraction",r_diff),("aberr",math.sqrt(r_ru1**2-r_diff**2)),
                ("resample",14.97),("overavg",7.61)]:
    print("  %-12s %7.2f um  %5.1f%% of variance" % (name, v, 100*v*v/tot**2))

# Ratio uncertainty, RANDOM error only, propagated from the instrument floor.
# M88 two-aperture: 31.70 (f/5.6) vs a f/11 rise giving ratio 1.025
a = 31.70; b = a*1.025
for s in (floor_ru1, 0.67):
    rel = math.sqrt((s/a)**2 + (s/b)**2)
    u = 1.025*rel
    print("\nfloor %.3f um -> ratio 1.025 +/- %.3f" % (s, u))
    print("   vs 1.000 : %.2f sigma" % (abs(1.025-1.0)/u))
    print("   vs 1.964 : %.2f sigma" % (abs(1.964-1.025)/u))

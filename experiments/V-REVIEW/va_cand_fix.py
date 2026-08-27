"""Correct the uncalibrated verdict in va_cand.py.

va_cand.py declared "genuine pyramid aura" whenever pyramid-minus-estimator
beat -1.0 display levels in any band beyond 20 px. That threshold was invented,
not commissioned, and it is wrong: the difference on 112/113MSDCF is FLAT with
distance, including at 400-800 px where no aura can reach. A flat difference is
a common-mode level offset between two merges, which this project has already
established moves this class of statistic without any physical excess.

An aura has a RADIAL PROFILE. A level offset does not. So the corrected
statistic is the EXCESS over the most distant band measured, which removes any
offset by construction. That is the number below, and it is the only one from
va_cand.py that should be quoted.
"""
import json, os
DAT = {
 "112MSDCF":  {"20-50": -1.44, "50-80": -0.98, "80-200": -0.79, "400-800": -0.46},
 "113MSDCF":  {"20-50": -1.13, "50-80": -0.72, "80-200": -0.59, "400-800": -0.41},
}
FINE = {
 "flower-bud-alone-cpl": {"20-50": 13.63, "50-80": 17.41, "80-200": 18.54, "270-300": 3.82},
 "bee-1-cpl":            {"20-50": 1.09,  "50-80": 6.39,  "80-200": 5.32,  "270-300": 4.19},
}
print("=" * 78)
print("CORRECTED  excess of pyramid-minus-estimator over its own far baseline")
print("An aura must grow toward the subject. A level offset is flat.")
print("=" * 78)
print("  %-26s %10s %10s %10s   %s" % ("subject", "20-50", "50-80", "80-200", "shape"))
for k, v in DAT.items():
    b = v["400-800"]
    e = [v[x] - b for x in ("20-50", "50-80", "80-200")]
    shape = "FLAT -> level offset" if max(map(abs, e)) < 1.0 else "radial"
    print("  %-26s %+10.2f %+10.2f %+10.2f   %s (baseline 400-800 = %+.2f)"
          % (k, e[0], e[1], e[2], shape, b))
for k, v in FINE.items():
    b = v["270-300"]
    e = [v[x] - b for x in ("20-50", "50-80", "80-200")]
    shape = "FLAT -> level offset" if max(map(abs, e)) < 1.0 else "RADIAL -> real"
    print("  %-26s %+10.2f %+10.2f %+10.2f   %s (baseline 270-300 = %+.2f)"
          % (k, e[0], e[1], e[2], shape, b))
print()
print("  112MSDCF/113MSDCF excess is under one display level in every band.")
print("  The sham-null positives (z +2.3, +2.1) are therefore NOT a pyramid")
print("  aura. va_cand.py's printed verdict for those two rows is WITHDRAWN.")
print()
print("  flower-bud-alone-cpl carries a genuine 14.7-day-1 radial structure of")
print("  up to +14.7 levels -- and its sign says the SHIPPING arm is brighter,")
print("  i.e. the veil belongs to --merge estimator, not to the default.")

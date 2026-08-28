import io
p = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-BANDFLOOR\bandmetrics.py"
s = io.open(p, encoding="utf-8").read()
old = '''        print("  %-42s %s" % (name % () if "%%" not in name else name.replace("%%", "%"),
                              "PASS" if ok else "FAIL"))'''
new = '''        print("  %-46s %s" % (name.replace("%%", "%"),
                              "PASS" if ok else "FAIL"))'''
assert old in s
s = s.replace(old, new)
for a, b in (('("IMPROVE  coarse bands 4-5 cut 50%%"', '("IMPROVE  coarse bands 4-5 cut 50%"'),
             ('("DEFECT   coarse modelling cut 30%%"', '("DEFECT   coarse modelling cut 30%"'),
             ('("IMPROVE  coarse modelling boosted 30%%"', '("IMPROVE  coarse modelling boosted 30%"')):
    assert a in s, a
    s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched")

import io
DST = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-TRIAGE\harness_nc.py"
s = io.open(DST, encoding="utf-8").read()
A = "HERE = os.path.dirname(os.path.abspath(__file__))\nsys.path.insert(0, HERE)"
if s.count(A) != 1:
    raise SystemExit("ANCHOR DID NOT LAND (%d matches)" % s.count(A))
B = ("HERE = r\"C:\\dev\\blog\\death-of-software\\projects\\strehl\\experiments\\BUILD-TRIAGE\"\n"
     "sys.path.insert(0, HERE)")
s2 = s.replace(A, B, 1)
if s2 == s:
    raise SystemExit("PATCH DID NOT APPLY")
io.open(DST, "w", encoding="utf-8").write(s2)
print("patched HERE -> BUILD-TRIAGE dir")

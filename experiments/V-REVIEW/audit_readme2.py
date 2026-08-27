import re, io, pathlib, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
R = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution\README.md")
L = R.read_text("utf8","replace").split("\n")
def sect(i):
    for j in range(i,-1,-1):
        if L[j].lstrip().startswith("#"): return L[j].strip()[:76]
    return "(no heading)"
print("CALIBRATION: wider context (+/-6 lines and the enclosing heading) for flagged ratio lines")
for n in (169,366,52,133):
    i=n-1
    print("\n" + "="*96)
    print("L%d   heading: %s" % (n, sect(i)))
    print("-"*96)
    for k in range(max(0,i-6), min(len(L), i+7)):
        mark = ">>" if k==i else "  "
        print("  %s L%-4d %s" % (mark, k+1, L[k].rstrip()[:100]))

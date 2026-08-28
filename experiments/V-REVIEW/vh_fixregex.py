import io, sys
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\vh_verify.py"
t = io.open(P, encoding="utf-8").read()
bad = 'r"leaf-2-cpl`` is \\*\\*acquitted of halo"'
good = 'r"leaf-2-cpl` is \\*\\*acquitted of halo"'
if t.count(bad) != 1:
    sys.exit("ANCHOR NOT FOUND (%d) -- refusing to patch" % t.count(bad))
io.open(P, "w", newline="\n", encoding="utf-8").write(t.replace(bad, good, 1))
print("fixed backtick count in leaf-2 acquittal regex")

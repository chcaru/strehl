import subprocess, io, os
D = r"C:\dev\blog\death-of-software\projects\strehl"
OUT = os.path.join(D, "experiments", "V-NEVERWORSE", "pin9b05")
for f in ["softgate.rs", "merge.rs", "focus.rs", "through_focus.rs", "noise.rs"]:
    r = subprocess.run(["git", "show", "9b05d0b7:crates/strehl-core/src/" + f],
                       cwd=D, capture_output=True)
    assert r.returncode == 0, (f, r.stderr[:200])
    p = os.path.join(OUT, f)
    open(p, "wb").write(r.stdout)
    print("%-20s %8d bytes" % (f, len(r.stdout)))

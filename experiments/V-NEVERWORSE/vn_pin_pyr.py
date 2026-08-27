import subprocess, os
D = r"C:\dev\blog\death-of-software\projects\strehl"
OUT = os.path.join(D, "experiments", "V-NEVERWORSE", "pin9b05")
r = subprocess.run(["git","show","9b05d0b7:crates/strehl-core/src/pyramid.rs"],cwd=D,capture_output=True)
assert r.returncode==0
open(os.path.join(OUT,"pyramid.rs"),"wb").write(r.stdout)
print("pyramid.rs", len(r.stdout), "bytes")

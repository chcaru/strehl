import hashlib, os, subprocess
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\flat-fields\subject-focus-sweep-with-cpl"
dst = r"C:\dev\strehl-out\V-BANDFLOOR\paper\srgb__NULL.tiff"
env = dict(os.environ); env["STREHL_GATE_FLOOR_SCALE"] = "1,1,1,1,1,1,1"
p = subprocess.run([EXE, "stack", SRC, "-o", dst, "--srgb"], capture_output=True, text=True, env=env)
print("rc", p.returncode)
for l in (p.stdout + p.stderr).splitlines():
    if l.strip().startswith("averaged"):
        print("  null arm:", l.split(":", 1)[1].strip()[:44])
ref = r"C:\dev\strehl-out\V-BANDFLOOR\paper\srgb__A-unset.tiff"
h1 = hashlib.sha256(open(ref, "rb").read()).hexdigest().upper()
h2 = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
print("  unset          ", h1)
print("  1,1,1,1,1,1,1  ", h2)
print("  BYTE-IDENTICAL:", h1 == h2)

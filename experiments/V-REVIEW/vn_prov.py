"""Provenance audit of the four published cells. No re-measurement."""
import os, glob, hashlib, re

CELLS = {
 "strehl (denominator, all four cells)": [
   r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff",
   r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff"],
 "enfuse (cells 1-2)": [
   r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif",
   r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif"],
 "focus-stack (cells 3-4)": [
   r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif",
   r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif"],
 "tile census (tile selection only)": [
   r"C:\dev\strehl-out\V-NOISE\census.npz"],
}
print("=" * 78)
print("1. EXACT INPUTS OF THE FOUR PUBLISHED CELLS")
print("=" * 78)
for role, fs in CELLS.items():
    print("  " + role)
    for f in fs:
        e = os.path.isfile(f)
        print("    %-58s %s %10d bytes" % (f, "EXISTS" if e else "MISSING",
                                           os.path.getsize(f) if e else -1))
        for suf in (".ok", ".provenance.txt"):
            for cand in (f + suf, os.path.splitext(f)[0] + suf):
                if os.path.isfile(cand):
                    print("        seal %-12s -> %s" % (suf,
                          open(cand, encoding="utf-8", errors="replace").read().strip()[:120]))
    print()

print("=" * 78)
print("2. DO ANY OF MY vn_*.py SCRIPTS INVOKE A BINARY AT ALL?")
print("=" * 78)
D = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW"
pat = re.compile(r"subprocess|\.exe|strehl-pinned|066A87|vr_lib|os\.system|Popen")
for f in sorted(glob.glob(os.path.join(D, "vn_*.py"))):
    src = open(f, encoding="utf-8", errors="replace").read()
    hits = sorted(set(m.group(0) for m in pat.finditer(src)))
    print("  %-16s %s" % (os.path.basename(f), hits if hits else "no binary invocation"))

print()
print("=" * 78)
print("3. WHAT IS 066A87AB, AND WHAT DID IT PRODUCE IN MY LANE?")
print("=" * 78)
b = r"C:\dev\strehl-out\V-REVIEW\bin"
if os.path.isdir(b):
    for f in sorted(glob.glob(os.path.join(b, "*"))):
        h = hashlib.sha256(open(f, "rb").read()).hexdigest().upper()
        print("  %-46s %10d  %s" % (f, os.path.getsize(f), h[:16]))
print()
for sub in ("geom", "halo2", "noise", "aura", "crops"):
    d = os.path.join(r"C:\dev\strehl-out\V-REVIEW", sub)
    if not os.path.isdir(d): continue
    fs = glob.glob(os.path.join(d, "**", "*"), recursive=True)
    im = [f for f in fs if f.lower().endswith((".tif", ".tiff", ".png"))]
    ok = [f for f in fs if f.endswith(".ok")]
    print("  %-8s %3d images %3d seals" % (sub, len(im), len(ok)))
    for o in sorted(ok)[:3]:
        print("      %s -> %s" % (os.path.basename(o),
              open(o, encoding="utf-8", errors="replace").read().strip()[:20]))

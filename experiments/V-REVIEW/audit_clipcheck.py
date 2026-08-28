"""Was the overshoot measurement contaminated by highlight clipping?

ORCH's 2026-08-27 broadcast: --auto-exposure at HEAD blows highlights, and a
saturated region has no structure, so clipping can manufacture findings. My
renders never passed --auto-exposure (arm 3), but my +8.2707% overshoot was
measured on a +1-stop render that may sit in the highlight roll-off anyway.
Measure the clip fraction of the exact renders the claim was built on.
"""
import subprocess, pathlib, os, sys
import numpy as np, tifffile

EXE = r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB = r"D:\personal\macro\109MSDCF"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\clip")
OUT.mkdir(parents=True, exist_ok=True)
FULL = 65535

def render(tag, extra):
    o = OUT / (tag + ".tiff")
    if o.exists():
        o.unlink()
    r = subprocess.run([EXE, "stack", SUB, "--out", str(o), "--limit", "4",
                        "--srgb", "--merge", "pyramid"] + extra, capture_output=True)
    if r.returncode != 0 or not o.exists():
        print(f"  RENDER FAILED {tag}: {r.stderr.decode('utf-8','replace')[-300:]}")
        return None
    return o

print("arm       flags                        %clipped   median   %>90%ceil")
rows = {}
for tag, extra in [("noauto", []), ("e0", ["--exposure", "0"]),
                   ("e1", ["--exposure", "1"]), ("em1", ["--exposure", "-1"]),
                   ("auto", ["--auto-exposure"])]:
    p = render(tag, extra)
    if p is None:
        continue
    a = tifffile.imread(str(p))
    clip = float((a >= FULL).mean() * 100.0)
    near = float((a >= 0.9 * FULL).mean() * 100.0)
    med = float(np.median(a))
    rows[tag] = (clip, med, near)
    print(f"{tag:9s} {' '.join(extra) or '(none)':28s} {clip:8.4f} {med:8.0f} {near:9.2f}")
    os.remove(p)

print()
if "auto" in rows and "noauto" in rows:
    print(f"ORCH's regression reproduced?  auto={rows['auto'][0]:.2f}% clipped "
          f"vs noauto={rows['noauto'][0]:.2f}%  -> "
          f"{'YES' if rows['auto'][0] > 25 else 'NO'}")
if "e1" in rows:
    print(f"My overshoot's bright endpoint (--exposure 1): {rows['e1'][0]:.4f}% clipped, "
          f"{rows['e1'][2]:.2f}% above 90% of ceiling")

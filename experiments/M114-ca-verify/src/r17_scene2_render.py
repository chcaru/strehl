"""M114 r17: render off/on for TWO scenes on ONE binary at HEAD.

ORCH's gain of 1.444 is from one scene AND one estimator. Comparing my scene-2
number against ORCH's scene-1 number would confound scene with instrument, so I
render BOTH scenes here and measure BOTH with my own estimator in r18.

Both scenes share the identical optical train (Sony A7C II + FE 100mm F2.8 Macro
GM + 2X Teleconverter, read from EXIF) and the identical aperture f/5.6, so the
only variable between them is the subject.

  scene 1  bee-3-cpl   299 frames  f/5.6 ISO 100   (in-sample for the fit)
  scene 2  119MSDCF     33 frames  f/5.6 ISO  50   (HELD OUT of the fit)

Exit codes come from subprocess.run().returncode.
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\target-s2\release\strehl.exe")
OUT = Path(r"C:\dev\strehl-out\M114-ca-verify\r17")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
R1_OFF = "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"
R1_ON = "E9580E8A2A85009494B2FE5A35441EBE5D5F9F7E6B80ADBD079B40130B7742E9"
SCENES = [("bee-3-cpl", r"D:\personal\macro\bee-3-cpl"),
          ("119MSDCF", r"D:\personal\macro\119MSDCF")]
OUT.mkdir(parents=True, exist_ok=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest().upper()

def run(args, env_extra):
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env.update(env_extra)
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, time.time() - t0, p.stdout + p.stderr

res = {}
for name, d in SCENES:
    side = OUT / (name + "-warpmap.txt")
    if not side.exists():
        code, sec, out = run([str(EXE), "align", d, "--out", str(side)], {})
        print("%-10s align exit=%d %.1fs" % (name, code, sec), flush=True)
        if code != 0:
            print(out[-2500:]); sys.exit("ALIGN FAILED " + name)
    res[name] = {}
    for arm, val in [("off", "0"), ("on", KEY)]:
        tif = OUT / ("%s-%s.tif" % (name, arm))
        code, sec, out = run([str(EXE), "stack", d, "--srgb", "--auto-exposure",
                              "-o", str(tif)],
                             {"STREHL_WARPMAP": str(side), "STREHL_FIX_CA": val})
        if code != 0:
            print(out[-2500:]); sys.exit("RENDER FAILED %s %s" % (name, arm))
        res[name][arm] = sha(tif)
        print("%-10s %-3s exit=%d %5.1fs  %s" % (name, arm, code, sec, res[name][arm]), flush=True)

# Informational: HEAD has moved far since r1 (M97 merge work landed), so a
# mismatch here is NOT a defect -- it just means scene 1 had to be re-rendered,
# which is exactly why this script renders it rather than reusing r1.
print("\nHEAD binary reproduces r1 off hash : %s" % (res["bee-3-cpl"]["off"] == R1_OFF))
print("HEAD binary reproduces r1 on  hash : %s" % (res["bee-3-cpl"]["on"] == R1_ON))
for n in res:
    print("%-10s off != on : %s" % (n, res[n]["off"] != res[n]["on"]))
(OUT / "r17.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

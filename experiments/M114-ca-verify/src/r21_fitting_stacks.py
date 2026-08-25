"""M114 r21: measure the gain on the stacks the coefficient was FITTED on.

ORCH's H1 vs H2. Provenance at optics.rs:309 reads
"M107 Instrument A: 20 gated ROIs over tweezers-cpl and bee-3-cpl", so BOTH
fitting stacks are named. bee-3-cpl was already measured in r17-r20 (gain 1.241);
this adds tweezers-cpl so the verdict rests on both, plus 119MSDCF as the
held-out control already in hand.

  H1 coefficient error   -> gain ~1.44 on the fitting stacks, flat
  H2 applicability error -> gain ~1.0 on the fitting stacks, wrong elsewhere
  H3 application bug     -> applied/declared != 1 and SCENE-INDEPENDENT, while
                            the fitted coefficient tracks native CA on all stacks

H3 is ORCH's third possibility and it is separable from H1/H2 because it splits
the gain into two independently measurable factors:

    gain = (applied / declared) x (declared_slope / native_slope)
             \___ application ___/   \______ fit quality ______/

LOGGING. ORCH could not tell which stack r1 rendered because r1.log did not
record its input. Every arm below logs its absolute input path.
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\target-s3\release\strehl.exe")
OUT = Path(r"C:\dev\strehl-out\M114-ca-verify\r21")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
SCENES = [("tweezers-cpl", r"D:\personal\macro\tweezers-cpl", "FITTING STACK"),
          ("bee-3-cpl", r"D:\personal\macro\bee-3-cpl", "FITTING STACK")]
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "r21.log"

def log(m):
    print(m, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(m + "\n")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest().upper()

def run(args, extra):
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env.update(extra)
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, time.time() - t0, p.stdout + p.stderr

log("binary %s" % EXE)
res = {}
for name, d, role in SCENES:
    nf = len(list(Path(d).glob("*.ARW")))
    log("SCENE %s  role=%s  INPUT=%s  frames=%d" % (name, role, d, nf))
    side = OUT / (name + "-warpmap.txt")
    if not side.exists():
        code, sec, out = run([str(EXE), "align", d, "--out", str(side)], {})
        log("  align INPUT=%s exit=%d %.1fs" % (d, code, sec))
        if code != 0:
            log(out[-2500:]); sys.exit("ALIGN FAILED " + name)
    res[name] = {}
    for arm, val in [("off", "0"), ("on", KEY)]:
        tif = OUT / ("%s-%s.tif" % (name, arm))
        code, sec, out = run([str(EXE), "stack", d, "--srgb", "--auto-exposure", "-o", str(tif)],
                             {"STREHL_WARPMAP": str(side), "STREHL_FIX_CA": val})
        if code != 0:
            log(out[-2500:]); sys.exit("RENDER FAILED %s %s" % (name, arm))
        res[name][arm] = sha(tif)
        log("  arm=%-3s INPUT=%s STREHL_FIX_CA=%r exit=%d %.1fs OUT=%s SHA=%s"
            % (arm, d, val, code, sec, tif.name, res[name][arm]))
    log("  off != on : %s" % (res[name]["off"] != res[name]["on"]))
(OUT / "r21_hashes.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

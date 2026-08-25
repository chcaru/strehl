"""M113-ca: render LINEAR camera-native arms.

M114's off.tif/on.tif -- the files ORCH measured the CA gain on -- were rendered
with `--srgb --auto-exposure`. The CLI's own help says of --srgb: "For looking
at, NOT for measuring", and the reason is decisive for a CHANNEL-GEOMETRY
measurement: --srgb applies the camera COLOUR MATRIX, which forms each output
channel as a linear combination of all three camera channels. Output red then
contains a large fraction of camera green AT ZERO DISPLACEMENT, which is exactly
the contaminant that pins a correlation-based estimator to zero lag.

This renders the byte-frozen LINEAR camera-native path instead (--demosaic, no
--srgb, no exposure), where R is R and G is G.

Also renders a SECOND STACK that is not one of the two M107 fitted the
coefficient on (tweezers-cpl and bee-3-cpl), so the scalar's transferability can
be tested rather than assumed.

Exit codes come from subprocess.run().returncode, which has none of the stale
$LASTEXITCODE behaviour of fact 1507.
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
OUT = Path(r"C:\dev\strehl-out\M113-ca\lin")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
BEE_SIDE = Path(r"C:\dev\strehl-out\M114-ca-verify\r1\m114-warpmap.txt")

# Second stack must NOT be one of the two M107 fitted the coefficient on
# (tweezers-cpl, bee-3-cpl), or it cannot test transfer. Candidates are tried in
# order and a stack that `align` REFUSES is skipped, not overridden:
# highly-angled-ruler-mm-cpl is rejected with "its subject is not normal to the
# optical axis", which is correct and --force-tilted would be measuring a
# knowingly-wrong sidecar.
STACKS = [
    ("bee-3-cpl", Path(r"D:\personal\macro\bee-3-cpl"), BEE_SIDE),
    ("couch-fibers-cpl", Path(r"D:\personal\macro\couch-fibers-cpl"), None),
]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

def run(args, extra):
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env["STREHL_CACHE_DIR"] = r"C:\dev\strehl-out\M113-ca\cache"
    env.update(extra)
    t = time.time()
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, time.time() - t, (p.stdout or "") + (p.stderr or "")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    Path(r"C:\dev\strehl-out\M113-ca\cache").mkdir(parents=True, exist_ok=True)
    log = []
    def say(s):
        print(s, flush=True); log.append(s)

    say("binary sha256 = %s" % sha(EXE))
    results = {}
    for name, d, side in STACKS:
        if not d.exists():
            say("%-10s MISSING %s" % (name, d)); continue
        n = len(list(d.glob("*.ARW")))
        ref = n // 2
        say("\n%s: %d frames, reference %d" % (name, n, ref))
        if side is None:
            side = OUT / ("%s-warpmap.txt" % name)
            if not side.exists():
                code, sec, out = run([str(EXE), "align", str(d), "--out", str(side),
                                      "--reference", str(ref)], {})
                say("  align EXIT=%d  %.1fs" % (code, sec))
                if code != 0:
                    say("  ALIGN REFUSED -- skipping this stack, not overriding:")
                    say("  " + (out.strip().splitlines() or ["(no message)"])[-1])
                    side.unlink(missing_ok=True)
                    continue
            else:
                say("  align: reusing existing sidecar")
        else:
            say("  align: reusing M114 sidecar %s" % side.name)
        for arm, val in (("off", None), ("on", KEY)):
            tif = OUT / ("%s-%s.tif" % (name, arm))
            if tif.exists():
                say("  %-4s exists, sha %s" % (arm, sha(tif)[:16])); results["%s_%s" % (name, arm)] = sha(tif); continue
            extra = {"STREHL_WARPMAP": str(side)}
            if val is not None:
                extra["STREHL_FIX_CA"] = val
            code, sec, out = run([str(EXE), "stack", str(d), "--demosaic",
                                  "-o", str(tif)], extra)
            say("  %-4s CA=%-26r EXIT=%d  %.1fs" % (arm, val, code, sec))
            if code != 0:
                say(out[-2000:]); sys.exit("STACK FAILED %s %s" % (name, arm))
            h = sha(tif)
            results["%s_%s" % (name, arm)] = h
            say("       sha256 %s" % h)
    say("")
    for name, _, _ in STACKS:
        a = results.get("%s_off" % name); b = results.get("%s_on" % name)
        if a and b:
            say("%-10s off!=on : %s" % (name, "PASS" if a != b else "FAIL -- ARMS IDENTICAL"))
    (OUT / "render.log").write_text("\n".join(log), encoding="utf-8")
    with open(OUT / "render.json", "w") as fh:
        json.dump(results, fh, indent=2)
    say("\nwrote render.json")

if __name__ == "__main__":
    main()
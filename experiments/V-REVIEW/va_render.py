"""Render the aura arms on the SHIPPING pin, sealed, with a byte-exact control.

Pin is DERIVED from the SHIP-V4 seal via the hardened vr_lib guard, not declared.

ARM P  --merge pyramid    the shipping default; must reproduce the master EXACTLY
ARM E  --merge estimator  the pre-switch default
ARM S  --limit 1          one frame, no merge at all: the reference for what the
                          background looks like before any merge touches it

Same --exposure for every arm, taken from the master's own provenance, so the
three land in one photometric space by construction rather than by hope.
"""
import os, sys, subprocess, hashlib, json
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
import vr_lib as V

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
SUBJ = "flower-bud-alone-cpl"
EXPO = "1.44"
os.makedirs(OUT, exist_ok=True)

seal, n = V.corpus_seal(ACC, "SHIP-V4")
EXE, PIN = V.pin_for(seal)
print("pin DERIVED from %d sealed masters: %s" % (n, PIN))
print("exe %s" % EXE)
print("hash verified against seal: %s" % (V._sha256(EXE) == seal))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def render(tag, extra):
    out = os.path.join(OUT, "%s--%s.tiff" % (SUBJ, tag))
    if os.path.exists(out):
        print("  %-10s cached" % tag)
        return out
    env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}
    cmd = [EXE, "stack", os.path.join(r"D:\personal\macro", SUBJ),
           "--out", out, "--srgb", "--exposure=%s" % EXPO] + extra
    print("  %-10s rendering..." % tag, flush=True)
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=3600)
    if p.returncode != 0:
        print(p.stderr.decode("utf-8", "replace")[-1500:])
        raise SystemExit("render %s failed rc=%d" % (tag, p.returncode))
    with open(out + ".ok", "w") as f:
        f.write(V._sha256(EXE))
    with open(out + ".provenance.txt", "w") as f:
        f.write("binary  %s\npin     %s\nsha256  %s\n" % (EXE, PIN, V._sha256(EXE)))
        f.write("corpus  SHIP-V4 seal %s\n" % seal)
        f.write("argv    %s\n" % " ".join(cmd))
        f.write("STREHL_* : all cleared\n")
    print("  %-10s done" % tag)
    return out


arms = {}
arms["pyramid"] = render("pyramid", ["--merge", "pyramid"])
arms["estimator"] = render("estimator", ["--merge", "estimator"])
arms["single"] = render("single", ["--limit", "1"])

print()
print("=" * 78)
print("CONTROL: does ARM P reproduce the shipped master byte for byte?")
print("=" * 78)
master = os.path.join(ACC, "%s--SHIP-V4.tiff" % SUBJ)
hm, hp = sha(master), sha(arms["pyramid"])
print("  master   %s" % hm)
print("  arm P    %s" % hp)
print("  IDENTICAL: %s" % (hm == hp))
if hm != hp:
    print("  -> my render pipeline does NOT match the shipped one; every")
    print("     downstream number is suspect until this is explained.")
else:
    print("  -> the shipping pipeline is reproduced exactly. Arm E and Arm S")
    print("     differ from the master ONLY by the switch named.")
json.dump({k: sha(v) for k, v in arms.items()},
          open(os.path.join(OUT, "arm_hashes.json"), "w"), indent=1)
for k, v in arms.items():
    print("  %-10s %s" % (k, os.path.basename(v)))

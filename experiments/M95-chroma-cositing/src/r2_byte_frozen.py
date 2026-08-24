"""R2 — prove the byte-frozen measurement path is untouched, then render
before/after on the sRGB path.

THE BYTE-FROZEN PROOF
---------------------
`merge_cmd.rs` sets the colour matrix only under `--srgb`, and both callers
reach `write_binned` only inside `if let Some(m) = matrix`. So the default
linear path cannot enter the corrected code. That is an argument from reading
the source, and an argument is not a measurement: this re-renders the corpus's
own default-path file with the NEW binary and compares SHA-256 against the file
the PINNED binary wrote. Equal bytes is the claim; anything else means a corpus
number moved tonight.

The positive control matters as much. If the two binaries produced identical
bytes on the `--srgb` path as well, the comparison would prove only that I ran
the same binary twice. So the same pair is also rendered WITH `--srgb`, where
the bytes must DIFFER.
"""

import hashlib
import os
import subprocess
import sys
import time

PIN = r"C:\dev\strehl-out\M95-pin\target\release\strehl.exe"
NEW = r"C:\dev\blog\death-of-software\projects\strehl\target-m95\release\strehl.exe"
STACK = r"D:\personal\macro\bee-3-cpl"
OUT = r"C:\dev\strehl-out\M95-chroma-cositing"
ARM1 = r"C:\dev\strehl-out\M93-out\armM-gate0-binlin.tif"

os.makedirs(OUT, exist_ok=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def render(binary, out, srgb, gate="0", align="0"):
    if os.path.exists(out):
        print("  cached: %s" % os.path.basename(out))
        return out
    args = [binary, "stack", STACK, "-o", out, "--gate", gate]
    if srgb:
        args.append("--srgb")
    env = dict(os.environ)
    env["STREHL_ALIGN"] = align
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(r.stdout[-4000:])
        print(r.stderr[-4000:])
        raise SystemExit("render failed: %s" % " ".join(args))
    print("  rendered %s in %.0fs" % (os.path.basename(out), time.time() - t0))
    with open(out + ".log", "w", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)
    return out


def main():
    print("== byte-frozen measurement path: default (no --srgb) ==")
    new_lin = render(NEW, os.path.join(OUT, "new-gate0-binlin.tif"), srgb=False)
    a, b = sha256(ARM1), sha256(new_lin)
    print("  pinned binary (arm 1) : %s" % a)
    print("  new binary            : %s" % b)
    frozen_ok = a == b
    print("  BYTE-FROZEN: %s" % ("PASS - identical" if frozen_ok else "FAIL - BYTES MOVED"))

    print("\n== positive control: the --srgb path MUST differ between binaries ==")
    old_srgb = render(PIN, os.path.join(OUT, "before-srgb.tif"), srgb=True)
    new_srgb = render(NEW, os.path.join(OUT, "after-srgb.tif"), srgb=True)
    c, d = sha256(old_srgb), sha256(new_srgb)
    print("  pinned binary --srgb  : %s" % c)
    print("  new binary   --srgb   : %s" % d)
    differ_ok = c != d
    print("  POSITIVE CONTROL: %s"
          % ("PASS - they differ, so the comparison above has power"
             if differ_ok else "FAIL - identical, the test proves nothing"))

    ok = frozen_ok and differ_ok
    print("\nR2: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

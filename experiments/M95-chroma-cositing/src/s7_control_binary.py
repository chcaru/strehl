"""S7 — rebuild the "before" from the SAME tree, because N2 failed.

WHY THIS EXISTS
---------------
S6 compared the pinned binary (build 1f17c1d5) against the new one and its N2
control failed: green was not bit-identical between the two renders, even though
the co-siting fix does not touch green. The diagnosis is that the pin predates
other agents' work in this tree -- M86 is live in `align.rs` -- and the shipped
configuration has alignment ON. So "before" and "after" differed by my change
AND by somebody else's alignment change, and every number in that column was
contaminated. N2 was the control that caught it.

The correct control is a binary built from the CURRENT tree with only the
co-siting disabled. `COSITE_SHIFT = 0.0` does exactly that, because Keys at
t = 0 is the weight vector [0, 1, 0, 0] and `0*a + 1*b + 0*c + 0*d == b`
exactly in f32. That is an argument, so it is checked rather than assumed:

  C12  the zero-shift binary must reproduce the PINNED binary's --srgb output
       byte for byte at STREHL_ALIGN=0, where the alignment difference cannot
       express itself. Equal bytes proves two things at once -- that
       COSITE_SHIFT = 0 is exactly the old arithmetic, and that on that path my
       edit is the only difference between the pin and HEAD.
"""

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")
TGT = ROOT / "crates" / "strehl-cli" / "src" / "image_out.rs"
OUT = pathlib.Path(r"C:\dev\strehl-out\M95-chroma-cositing")
CARGO = os.path.join(os.path.expanduser("~"), ".cargo", "bin", "cargo.exe")
REL = ROOT / "target-m95" / "release" / "strehl.exe"
NOCOSITE = OUT / "strehl-nocosite.exe"
STACK = r"D:\personal\macro\bee-3-cpl"

ENV = dict(os.environ)
ENV["CARGO_TARGET_DIR"] = str(ROOT / "target-m95")

ANCHOR = "const COSITE_SHIFT: f32 = 0.25;\n"
DISABLED = "const COSITE_SHIFT: f32 = 0.0;\n"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    t = time.time() + 1
    os.utime(path, (t, t))


def build():
    r = subprocess.run([CARGO, "build", "--release", "-p", "strehl-cli"],
                       cwd=ROOT, env=ENV, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("build failed")


def render(binary, out, args, align=None):
    if os.path.exists(out):
        print("   cached: %s" % os.path.basename(out))
        return
    env = dict(os.environ)
    if align is not None:
        env["STREHL_ALIGN"] = align
    else:
        env.pop("STREHL_ALIGN", None)
    cmd = [str(binary), "stack", STACK, "-o", str(out)] + args
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("render failed: %s" % " ".join(cmd))
    print("   rendered %s in %.0fs" % (os.path.basename(out), time.time() - t0))


def main():
    original = TGT.open("r", encoding="utf-8", newline="").read()
    backup = pathlib.Path(tempfile.gettempdir()) / "M95-image_out-FIXED.rs"
    shutil.copyfile(TGT, backup)
    orig_sha = sha256(TGT)
    print("fixed source backed up to %s (sha %s)" % (backup, orig_sha[:16]))
    assert original.count(ANCHOR) == 1, "COSITE_SHIFT anchor not unique"

    try:
        print("\n== building the zero-shift control binary from the SAME tree ==")
        write(TGT, original.replace(ANCHOR, DISABLED, 1))
        build()
        shutil.copyfile(REL, NOCOSITE)
        print("   wrote %s" % NOCOSITE)
    finally:
        write(TGT, original)
        assert sha256(TGT) == orig_sha, "restore did not reproduce the fixed source"
    print("   source restored, sha matches")

    print("\n== rebuilding the shipping binary ==")
    build()

    print("\n== C12: zero-shift binary vs the PIN, at STREHL_ALIGN=0 ==")
    render(NOCOSITE, OUT / "c12-nocosite-srgb.tif",
           ["--gate", "0", "--srgb"], align="0")
    a = sha256(OUT / "before-srgb.tif")       # pinned binary, same args
    b = sha256(OUT / "c12-nocosite-srgb.tif")
    print("   pinned binary        : %s" % a)
    print("   zero-shift, this tree: %s" % b)
    c12 = a == b
    if c12:
        print("   C12: PASS - identical, so COSITE_SHIFT=0 IS the old arithmetic")
    else:
        print("   C12: FAIL - they differ, so the tree changed elsewhere on this path too")

    print("\n== rendering the shipped configuration with the control binary ==")
    render(NOCOSITE, OUT / "ship-before-Z.tif", ["--gate", "2.0", "--srgb"])

    print("\n== N2 re-run: green between ship-before-Z and ship-after ==")
    import numpy as np
    import tifffile
    z = tifffile.imread(OUT / "ship-before-Z.tif")
    y = tifffile.imread(OUT / "ship-after.tif")
    same = np.array_equal(z[:, :, 1], y[:, :, 1])
    dr = int(np.abs(z[:, :, 0].astype(int) - y[:, :, 0].astype(int)).max())
    db = int(np.abs(z[:, :, 2].astype(int) - y[:, :, 2].astype(int)).max())
    print("   green bit-identical : %s" % same)
    print("   max |dR| %d DN, max |dB| %d DN" % (dr, db))
    n2 = bool(same) and dr > 0 and db > 0
    print("   N2-shipped: %s" % ("PASS" if n2 else "FAIL"))

    ok = c12 and n2
    print("\nS7: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

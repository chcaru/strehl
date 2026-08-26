"""Attribute the coffee-bean-20-gate2-sidecar freeze move by ISOLATING THE VARIABLE.

BUILD-HALO established the standard for this file at 2525e08 and it is the right
one: pinning a parent commit can only show the bytes differ ACROSS a boundary,
and cannot separate my change from anything else in the same range. Re-rendering
the row's OWN recorded invocation with my variable forced off is strictly
stronger -- if it reproduces the previous baseline bit-exactly then the whole
delta is mine, and every other commit in the range is cleared of touching these
bytes as a side effect.

Two arms, one pinned binary, the row's own recorded command:

  fixca-off  STREHL_FIX_CA=off  -> must equal the PREVIOUS baseline
  default    STREHL_FIX_CA unset -> must equal the NEW hash

Both must hold. "off reproduces the old bytes" alone would be satisfied by a
build that ignored the flag entirely and never moved anything; pairing it with
"default reproduces the new bytes" pins down that the flag is the only mover.
"""

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

PIN = pathlib.Path(r"C:\dev\strehl-out\BUILD-RENDER-pin-96571ee")
EXE = PIN / "target" / "release" / "strehl.exe"
WARPMAP = PIN / "crates" / "strehl-cli" / "tests" / "data" / "coffee-bean-20.warpmap.txt"
SUBJECT = r"D:\personal\macro\coffee-bean"

PREV = "6325922C11DE23A1B73FFEF69C6E2FEE6BD628FF4275C87DA5797669C4227D8F"
NEW = "88154E2D59A7288304A6B6967960183F6EB1D538FF5D4649F059206AEECA461E"

# Exactly the list the test clears, so this render differs from the test's only
# in STREHL_FIX_CA -- which is the variable under study and, as it happens, the
# one the test forgot.
RENDER_ENV = [
    "STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
    "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU", "STREHL_EDGE_CONF",
    "STREHL_ONLY_FRAME", "STREHL_MERGE", "STREHL_PYRAMID_WORKERS",
    "STREHL_VEIL", "STREHL_VEIL_MARGIN", "STREHL_VEIL_FLOOR",
    "STREHL_FIX_CA",
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def arm(name, fix_ca):
    env = dict(os.environ)
    for k in RENDER_ENV:
        env.pop(k, None)
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"br-attrib-{name}-"))
    env["STREHL_WARPMAP"] = str(WARPMAP)
    env["STREHL_CACHE_DIR"] = str(scratch / "cache")
    if fix_ca is not None:
        env["STREHL_FIX_CA"] = fix_ca
    out = scratch / "render.tif"
    cmd = [str(EXE), "stack", SUBJECT, "--merge", "estimator",
           "--limit", "20", "--gate", "2.0", "--out", str(out)]
    r = subprocess.run(cmd, env=env, capture_output=True)
    assert r.returncode == 0, f"{name} exited {r.returncode}\n{r.stderr.decode(errors='replace')[-2000:]}"
    h, n = sha256(out), out.stat().st_size
    shutil.rmtree(scratch, ignore_errors=True)
    return h, n


def main():
    assert EXE.is_file(), f"missing pinned binary {EXE}"
    assert WARPMAP.is_file(), f"missing warpmap {WARPMAP}"
    print(f"binary  : {EXE}")
    print(f"sha256  : {sha256(EXE)[:32]}")
    print(f"warpmap : {WARPMAP.name}\n")

    off_h, off_n = arm("fixca-off", "off")
    def_h, def_n = arm("default", None)

    print(f'{"arm":<12}{"bytes":>12}  sha256')
    print(f'{"fixca-off":<12}{off_n:>12}  {off_h}')
    print(f'{"default":<12}{def_n:>12}  {def_h}')
    print()
    print(f'{"PREV baseline":<12}{"":>12}  {PREV}')
    print(f'{"NEW  actual":<12}{"":>12}  {NEW}')
    print()

    checks = [
        ("STREHL_FIX_CA=off reproduces the PREVIOUS baseline bit-exactly", off_h == PREV),
        ("default reproduces the NEW hash bit-exactly", def_h == NEW),
        ("the two arms differ (the flag is not inert)", off_h != def_h),
        ("geometry unchanged (only pixel VALUES moved)", off_n == def_n),
    ]
    bad = 0
    for label, ok in checks:
        print(f'  [{"PASS" if ok else "FAIL"}] {label}')
        if not ok:
            bad += 1
    print()
    if bad == 0:
        print("ATTRIBUTED: the entire move is STREHL_FIX_CA defaulting on.")
        print("Every other commit in the range is thereby cleared of touching these bytes.")
    else:
        print(f"NOT ATTRIBUTED: {bad} check(s) failed -- do NOT re-baseline on this evidence.")
    return bad


if __name__ == "__main__":
    sys.exit(main())

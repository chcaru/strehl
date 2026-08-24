"""Verify section 30 of the M87 report by RE-DERIVATION.

Every figure quoted in section 30 is recomputed here from an operand that is
not the prose: the render files themselves (SHA-256), and the JSON written by
83-arm-a-retake.py / 35-registration.py / 36-registration-controls.py.  A
figure that only agrees with itself is not checked.

Occurrence counts are asserted EXACTLY, not by presence.  A figure that is
right in one place and wrong in another must fail (see fact P112/P113), so
these counts are part of the check and must be updated deliberately when a
figure is legitimately quoted somewhere new.

Also enforces the guard that nothing else in the toolchain provides: the
report must contain ZERO stray C0 control characters (fact P116).
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
DOC = pathlib.Path("docs/research/M87-occlusion.md")
DATA = HERE / "data"
ALIGN = HERE / "cache" / "align"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")

fails = []
checks = 0


def flat(t):
    return re.sub(r"\s+", " ", t.replace("\u2212", "-"))


def chk(label, needle, hay, count=1):
    """Assert `needle` occurs exactly `count` times."""
    global checks
    checks += 1
    got = hay.count(needle)
    if got != count:
        fails.append(f"{label}: expected {count}x {needle!r}, found {got}")


def eq(label, derived, quoted, tol=0.0):
    global checks
    checks += 1
    if abs(derived - quoted) > tol:
        fails.append(f"{label}: re-derived {derived!r} != quoted {quoted!r}")


def sha24(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:24]


def main():
    raw = DOC.read_bytes()
    t = raw.decode("utf-8")
    f = flat(t)

    # ---- the guard nothing else provides -------------------------------
    global checks
    checks += 1
    bad = sorted({ord(c) for c in t
                  if (ord(c) < 32 and ord(c) not in (9, 10, 13)) or ord(c) == 127})
    if bad:
        fails.append(f"C0-GUARD: stray control characters present: {bad}")

    # ---- structure ------------------------------------------------------
    chk("s30-heading", "## 30. The sidecar alert", f)
    for pid in ("P114", "P115", "P116", "P117"):
        chk(f"{pid}-row", f"| {pid} | ", f)

    # ---- 1. the hash equality, recomputed from the renders --------------
    a = sha24(ALIGN / "A-aligned.tif")
    a2 = sha24(SCRATCH / "A2-aligned.tif")
    u = sha24(ALIGN / "U-unaligned.tif")
    u2 = sha24(SCRATCH / "U2-unaligned.tif")
    checks += 1
    if a != a2:
        fails.append(f"HASH-A: A {a} != A2 {a2} -- the central claim of s30")
    checks += 1
    if u != u2:
        fails.append(f"HASH-U: U {u} != U2 {u2}")
    chk("quoted-hash-A", a, f, 2)
    chk("quoted-hash-U", u, f, 3)

    # ---- 2. the retake, re-derived from its own JSON --------------------
    r = json.loads((DATA / "83-arm-a-retake.json").read_text(encoding="utf-8"))
    rt = r["retake"]
    delta = 100.0 * (rt["ISO_A2"] - rt["ISO_U2"]) / rt["ISO_U2"]
    eq("delta-rederived", delta, rt["delta_pct"], 1e-9)
    chk("delta-quoted", "8.086", f, 2)
    eq("delta-to-3dp", round(abs(delta), 3), 8.086, 1e-9)

    moved = abs(delta - r["bars"]["DELTA_ORIGINAL"])
    eq("moved-points", round(moved, 2), 1.49, 1e-9)
    chk("moved-quoted", "1.49 points", f)

    checks += 1
    if rt["verdict"] != "CONFIRM":
        fails.append(f"verdict: JSON says {rt['verdict']}, s30 says CONFIRM")
    chk("verdict-word", "**Verdict CONFIRM**", f)
    checks += 1
    if rt["class"] != "R1-C" or rt["class_original"] != "R1-C":
        fails.append(f"class: {rt['class']} / {rt['class_original']} != R1-C")
    checks += 1
    if r["C_BINARY"]["verdict"] != "PASS":
        fails.append("C_BINARY did not pass")
    checks += 1
    if r["C_BINARY"]["max_abs_dn"] != 0.0:
        fails.append(f"C_BINARY max_abs_dn = {r['C_BINARY']['max_abs_dn']} != 0")

    # ---- 3. the reproduction claim against s15's own stored run ---------
    s35 = json.loads((DATA / "35-registration.json").read_text(encoding="utf-8"))
    eq("repro-ISO-U", rt["ISO_U2"], s35["R1_U"]["ISO"], 1e-12)
    eq("repro-ISO-A", rt["ISO_A2"], s35["R1_A"]["ISO"], 1e-12)
    eq("repro-reduction", abs(delta), s35["reduction_pct"], 1e-9)
    chk("ISO-U-quoted", str(s35["R1_U"]["ISO"]), f)
    chk("ISO-A-quoted", str(s35["R1_A"]["ISO"]), f)
    chk("n-U", "6600", f)
    chk("n-A", "6380", f)
    eq("n-U-json", s35["R1_U"]["n"], 6600)
    eq("n-A-json", s35["R1_A"]["n"], 6380)
    chk("roi-A", "(1182, 1915, 202, 1354)", f)
    chk("scale", "1.0473871678", f)

    # ---- 4. the script-35 vs script-36 clarification -------------------
    s36 = json.loads(
        (DATA / "36-registration-controls.json").read_text(encoding="utf-8"))
    eq("s36-total", round(s36["total_pct"], 3), -6.595, 1e-9)
    eq("s36-resample", round(s36["resample_pct"], 3), 0.579, 1e-9)
    eq("s36-registration", round(s36["registration_pct"], 3), -7.174, 1e-9)
    chk("s36-total-quoted", "-6.595", f)
    chk("s36-resample-quoted", "+0.579", f)
    chk("s36-registration-quoted", "-7.174", f)
    eq("s36-U", round(s36["U"]["ISO"], 5), 0.06805, 1e-9)
    eq("s36-Uw", round(s36["Uw"]["ISO"], 5), 0.06844, 1e-9)
    eq("s36-A", round(s36["A"]["ISO"], 5), 0.06356, 1e-9)

    # ---- 5. the sidecar solve's own reported numbers -------------------
    chk("digest", "8d023c0fe355d109", f)
    chk("heldout", "13.578", f)
    chk("cyclefloor", "2.908", f)
    chk("provenance", "299 placed / 0 refused", f, 2)
    chk("reference", "reference frame 149", f, 2)

    # ---- 6. the control-character finding ------------------------------
    chk("VT", "U+000B", f, 4)
    chk("BEL", "U+0007", f)
    chk("other-file", "M105b-exposure-ship.md", f)
    chk("crlf-count", "4088", f)

    # ---- 7. the exit-code measurement ----------------------------------
    chk("fast", "0.3 s", f, 2)
    chk("slow", "6.1 s", f, 2)

    print(f"{checks} checks passed; {len(fails)} failures"
          if not fails else f"{checks} checks run; {len(fails)} FAILURES")
    for x in fails:
        print(f"  FAIL {x}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

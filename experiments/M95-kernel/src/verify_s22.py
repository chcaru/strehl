"""Gate for section 22 of docs/research/M95-kernel.md.

Contract, which matters as much as the checks (discipline 702):
  exit 0 = every registered claim verified
  exit 1 = at least one claim FAILED, and each failure is printed
  exit 2 = the verifier itself broke; no verdict was reached

A gate that cannot distinguish tool failure from subject failure makes a green
run and a broken run the same observation. stdout is reconfigured to UTF-8 with
errors='backslashreplace', which cannot itself raise, because Python picks the
ANSI codepage for piped stdout and this corpus is full of characters cp1252
cannot encode.

Anchoring rules this milestone has paid for, all five of them applied below:
an anchor must be a NEIGHBOUR of the value, must not itself be any other checked
value, must not contain another checked value, must survive line wrapping, and
the value must appear exactly once inside its window.
"""

import hashlib
import json
import os
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


def _boom(t, v, tb):
    import traceback
    traceback.print_exception(t, v, tb)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(2)          # a bare sys.exit here does not survive the hook


sys.excepthook = _boom

REPO = pathlib.Path(__file__).resolve().parents[3]
REPORT = REPO / "docs" / "research" / "M95-kernel.md"
OUT = REPO / "experiments" / "M95-resample" / "out"
RENDERS = pathlib.Path(r"C:\dev\strehl-out\M95-montage")

raw = REPORT.read_text(encoding="utf-8").replace("\r\n", "\n")
m = re.search(r"^## 22\. ", raw, re.M)      # NOT split("## 22."): that also
if not m:                                   # matches "### 22.1" and truncates
    print("TOOL FAILURE: section 22 heading not found in the report")
    os._exit(2)
S = raw[m.start():]
FLAT = re.sub(r"\s+", " ", S)               # prose wraps; match on collapsed text
print(f"section 22: {len(S)} chars, {S.count(chr(10))} lines")

good, bad = 0, 0


def check(label, ok, detail=""):
    global good, bad
    if ok:
        good += 1
        print(f"  ok   {label}")
    else:
        bad += 1
        print(f"  BAD  {label}   {detail}")


def has(label, value, ctx):
    """`value` must occur exactly once inside a window anchored on `ctx`."""
    i = FLAT.find(ctx)
    if i < 0:
        check(label, False, f"anchor {ctx!r} not found in section 22")
        return
    win = FLAT[max(0, i - 160): i + len(ctx) + 160]
    n = win.count(value)
    check(f"{label} = {value}", n == 1,
          f"occurs {n}x in the window anchored on {ctx!r}")


def phrase(label, text):
    check(label, text in FLAT, f"phrase absent: {text!r}")


# ---------------------------------------------------------------- artifacts
r1 = json.loads((OUT / "x9_ringing.json").read_text(encoding="utf-8"))
r2 = json.loads((OUT / "x9_ringing2.json").read_text(encoding="utf-8"))
mo = json.loads((OUT / "x9_montage.json").read_text(encoding="utf-8"))

print("\n-- the report must agree with what the code printed --")
check("arm 12 R1 recorded as FAIL", r1["R1"]["pass"] is False, str(r1["R1"]))
check("arm 12 R2 recorded as PASS", r1["R2"]["pass"] is True, str(r1["R2"]))
check("arm 12 R3 recorded as FAIL", r1["R3"]["pass"] is False, str(r1["R3"]))
check("arm 12b R4 recorded as FAIL", r2["R4"]["pass"] is False, str(r2["R4"]))
check("arm 12b R5 recorded as PASS", r2["R5"]["pass"] is True, str(r2["R5"]))
check("arm 12b R6 recorded as PASS", r2["R6"]["pass"] is True, str(r2["R6"]))

r4x = f"{r2['R4']['ratio']:.2f}x"
check("R4 ratio appears 3x (table, headline, refuted-prediction) and all agree",
      FLAT.count(r4x) == 3,
      f"artifact {r2['R4']['ratio']:.4f} -> {r4x}, found {FLAT.count(r4x)}x")
check("R5 fraction in report matches artifact",
      FLAT.count(f"{r2['R5']['frac']:.3f}") == 1, f"artifact {r2['R5']['frac']:.4f}")
check("R6 recovery DN in report matches artifact",
      FLAT.count(f"{r2['R6']['recovered']:.1f}") == 1, f"artifact {r2['R6']['recovered']}")
check("R3 recovery DN in report matches artifact",
      FLAT.count(f"{r1['R3']['recovered']:.1f}") == 1, f"artifact {r1['R3']['recovered']}")

# Reconstruct each results table row from the JSON and require it verbatim.
# Stronger than checking cells one at a time, and immune to the short-token
# collision that made a bare "0.60" match three places in this section.
for arm in ("lanczos2", "lanczos3"):
    a = r2["results"][arm]
    ratio = a["NEAR"]["mean_excess"] / max(a["FAR"]["mean_excess"], 1e-9)
    bold = "**" if arm == "lanczos3" else ""
    row = (f"| {arm} | {a['NEAR']['mean_excess']:.2f} DN | "
           f"{a['FAR']['mean_excess']:.2f} DN | {bold}{ratio:.2f}x{bold} | "
           f"{a['NEAR']['n']:,} | {a['FAR']['n']:,} |".replace(",", " "))
    check(f"arm 12b {arm} row reconstructed from the artifact", row in FLAT, row)

for arm in ("lanczos2", "lanczos3"):
    a = r1["results"][arm]
    row = (f"| {arm} | {a['FLAT']['mean_excess']:.2f} DN | "
           f"{a['MID']['mean_excess']:.2f} | {a['EDGE']['mean_excess']:.2f} | "
           f"{a['EDGE']['n']:,} |".replace(",", " "))
    check(f"arm 12 {arm} row reconstructed from the artifact", row in FLAT, row)

check("montage sha256 in report matches the json artifact",
      mo["montage_sha256"] in FLAT, mo["montage_sha256"][:16])

print("\n-- the report's hashes must match the bytes on disk --")
for arm, tag in (("catmull-rom", "E400A63A"), ("lanczos2", "CE1710CE"),
                 ("lanczos3", "DC6555BC")):
    p = RENDERS / f"bee3-{arm}.tif"
    if not p.exists():
        check(f"{arm} render present", False, str(p))
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest().upper()
    check(f"{arm} render sha256 on disk appears in the report", h in FLAT, h[:24])
    check(f"{arm} render begins {tag}", h.startswith(tag), h[:16])
    check(f"{arm} render is 197797874 bytes", p.stat().st_size == 197797874,
          str(p.stat().st_size))

pm = RENDERS / "M95-kernel-montage.png"
if pm.exists():
    hm = hashlib.sha256(pm.read_bytes()).hexdigest()
    check("montage png on disk matches the sha256 in the report", hm in FLAT, hm[:24])
else:
    check("montage png present", False, str(pm))

print("\n-- the ladder, anchored on a neighbouring literal --")
has("mitchell identity dex", "-0.200830", "mitchell")
has("lanczos2 gain over catmull-rom", "+0.0043", "lanczos2 | -0.1963")
has("lanczos3 gain over catmull-rom", "+0.1343", "lanczos3 | -0.0663")
has("bspline gain over catmull-rom", "+0.1055", "bspline | -0.0951")
# 6.2500 is deliberately NOT checked by window: it occurs five times by design
# (the analytic harness sentence, the catmull-rom row, the lanczos2 row, and
# twice in the "6.2500% against 6.2500%" identity sentence) and that repetition
# IS the finding. Assert the count instead. The first count I wrote here was 3;
# the gate caught it and printed 5.
check("6.2500 occurs exactly 5x across the harness sentence, two table rows "
      "and the identity sentence",
      FLAT.count("6.2500") == 5, f"occurs {FLAT.count('6.2500')}x")
phrase("the two-kernel identity is stated",
       "6.2500% against 6.2500%")
has("lanczos3 clean-step overshoot", "11.1413", "lanczos3 | 11.1413")
has("lanczos3 ringing versus catmull-rom", "1.78x", "reach 5")

print("\n-- the cost, and its honest range --")
has("catmull-rom gather", "330.606 s", "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112")
has("lanczos2 gather", "1386.041 s", "CE1710CED111C419AA02960963B2FD7C422FCABA7DDA0A5F5C2E6F1CE7C03983")
has("lanczos3 gather", "2292.288 s", "DC6555BCDAE0FC4B334DE31AD130A0C644068647FA77F5FDD94F3271044B26A9")
has("repeat gather timing", "411.261 s", "identical invocation")
phrase("the repeat reproduced bit for bit", "reproduced its output **bit for bit**")
phrase("cost is reported as a range", "the cost ratios are a range, not a point")

print("\n-- the failures are reported as failures --")
phrase("R3 failure is stated", "recovered 144.1 DN of a planted 2000 DN, 7.2%")
phrase("R1 is declared unreadable", "makes R1 unreadable")
phrase("the blind spot is named", "blind precisely where it was aimed")
phrase("R4 failed on a live instrument", "R4 failed, on a live instrument")
phrase("ringing is not claimed", "this is not ringing and I will not call it ringing")
phrase("the pre-registration defect is owned",
       "A control that cannot pass is no more a control than one that cannot fail.")
phrase("the retired metric is named as retired", "The metric is retired")
phrase("the bar was not relaxed", "I did not relax the bar.")
phrase("PIL truncation is disclosed", "measured 8-bit quantisation rather")
phrase("the stale figure is corrected", "1.78x on a true discontinuity")
phrase("refuted prediction, NEAR magnitude", "well below my range")
phrase("no self-verification claimed", "I am not able to verify my own work")

print("\n-- provenance of the pre-registrations --")
for sha, what in (("42a0c7c", "arm 11 bars"), ("85ee287", "arm 12 bars"),
                  ("35c40c2", "arm 12b bars"), ("ac95e1b", "lanczos2 landing"),
                  ("843f6e1", "lanczos3 already landed"),
                  ("adff9c8b7818624ba24cd5d21ffd108630e3055d", "render commit")):
    check(f"{what} cites {sha}", sha in FLAT, "absent")

print(f"\nverify_s22: {good} ok, {bad} BAD")
if bad:
    print("verify_s22: FAILED")
    sys.exit(1)
print("verify_s22: GREEN")
sys.exit(0)

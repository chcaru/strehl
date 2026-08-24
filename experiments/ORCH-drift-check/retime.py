"""Re-measure the README's shipped end-to-end claim.

README line 27-29 claims 299 frames of 33 MP ARW to a 7032 x 4688 16-bit sRGB
TIFF in 23.1 s. Three things have landed since: alignment was wired into
`strehl stack` (885e9f7), M95 made full-resolution demosaic the default under
--srgb, and M100 added the exposure statistic. M97's ledger row explicitly
warned that 23.1 s is a shipped claim that must be re-measured rather than
assumed. This measures it.

Reports the MINIMUM of N runs, warm, because the claim is a capability claim
and the minimum is the honest estimator for one -- but prints every run so the
spread is visible rather than hidden behind the minimum.
"""
import os
import re
import subprocess
import time

EXE = r".cargo-target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\bee-3-cpl"
OUT = os.path.join(os.environ["TEMP"], "M-timing")
os.makedirs(OUT, exist_ok=True)
RUNS = 3

VARIANTS = [
    ("default (binned linear, the measurement path)", []),
    ("--srgb --auto-exposure (the viewing path)", ["--srgb", "--auto-exposure"]),
    ("--srgb --binned (pre-M95 viewing render)", ["--srgb", "--binned"]),
]

DIM = re.compile(r"(\d+) x (\d+), 16-bit")

print("warming the page cache ...", flush=True)
subprocess.run([EXE, "stack", SRC, "--gate", "2", "--limit", "40",
                "--out", os.path.join(OUT, "warm.tif")],
               capture_output=True, text=True)

print()
print("%-46s %9s %9s %9s  %s" % ("variant", "best", "median", "worst", "output"))
print("-" * 100)
for label, extra in VARIANTS:
    dst = os.path.join(OUT, "t.tif")
    ts, dims = [], ""
    for _ in range(RUNS):
        if os.path.exists(dst):
            os.remove(dst)
        t0 = time.perf_counter()
        r = subprocess.run([EXE, "stack", SRC, "--gate", "2", "--out", dst] + extra,
                           capture_output=True, text=True)
        ts.append(time.perf_counter() - t0)
        if r.returncode != 0:
            print("  FAIL rc=%d\n%s" % (r.returncode, (r.stderr or "")[-1500:]))
            ts = []
            break
        m = DIM.search(r.stderr or "")
        if m:
            dims = "%s x %s" % (m.group(1), m.group(2))
    if not ts:
        continue
    ts.sort()
    print("%-46s %8.2fs %8.2fs %8.2fs  %s"
          % (label, ts[0], ts[len(ts) // 2], ts[-1], dims), flush=True)

n = len([f for f in os.listdir(SRC) if f.lower().endswith(".arw")])
print()
print("frames: %d   runs per variant: %d   README claims 23.1 s at 7032 x 4688" % (n, RUNS))

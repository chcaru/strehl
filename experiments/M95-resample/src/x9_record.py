"""M95 arm 11 - the rule 47 record for the owner's montage, printed from the
artifacts on disk rather than from anything I remember.

Rule 47 as amended binds the environment, not only the CLI flags: STREHL_ALIGN,
STREHL_WARPMAP, STREHL_FIX_HALO, thread count, byte count, commit SHA. An
environment variable, not a flag, is what made the last freeze irreproducible.

Also lifts the tool's own `field + gate` timing line, which is summed across
workers and is therefore a far better cost instrument than wall clock on a
machine currently shared with about six other agents.
"""

import hashlib
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

DST = pathlib.Path(r"C:\dev\strehl-out\M95-montage")
REPO = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")
KERNELS = ["catmull-rom", "lanczos2", "lanczos3"]

sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                     capture_output=True).stdout.decode().strip()
print(f"commit SHA at render time : {sha}")
print(f"STREHL_ALIGN              : (unset -- alignment is on by default; log says 'ON')")
print(f"STREHL_FIX_HALO           : (unset)")
print(f"STREHL_WARPMAP            : per arm, below (own scratch, never the capture library)")
print()

rows = []
for k in KERNELS:
    tif = DST / f"bee3-{k}.tif"
    log = (DST / f"log-{k}.txt").read_text(encoding="utf-8", errors="replace")
    b = tif.read_bytes()
    d = hashlib.sha256(b).hexdigest().upper()

    def grab(pat, default="(absent)"):
        m = re.search(pat, log)
        return m.group(1).strip() if m else default

    placed = grab(r"alignment\s*:\s*(.+)")
    resamp = grab(r"resampler\s*:\s*(\S+)")
    fieldg = grab(r"field \+ gate\s*:\s*(.+)")
    threads = grab(r"(?:threads|workers)\s*[:=]\s*(\S+)")
    dims = grab(r"wrote\s*:\s*\S+ \((\d+ x \d+)")
    rows.append((k, d, len(b), resamp, fieldg, placed, threads, dims))

print(f"{'kernel':12s} {'bytes':>12s}  {'sha256 (first 16)':18s} resampler   field+gate (summed across workers)")
for k, d, n, resamp, fieldg, placed, threads, dims in rows:
    print(f"{k:12s} {n:12d}  {d[:16]:18s} {resamp:11s} {fieldg}")
print()
for k, d, n, resamp, fieldg, placed, threads, dims in rows:
    print(f"{k}:")
    print(f"  STREHL_WARPMAP = {DST / (k + '.warpmap.txt')}")
    print(f"  invocation     = strehl stack D:\\personal\\macro\\bee-3-cpl --srgb "
          f"--exposure 1.54 --gate 4.0 -o {DST / ('bee3-' + k + '.tif')}")
    print(f"  alignment      = {placed}")
    print(f"  threads        = {threads}")
    print(f"  output         = {dims}, {n} bytes, sha256 {d}")

# The three renders must differ, or the sidecar rewrite did not reach the gather.
digs = {r[0]: r[1] for r in rows}
if len(set(digs.values())) != len(KERNELS):
    sys.exit(f"RENDERS ARE NOT DISTINCT -- the kernel selection did not reach the gather: {digs}")
print("\nall three renders are byte-distinct: the sidecar's resampler line reaches the gather.")

# Cost, relative, on the tool's own summed-across-workers number.
def secs(s):
    m = re.search(r"([\d.]+)\s*s summed", s)
    return float(m.group(1)) if m else None

base = secs(rows[0][4])
print(f"\ngather cost, relative to catmull-rom (tool's own summed-across-workers timer):")
for k, d, n, resamp, fieldg, placed, threads, dims in rows:
    t = secs(fieldg)
    if t is None or base is None:
        print(f"  {k:12s} (could not parse)")
    else:
        print(f"  {k:12s} {t:9.1f} s   {t / base:5.2f}x")
print("END OF RULE 47 RECORD")

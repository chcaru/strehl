"""M95 arm 11 - write the per-kernel sidecars for the owner's montage.

The sidecar's `resampler <name>` line is the supported selection path: warpmap.rs
writes it, parses it back, and merge_cmd gathers with map.resampler(). Rewriting
that one line is how the orchestrator's own verified A/B selected a kernel, and
it needs no CLI change, which matters because align_cmd.rs is not mine.

Anchored on the full line and hard-errors if it does not land exactly once. A
bare replace that silently matches nothing would produce three identical
sidecars and a montage showing no difference -- which is indistinguishable from
a real null, and is exactly the failure this project keeps paying for.
"""

import hashlib
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

DST = pathlib.Path(r"C:\dev\strehl-out\M95-montage")
BASE = DST / "base.warpmap.txt"
KERNELS = ["catmull-rom", "lanczos2", "lanczos3"]
ANCHOR = "resampler catmull-rom"

raw = BASE.read_bytes()
text = raw.decode("utf-8")
n = text.count(ANCHOR)
if n != 1:
    sys.exit(f"ANCHOR {ANCHOR!r} OCCURS {n} TIMES, EXPECTED 1 -- refusing to write sidecars")

print(f"base: {BASE}  {len(raw)} bytes  sha256 {hashlib.sha256(raw).hexdigest()[:16]}")
for k in KERNELS:
    out = text.replace(ANCHOR, f"resampler {k}", 1)
    if f"resampler {k}" not in out:
        sys.exit(f"REWRITE FOR {k} DID NOT LAND")
    p = DST / f"{k}.warpmap.txt"
    p.write_bytes(out.encode("utf-8"))
    got = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.startswith("resampler ")]
    if got != [f"resampler {k}"]:
        sys.exit(f"VERIFY FAILED for {k}: sidecar says {got}")
    frames = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.startswith("frames ")]
    print(f"  {k:12s} -> {got[0]:26s} {frames[0]:12s} {p.stat().st_size} bytes")

# The three must differ from each other, or the montage is comparing one render
# to itself three times.
digests = {k: hashlib.sha256((DST / f"{k}.warpmap.txt").read_bytes()).hexdigest() for k in KERNELS}
if len(set(digests.values())) != len(KERNELS):
    sys.exit(f"SIDECARS ARE NOT DISTINCT: {digests}")
print("\nall three sidecars are distinct:")
for k, d in digests.items():
    print(f"  {k:12s} {d[:32]}")
print("END OF SIDECAR WRITER")

"""K10 -- does the silently-accepted `resampler` field actually change the render?

K9 proved the loader accepts a sidecar whose `resampler` line was mutated
catmull-rom -> lanczos3, announcing it with a line byte-identical to the
baseline's. That is only a hazard if the field is HONOURED on the read path.
If `stack` ignores it and always gathers with its own kernel, the mutation is
cosmetic and I must say so.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
H4c POWER / DETERMINISM CONTROL, RUN FIRST.
    Two renders through the SAME sidecar must be byte-identical. If they are
    not, the render is nondeterministic and no hash comparison below carries
    any information. FAIL here => abandon, report the instrument failure.

H4  TREATMENT.
    Render the same 6-frame bracket twice, once through the catmull-rom
    sidecar and once through the lanczos3-mutated one, everything else held
    fixed.
    HONOURED : hashes differ => the field is live on the read path, and a
               stale cache entry silently changes which kernel gathers your
               pixels. Report the fraction of differing bytes as the size.
    INERT    : hashes identical => the field is solve-time only; the K9
               acceptance is cosmetic and the hazard is smaller than claimed.

Both outcomes get reported. I am not trying to make this land either way.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
EXE = ROOT / "target-m95" / "release" / "strehl.exe"
STACK_DIR = Path(r"D:\personal\macro\bee-3-cpl")
SCRATCH = Path(r"C:\dev\strehl-out\M95-kernel\k9")
OUT = ROOT / "experiments" / "M95-kernel" / "out"
CACHE = Path(os.environ["LOCALAPPDATA"]) / "strehl" / "warpmaps"

SIDE_CR = SCRATCH / "side-6-cr.txt"
SIDE_LZ = SCRATCH / "side-6-lz.txt"

R = {}


def cache_state():
    if not CACHE.is_dir():
        return {}
    return {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(CACHE.glob("*.warpmap.txt"))
    }


def render(sidecar: Path, dst: Path):
    if dst.exists():
        dst.unlink()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["STREHL_WARPMAP"] = str(sidecar)
    p = subprocess.run(
        [str(EXE), "stack", str(STACK_DIR), "--limit", "6", "--gate", "0", "--out", str(dst)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=3600,
    )
    log = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 or not dst.exists():
        raise SystemExit(f"render failed rc={p.returncode} for {sidecar}\n{log[-1500:]}")
    return hashlib.sha256(dst.read_bytes()).hexdigest(), dst.stat().st_size, log


def diff_bytes(a: Path, b: Path):
    x, y = a.read_bytes(), b.read_bytes()
    n = min(len(x), len(y))
    d = sum(1 for i in range(n) if x[i] != y[i])
    return d, n, (d / n if n else 0.0)


print("=" * 78)
print("K10  is the accepted resampler field honoured on the read path?")
print("=" * 78)
for p in (SIDE_CR, SIDE_LZ):
    print(f"  {p.name}  exists={p.exists()}")
cache_before = cache_state()

print("\n--- H4c  POWER / DETERMINISM CONTROL (runs first) ---")
h_a, sz_a, _ = render(SIDE_CR, SCRATCH / "render-cr-a.tif")
h_b, sz_b, _ = render(SIDE_CR, SCRATCH / "render-cr-b.tif")
det = h_a == h_b
print(f"  same sidecar, run A : {h_a[:32]}  {sz_a} B")
print(f"  same sidecar, run B : {h_b[:32]}  {sz_b} B")
print(f"  H4c = {'PASS' if det else 'FAIL'}  (byte-identical: {det})")
R["H4c"] = {"verdict": "PASS" if det else "FAIL", "sha_a": h_a, "sha_b": h_b, "bytes": sz_a}

if not det:
    print("  !! nondeterministic render; the H4 comparison would be meaningless.")
    R["H4"] = {"verdict": "ABANDONED", "reason": "determinism control failed"}
else:
    print("\n--- H4  TREATMENT: catmull-rom sidecar vs lanczos3-mutated sidecar ---")
    h_lz, sz_lz, log_lz = render(SIDE_LZ, SCRATCH / "render-lz.tif")
    print(f"  catmull-rom sidecar : {h_a[:32]}  {sz_a} B")
    print(f"  lanczos3    sidecar : {h_lz[:32]}  {sz_lz} B")
    honoured = h_lz != h_a
    print(f"  H4 = {'HONOURED' if honoured else 'INERT'}")
    R["H4"] = {
        "verdict": "HONOURED" if honoured else "INERT",
        "sha_catmull_rom": h_a,
        "sha_lanczos3": h_lz,
        "bytes": sz_lz,
    }
    if honoured:
        d, n, frac = diff_bytes(SCRATCH / "render-cr-a.tif", SCRATCH / "render-lz.tif")
        print(f"  differing bytes     : {d} / {n}  = {frac * 100:.4f}%")
        R["H4"]["differing_bytes"] = d
        R["H4"]["compared_bytes"] = n
        R["H4"]["differing_frac"] = frac
        print("  => a stale cache entry silently changes WHICH KERNEL gathers your pixels,")
        print("     and the announcement line is identical in both cases.")
    else:
        print("  => the field is solve-time only; K9's acceptance is cosmetic.")

print("\n--- closing state ---")
cache_after = cache_state()
print(f"  shared cache unchanged over the whole run: {cache_before == cache_after}")
print(f"  D:\\personal\\macro\\bee-3-cpl\\warpmap.txt exists: {(STACK_DIR / 'warpmap.txt').exists()}")
R["closing"] = {
    "cache_unchanged": cache_before == cache_after,
    "legacy_exists": (STACK_DIR / "warpmap.txt").exists(),
}

print("\n" + "=" * 78)
print(f"H4c determinism control : {R['H4c']['verdict']}")
print(f"H4  resampler field     : {R['H4']['verdict']}")
print("=" * 78)

(OUT / "k10_resampler_field.json").write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT / 'k10_resampler_field.json'}")

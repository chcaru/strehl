"""K9 -- the shared-sidecar hazard, measured rather than reasoned.

The orchestrator broadcast that `strehl align` writes its sidecar to
`<stackdir>/warpmap.txt` inside the read-only capture library, and that seven
live agents have been silently overwriting each other's. This script tests
that claim and the three follow-on questions, on the tree as it stands now.

BARS, REGISTERED BEFORE THE RUN (2026-08-24)
--------------------------------------------
H0  WHERE DOES THE DEFAULT GO?
    Read `sidecar_path()`'s behaviour empirically. The orchestrator's premise
    is that it is `<stackdir>/warpmap.txt`.
    PASS-premise  : that file exists / is created by an `align` with no --out.
    REFUTE-premise: it is not, and the default lands somewhere else.

H1  DOES `--out` PROTECT THE SHARED CACHE?
    Seven agents are being told to rely on `--out`. Record SHA-256 + size of
    the shared cache entry, run `align --limit 6 --out <my scratch>`, re-record.
    PASS: byte-identical. FAIL: any change -- and then the advice is unsafe.

H2  IS THE `resampler` FIELD VALIDATED?
    `StackIdentity::check` (warpmap.rs:257) compares digest + frames only, and
    `load_or_solve` adds only `map.len() == paths.len()`. Nothing appears to
    compare `resampler`. M95 has just SHIPPED a flag that writes that field.
    Mutate a sidecar's resampler line and apply it to the same bracket.
    HAZARD-CONFIRMED: accepted silently => the kernel can diverge unannounced.
    NO-HAZARD       : refused => report that instead.

H3  POWER CONTROL -- CAN THE LOADER SAY OTHERWISE AT ALL? (discipline 594)
    H2's "accepted" is worthless unless the same loader is shown REFUSING
    something. Solve a genuinely different bracket (--limit 5), apply it to the
    6-frame bracket. MUST be refused on digest/frame-count.
    If H3 is accepted the instrument is dead and H2 is uninterpretable: report
    the instrument failure and draw no conclusion about the resampler.

Every mutation is anchored on a unique full line and hard-errors if it does not
land, because a mutation that silently misses reports a false GREEN.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
EXE = ROOT / "target-m95" / "release" / "strehl.exe"
STACK_DIR = Path(r"D:\personal\macro\bee-3-cpl")
SCRATCH = Path(r"C:\dev\strehl-out\M95-kernel\k9")
OUT = ROOT / "experiments" / "M95-kernel" / "out"
CACHE = Path(os.environ["LOCALAPPDATA"]) / "strehl" / "warpmaps"
LEGACY = STACK_DIR / "warpmap.txt"

R = {}


def sh(args, env_extra=None, timeout=1800):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update({k: str(v) for k, v in env_extra.items()})
    p = subprocess.run(
        [str(a) for a in args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def digest_file(p: Path):
    if not p.exists():
        return None
    b = p.read_bytes()
    return {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def cache_entries():
    if not CACHE.is_dir():
        return {}
    out = {}
    for f in sorted(CACHE.glob("*.warpmap.txt")):
        out[f.name] = digest_file(f)
    return out


def header(p: Path):
    """The three fields that decide what a render actually does."""
    txt = p.read_text(encoding="utf-8", errors="replace")
    g = {}
    for key in ("frames", "reference", "resampler", "stack", "digest"):
        m = re.search(rf"^{key}\s+(.+)$", txt, re.M)
        g[key] = m.group(1).strip() if m else None
    return g


def mutate_line(src: Path, dst: Path, old: str, new: str):
    """Anchored, hard-erroring mutation. A miss must never look like a pass."""
    txt = src.read_text(encoding="utf-8", errors="replace")
    n = txt.count(old)
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND (or ambiguous): {old!r} occurs {n} times in {src}"
        )
    dst.write_text(txt.replace(old, new, 1), encoding="utf-8")
    if dst.read_text(encoding="utf-8", errors="replace").count(new) != 1:
        raise SystemExit(f"MUTATION DID NOT LAND: {new!r} not in {dst}")


def alignment_lines(log: str):
    return [ln.strip() for ln in log.splitlines() if "alignment" in ln.lower()]


print("=" * 78)
print("K9  shared-sidecar hazard")
print("=" * 78)
print(f"exe        : {EXE}  exists={EXE.exists()}")
print(f"stack dir  : {STACK_DIR}  exists={STACK_DIR.is_dir()}")
print(f"cache root : {CACHE}  exists={CACHE.is_dir()}")
SCRATCH.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- H0
print("\n--- H0  where does the default sidecar go? ---")
legacy_before = LEGACY.exists()
any_legacy = sorted(Path(r"D:\personal\macro").glob("*/warpmap.txt"))
print(f"  {LEGACY}  exists={legacy_before}")
print(f"  any <stack>/warpmap.txt under D:\\personal\\macro : {len(any_legacy)}")
for p in any_legacy:
    print(f"    {p}")
cache_before = cache_entries()
print(f"  shared cache entries: {len(cache_before)}")
for k, v in cache_before.items():
    print(f"    {k}  {v['bytes']}B  sha={v['sha256'][:16]}")
R["H0"] = {
    "legacy_exists": legacy_before,
    "legacy_count_under_library": len(any_legacy),
    "cache_entries_before": cache_before,
    "premise_refuted": (not legacy_before) and len(any_legacy) == 0,
}

# ---------------------------------------------------------------- H1
print("\n--- H1  does --out protect the shared cache? ---")
side_cr = SCRATCH / "side-6-cr.txt"
rc, log = sh(
    [EXE, "align", STACK_DIR, "--limit", 6, "--out", side_cr, "--resampler", "catmull-rom"]
)
print(f"  align --limit 6 --out ...  rc={rc}  wrote={side_cr.exists()}")
cache_after = cache_entries()
same = cache_before == cache_after
print(f"  shared cache byte-identical after the run: {same}")
if not same:
    for k in set(cache_before) | set(cache_after):
        if cache_before.get(k) != cache_after.get(k):
            print(f"    CHANGED {k}: {cache_before.get(k)} -> {cache_after.get(k)}")
h1 = "PASS" if (same and side_cr.exists()) else "FAIL"
print(f"  H1 = {h1}")
if side_cr.exists():
    print(f"  my sidecar header: {header(side_cr)}")
R["H1"] = {
    "verdict": h1,
    "rc": rc,
    "cache_unchanged": same,
    "out_written": side_cr.exists(),
    "header": header(side_cr) if side_cr.exists() else None,
    "legacy_created": LEGACY.exists(),
}
if h1 == "FAIL":
    print("  !! --out does NOT protect the cache; stop and report.")

# ---------------------------------------------------------------- H3 first
# The power control runs BEFORE the treatment so that a dead loader is caught
# before any conclusion is drawn from H2.
print("\n--- H3  POWER CONTROL: solve a different bracket, apply it here ---")
side_5 = SCRATCH / "side-5-cr.txt"
rc5, _ = sh([EXE, "align", STACK_DIR, "--limit", 5, "--out", side_5, "--resampler", "catmull-rom"])
print(f"  align --limit 5 --out ...  rc={rc5}  wrote={side_5.exists()}")
if side_5.exists():
    print(f"  5-frame header: {header(side_5)}")
rc, log3 = sh(
    [EXE, "stack", STACK_DIR, "--limit", 6, "--gate", 0],
    env_extra={"STREHL_WARPMAP": side_5},
)
refused3 = rc != 0
print(f"  applying the 5-frame sidecar to the 6-frame bracket: rc={rc} refused={refused3}")
for ln in [l for l in log3.splitlines() if l.strip()][-6:]:
    print(f"    | {ln.strip()}")
h3 = "PASS" if refused3 else "FAIL"
print(f"  H3 = {h3}  (the loader can say otherwise)" if refused3 else f"  H3 = {h3}  !! DEAD INSTRUMENT")
R["H3"] = {"verdict": h3, "rc": rc, "refused": refused3, "tail": log3.strip()[-1200:]}

# ---------------------------------------------------------------- H2
print("\n--- H2  is the resampler field validated? ---")
h2 = "SKIPPED"
if h3 != "PASS":
    print("  SKIPPED: H3 failed, so an 'accepted' result would be uninterpretable.")
    R["H2"] = {"verdict": h2, "reason": "power control H3 failed"}
else:
    side_lz = SCRATCH / "side-6-lz.txt"
    mutate_line(side_cr, side_lz, "resampler catmull-rom", "resampler lanczos3")
    print(f"  mutated header: {header(side_lz)}")
    rc_cr, log_cr = sh(
        [EXE, "stack", STACK_DIR, "--limit", 6, "--gate", 0],
        env_extra={"STREHL_WARPMAP": side_cr},
    )
    rc_lz, log_lz = sh(
        [EXE, "stack", STACK_DIR, "--limit", 6, "--gate", 0],
        env_extra={"STREHL_WARPMAP": side_lz},
    )
    print(f"  baseline  (catmull-rom sidecar): rc={rc_cr}")
    for ln in alignment_lines(log_cr):
        print(f"    | {ln}")
    print(f"  mutated   (lanczos3   sidecar): rc={rc_lz}")
    for ln in alignment_lines(log_lz):
        print(f"    | {ln}")
    accepted = rc_lz == 0
    h2 = "HAZARD-CONFIRMED" if accepted else "NO-HAZARD"
    print(f"  H2 = {h2}")
    if not accepted:
        for ln in [l for l in log_lz.splitlines() if l.strip()][-6:]:
            print(f"    | {ln.strip()}")
    R["H2"] = {
        "verdict": h2,
        "rc_baseline": rc_cr,
        "rc_mutated": rc_lz,
        "accepted_silently": accepted,
        "align_lines_baseline": alignment_lines(log_cr),
        "align_lines_mutated": alignment_lines(log_lz),
        "tail_mutated": log_lz.strip()[-1200:],
    }

# ---------------------------------------------------------------- close
print("\n--- closing state ---")
cache_end = cache_entries()
print(f"  shared cache unchanged over the WHOLE run: {cache_before == cache_end}")
print(f"  {LEGACY} exists: {LEGACY.exists()}")
R["closing"] = {
    "cache_unchanged_whole_run": cache_before == cache_end,
    "legacy_exists": LEGACY.exists(),
    "cache_entries_after": cache_end,
}

print("\n" + "=" * 78)
print(f"H0 premise refuted (default is NOT in the capture dir): {R['H0']['premise_refuted']}")
print(f"H1 --out protects the shared cache               : {R['H1']['verdict']}")
print(f"H3 power control, loader refuses a foreign map   : {R['H3']['verdict']}")
print(f"H2 resampler field                               : {R['H2']['verdict']}")
print("=" * 78)

(OUT / "k9_sidecar.json").write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT / 'k9_sidecar.json'}")

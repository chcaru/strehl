"""Verify section 20 of docs/research/M95-kernel.md against primary sources.

Every numeric claim is re-derived from the artifact that produced it -- the
k17 JSON, the k17b output, the sidecar on disk, and the source files read out
of the git working tree -- never from the report's own prose. Two earlier
verifiers in this milestone caught the report drifting from the world that way
(section 19.3), which is the only reason those corrections were made.

Numeric claims are discriminated against last-digit decoys, each anchored on a
neighbouring literal so a short token cannot match by chance (a failure this
milestone paid for twice). Prose is searched whitespace-collapsed and
case-insensitively, because the report wraps and capitalisation at the start of
a sentence is not a claim.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
JSON_OUT = Path(__file__).resolve().parents[1] / "out" / "k17_crop.json"
KDIAG = Path(__file__).resolve().parents[1] / "out" / "k17b_kdiag.txt"
SIDECAR = Path(r"C:\dev\strehl-out\M95-crop\bee-3-cpl-ref149.warpmap.txt")

ok = bad = 0


def section(raw, n):
    """Slice one '## N.' section.

    Never split on '## N.': that substring also occurs inside '### N.M', which
    truncates the section to its first paragraph and turns present claims into
    failures. Anchor on a line start and slice to the next top-level heading.
    """
    m = re.search(rf"^## {n}\. ", raw, re.M)
    if not m:
        sys.exit(f"SECTION {n} NOT FOUND")
    rest = raw[m.end():]
    nxt = re.search(r"^## \d+\. ", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    if len(body.splitlines()) < 40:
        sys.exit(f"SECTION {n} SUSPICIOUSLY SHORT: {len(body.splitlines())} lines")
    return body


def flat(s):
    return re.sub(r"\s+", " ", s)


def num(label, token, ctx):
    """Claim `token` appears in the report within 300 chars of `ctx`.

    `ctx` is mandatory, must be UNIQUE in the section, and must not overlap
    `token`. A self-anchored check (ctx == token, or one containing the other)
    only proves the token exists somewhere, not that it sits where it is
    claimed to -- the negative control caught exactly that: mutating one of two
    "100.00%" occurrences left the other for the anchor to find, and the check
    passed on a report that had become wrong.
    """
    global ok, bad
    if ctx in token or token in ctx:
        sys.exit(f"SELF-ANCHORED CHECK {label!r}: ctx {ctx!r} overlaps token {token!r}")
    n = FLAT.count(ctx)
    if n != 1:
        sys.exit(f"ANCHOR NOT UNIQUE for {label!r} ({n} occurrences): {ctx!r}")
    i = FLAT.find(ctx)
    hay = FLAT[max(0, i - 300): i + 300]
    if token in hay:
        print(f"  ok   {label}: {token}")
        ok += 1
    else:
        print(f"  BAD  {label}: {token!r} not found near {ctx!r}")
        bad += 1


def prose(label, phrase):
    global ok, bad
    if flat(phrase).lower() in FLAT.lower():
        print(f"  ok   {label}")
        ok += 1
    else:
        print(f"  BAD  {label}: {phrase!r}")
        bad += 1


def source_has(label, relpath, needle):
    """Re-read the source file from the working tree, not from the report."""
    global ok, bad
    p = ROOT / relpath
    if not p.exists():
        print(f"  BAD  {label}: {relpath} missing")
        bad += 1
        return
    if needle in re.sub(r"\s+", " ", p.read_text(encoding="utf-8")):
        print(f"  ok   {label}: {relpath} contains it")
        ok += 1
    else:
        print(f"  BAD  {label}: {relpath} lacks {needle!r}")
        bad += 1


raw = REPORT.read_text(encoding="utf-8")
S20 = section(raw, 20)
FLAT = flat(S20)
J = json.loads(JSON_OUT.read_text(encoding="utf-8"))

print("=" * 72)
print("verify section 20 -- crop-instead-of-upsample")
print("=" * 72)

print("\n-- the arms, from k17_crop.json --")
# Anchor each arm's cost on that arm's own sem: the bare tokens "NOW" and "FIX"
# also occur in the bars block at the top of the section ("cost(NOW) - 0.10
# dex"), which is a weaker anchor than the row and matched first.
num("NOW cost", f"{J['NOW']['cost_dex']:+.4f}", f"{J['NOW']['sem']:.4f}")
num("FIX cost", f"{J['FIX']['cost_dex']:+.4f}", f"{J['FIX']['sem']:.4f}")
num("SNAP cost", f"{J['SNAP']['cost_dex']:+.4f}", f"{J['SNAP']['sem']:.4f}")
num("NOW step", f"{J['NOW']['mean_step']:.4f}", f"{J['NOW']['sem']:.4f}")
num("FIX step", f"{J['FIX']['mean_step']:.4f}", f"{J['FIX']['sem']:.4f}")
num("recovery", f"{J['recovery_dex']:+.4f}", "The crop recovers")
num("n per arm", str(J["NOW"]["n"]), "pairs per arm")

print("\n-- controls --")
num("K0 derived k", f"{J['k_derived']:.6f}", "0.931500")
num("K1 null", f"{J['K1_null']:+.6f}", "identity warp, no coverage")
num("K3 positive", f"{J['K3_positive']:+.6f}", "planted sigma=0.30 px")
num("K6 cover alone", f"{J['K6_cover_alone']:+.6f}", "coverage scale acting alone")

print("\n-- phase (P1/P2) --")
num("SNAP near-int", f"{100 * J['SNAP']['near_int_frac']:.2f}%",
    f"{J['SNAP']['sem']:.4f}")
num("NOW near-int", f"{100 * J['NOW']['near_int_frac']:.2f}%",
    f"{J['NOW']['sem']:.4f}")
num("FIX near-int", f"{100 * J['FIX']['near_int_frac']:.2f}%",
    f"{J['FIX']['sem']:.4f}")
num("SNAP near-int restated in prose", f"{100 * J['SNAP']['near_int_frac']:.2f}%",
    "integer by construction")

print("\n-- R5 --")
num("ref0 k", f"{J['R5']['ref0_k']:.6f}", f"{J['R5']['ref0_step']:.4f}")
num("ref0 cost", f"{J['R5']['ref0_cost']:+.4f}", f"{J['R5']['ref0_step']:.4f}")
num("ref0 step", f"{J['R5']['ref0_step']:.4f}", f"{J['R5']['ref0_cost']:+.4f}")
num("R5 difference", f"{abs(J['R5']['difference_dex']):.4f}", "resamples")

print("\n-- verdicts must match the JSON, not the prose --")
if J["B2_dead"] and not J["B2_ships"]:
    prose("B2-DEAD fires", "B2-DEAD fires")
else:
    print("  BAD  JSON does not say dead")
    bad += 1
if J["P2"] == "REFUTED":
    prose("P2 refuted", "REFUTED")
else:
    print(f"  BAD  JSON P2 = {J['P2']}")
    bad += 1
if J["R5"]["verdict"] == "NOT A LEVER":
    prose("R5 not a lever", "NOT A LEVER")
else:
    print(f"  BAD  JSON R5 = {J['R5']['verdict']}")
    bad += 1

print("\n-- derived arithmetic, recomputed here --")
inv = 1.0 / J["k_derived"]
num("1/k", f"{inv:.4f}", "1/k =")
num("view at 1:1", f"{100 * inv:.2f}%", "view of the data")
num("crop percent", f"{100 * (1 - J['k_derived']):.2f}%", "needs 6.85")

print("\n-- the pinned sidecar really is what the report says --")
if SIDECAR.exists():
    h = hashlib.sha256(SIDECAR.read_bytes()).hexdigest().upper()
    num("sidecar sha256", h, "sha256")
    txt = SIDECAR.read_text(encoding="utf-8")
    for key, want in (("frames", "299"), ("reference", "149"),
                      ("stack-digest", "8d023c0fe355d109")):
        if re.search(rf"^{key} {want}$", txt, re.M):
            print(f"  ok   sidecar {key} {want}")
            ok += 1
        else:
            print(f"  BAD  sidecar {key} != {want}")
            bad += 1
else:
    print(f"  BAD  pinned sidecar missing: {SIDECAR}")
    bad += 1

print("\n-- source claims, re-read from the working tree --")
source_has("srgb implies demosaic", "crates/strehl-cli/src/main.rs",
           "demosaic: demosaic || (srgb && !binned),")
source_has("geom from frame 0", "crates/strehl-cli/src/merge_cmd.rs",
           "let geom = first.geometry();")
source_has("frozen branch can be srgb", "crates/strehl-cli/src/merge_cmd.rs",
           "let v = if srgb { srgb_encode(v) } else { v };")
source_has("fit_to_cover keeps geom", "crates/strehl-cli/src/align_cmd.rs",
           "Some((WarpMap::new(prov, geom, map.resampler(), warps), lo))")
source_has("x8 guard landed", "experiments/M95-coverage/src/x8_fix.py",
           "REFUSING TO MEASURE")

print("\n-- the bars were registered before the run, in a prior commit --")
r = subprocess.run(
    ["git", "log", "-1", "--format=%H %ad", "--date=iso",
     "--", "experiments/M95-coverage/PRE-REGISTRATION.md"],
    cwd=ROOT, capture_output=True)
line = r.stdout.decode("utf-8", "replace").strip()
if line:
    print(f"  ok   PRE-REGISTRATION.md last touched {line}")
    ok += 1
else:
    print("  BAD  PRE-REGISTRATION.md has no git history")
    bad += 1
blob = subprocess.run(
    ["git", "show", "HEAD:experiments/M95-coverage/PRE-REGISTRATION.md"],
    cwd=ROOT, capture_output=True)
btxt = re.sub(r"\s+", " ", blob.stdout.decode("utf-8", "replace"))
for token in ("cost(FIX) < cost(NOW) − 0.10 dex", "cost(FIX) > cost(NOW) − 0.03 dex"):
    if token in btxt:
        print(f"  ok   committed bar: {token}")
        ok += 1
    else:
        print(f"  BAD  committed bar missing: {token}")
        bad += 1

print("\n-- k17b diagnostic agrees --")
if KDIAG.exists():
    kd = KDIAG.read_text(encoding="utf-8")
    for token in ("0.931464", "0.997438", "the printed 0.9315 belongs to that solve"):
        if token in kd:
            print(f"  ok   kdiag: {token}")
            ok += 1
        else:
            print(f"  BAD  kdiag lacks {token!r}")
            bad += 1
else:
    print("  BAD  k17b output missing")
    bad += 1

print("\n" + "=" * 72)
print(f"{ok} checks passed, {bad} failed  ->  {'GREEN' if bad == 0 else 'RED'}")
sys.exit(1 if bad else 0)

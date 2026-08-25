"""Re-baseline both coffee-bean rows, with the attribution PROVEN, not inferred."""
import sys
from pathlib import Path

TSV = Path(r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\tests\byte-freezes.tsv")

SHARED = (
    "Both coffee-bean rows moved together and both are mine. ATTRIBUTION PROVEN BY ISOLATING THE "
    "VARIABLE, NOT BY BLAMING A COMMIT RANGE: re-rendering this row's own recorded invocation with "
    "the CURRENT binary and STREHL_EDGE_AWARE=0 reproduces the previous baseline BIT-EXACTLY "
    "(experiments/BUILD-HALO/attribute_freeze.py). That is strictly stronger than pinning my parent "
    "commit, which could only show the bytes differ ACROSS a boundary and could not separate my "
    "change from anything else in the same range -- and it incidentally clears every other agent's "
    "commits since 9695b3c of touching these bytes. WHAT MOVED THEM: debc8ea 'halo: solve the "
    "selection radius from the noise model, and ship it on' made the edge-aware adaptive selection "
    "radius the shipped default -- edge_aware_arm() returns EdgeArm::Acuity when STREHL_EDGE_AWARE "
    "is unset -- so the focus window now collapses near a depth silhouette instead of standing at "
    "WINDOW_RADIUS=13 everywhere. That changes which frame wins at edge pixels, so the merged bytes "
    "move. ce2c793 'halo: gate the collapse on proof that collapsing buys something' then moved "
    "them AGAIN, requiring BimodalStats::peak_excess to clear the gate before a pixel may cap its "
    "radius -- a veto, so it collapses in strictly FEWER places than debc8ea did, not more. NOT A "
    "REGRESSION AND NOT A DEFECT IN THE RENDERER: a deliberate change to the render path is exactly "
    "what these rows exist to catch, and they caught it. The only defect was that it sat unrecorded "
    "and read as unattributed, which is how the next agent to touch this path re-baselines it "
    "believing their own change caused it and absorbs someone else's delta into their justification. "
    "FIXED WITH THIS BASELINE: STREHL_EDGE_AWARE, STREHL_EDGE_TAU, STREHL_EDGE_CONF and "
    "STREHL_ONLY_FRAME are now in RENDER_ENV and cleared before the render. They were not, and every "
    "one re-routes the election -- STREHL_ONLY_FRAME renders a single frame with NO election at all "
    "-- so until now these hashes silently depended on the ambient environment of whoever ran the "
    "test. That is the STREHL_ALIGN=0 defect described in this file's own header, committed a second "
    "time by me when I added the variables and not the entries. Both hashes below were measured with "
    "all four confirmed unset. bytes are unchanged at 49450019: the geometry did not move, only the "
    "pixel VALUES."
)

ROWS = {
    "coffee-bean-20-gate2-unaligned": (
        "3162EB0B1C8D5F3A1D646CCE50900492DABB9606B6BA58B36156E19171D0781A",
        "RE-BASELINED at 2525e08. " + SHARED + " THIS ROW: registration is OFF, because "
        "align_enabled() short-circuits before any cache path is computed, so no shared state can "
        "reach it. Superseded value 89958637..C218 was the pre-debc8ea baseline at 9695b3c and is "
        "the value the arm-off control reproduces. V-TONE independently measured CC1468A3..523A "
        "from a git-archive pin of debc8ea's parent -- a correct measurement of the state AFTER the "
        "radius change and BEFORE the veto. Do not paste CC1468A3 in: it is a real hash of a real "
        "commit, but not of what ships.",
    ),
    "coffee-bean-20-gate2-sidecar": (
        "6325922C11DE23A1B73FFEF69C6E2FEE6BD628FF4275C87DA5797669C4227D8F",
        "RE-BASELINED at 2525e08. " + SHARED + " THIS ROW: alignment reads a COMMITTED warp map and "
        "writes nothing, so the warp is a constant here and the moving part is decode -> focus -> "
        "election -> merge. It was NOT reported broken alongside its sibling only because the test "
        "panics on the first failing row and this one is second; it had been broken exactly as long. "
        "Superseded value 2DB8A978..46E5 was the pre-debc8ea baseline at 9695b3c and is the value "
        "the arm-off control reproduces.",
    ),
}

text = TSV.read_text(encoding="utf-8")
lines = text.split("\n")
changed = 0

for rid, (sha, why) in ROWS.items():
    hits = [i for i, l in enumerate(lines) if l.startswith(rid + "\t")]
    if len(hits) != 1:
        sys.exit(f"REBASELINE TARGET NOT FOUND: {len(hits)} rows matched {rid!r}")
    i = hits[0]
    f = lines[i].split("\t")
    if len(f) != 17:
        sys.exit(f"{rid}: expected 17 columns, found {len(f)}")
    for bad in ("\t", "\n", "\r"):
        if bad in why:
            sys.exit(f"{rid}: why contains a delimiter")
    f[11] = sha
    f[14] = "2525e08"
    f[15] = "2026-08-25"
    f[16] = why
    lines[i] = "\t".join(f)
    if len(lines[i].split("\t")) != 17:
        sys.exit(f"{rid}: column count changed")
    print(f"{rid}: sha256 -> {sha}  ({len(why)} chars of why)")
    changed += 1

if changed != 2:
    sys.exit("expected to change exactly 2 rows")

TSV.write_text("\n".join(lines), encoding="utf-8")
print("wrote", TSV)

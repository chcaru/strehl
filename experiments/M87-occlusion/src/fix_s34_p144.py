"""M87 -- adjudicate ORCH's fact 1446 cache-contamination warning against M87.

ORCH named M87 as one of the milestones whose comparisons the unkeyed stack
cache could silently corrupt, and asked for the run/perturb/re-run control.
That control is not the strongest evidence available here, so this records the
stronger one: M87's numbers cannot reach the stack cache at all, on two
structural grounds verified in the Rust source, plus a four-way hash agreement.

Same trap as the P143 script: `control_s29` asserts three sentences occur
exactly once, so the new prose must not reproduce them.  Guarded by FORBIDDEN
and re-checked after the write.  The figure `100.00%` is avoided entirely --
that is the exact collision P143 is about.
"""
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

FORBIDDEN = [
    "It measured **100.00%** and printed PASS.",
    "It measured **100.00%** and printed **PASS**.",
    "| **100.00%** | 0.4137 |",
]

ROW = (
    "| P144 | **M87 is structurally out of reach of the unkeyed stack cache, "
    "and the warning that named it is superseded at HEAD.** Fact 1446 reports "
    "that `StackIdentity` omits `reference` and `resampler`, so an identical "
    "command line can return different bytes. Two grounds, both read in the "
    "Rust rather than relayed: (a) **no M87 script invokes the binary** -- "
    "every cube is a `rawpy` decode of the `.ARW` files (`m87lib.py:124,145`), "
    "and `fix_audit.py:58` *asserts* `scripts_invoking_binary` is 0 across the "
    "104 measurement scripts, so this is a guarded property and not a lucky "
    "observation; (b) the one render-dependent line, the §33/§34 gate ladder, "
    "consumes ORCH's four pinned TIFFs, which were rendered with "
    "`STREHL_WARPMAP` set -- and `merge_cmd.rs:1135` resolves that to *an "
    "explicitly named sidecar ... otherwise the normal discover-or-solve "
    "path*, so the cache is bypassed, nothing is written, and a bracket "
    "mismatch is a refusal (`tests/byte-freeze.rs:69`). | **The control ORCH "
    "prescribed would have been the weakest evidence in this row, so I ran a "
    "stronger one.** Empirically the gate-4.00 arm still hashes "
    "`E400A63A...7112` on disk, matching three independent records: ORCH's "
    "provenance note, the `provenance.gate_4_sha256` this report's own §34 run "
    "stored at measurement time, and fact 1373's kernel A/B from a *different "
    "session and a different exposure code path*. All four arms carry distinct "
    "hashes at one byte length, so the cache never collapsed them. But a "
    "repeated hash alone cannot separate *correct bytes twice* from *the same "
    "stale bytes twice* -- only ground (b) does that, which is why the source "
    "read is load-bearing and the hashes are corroboration. Fact 1446 was "
    "measured before `69f7b4c`; at HEAD `solve_config_key` hashes `reference`, "
    "`spans`, `resampler` and every `SOLVE_ENV` variable, so **both** omitted "
    "fields are keyed, exactly as ORCH's own later fact 1476 concluded. | "
    "MEASURED |"
)

ANCHOR = "Three limits, stated rather than buried."

PARA = """**ORCH's cache-contamination warning does not reach this report, and I
checked that in the Rust rather than by asserting it.** Fact 1446 measured an
identical `strehl stack` command line returning either of two hashes depending
on whether an unrelated `align --reference 40` ran first, because
`StackIdentity` covers the frame set but not `reference` and not `resampler`.
M87 was named explicitly, alongside every other milestone running an A/B.

The prescribed control is run the arm, perturb the cache, re-run the arm, and
compare. I did not make that the primary evidence, because for this report it
is the weakest thing available. **The first ground is that M87 never calls the
binary.** Every number in this document is computed in Python from cubes
decoded straight out of the `.ARW` files with `rawpy`; the merge in §25 is
*reproduced* from the frame cube and the selection map rather than read back
from a rendered TIFF. That is not an observation I made once -- `fix_audit.py`
asserts it on every run, and it currently reports 0 binary invocations across
104 measurement scripts.

**The second ground covers the one place I do consume a render.** The §33/§34
gate ladder runs on ORCH's four pinned TIFFs, and those were rendered with
`STREHL_WARPMAP` pointing at a fixed sidecar. `merge_cmd.rs:1135` documents
that path as resolving an explicitly named sidecar *instead of* the normal
discover-or-solve route, and the byte-freeze suite adds that when the variable
is set nothing is written anywhere and a bracket mismatch is refused rather
than silently re-solved. So those renders never enter the code path the defect
lives in. ORCH's own fact 1476 reaches the same exemption for M113 and M110 on
exactly this reasoning.

**What the hashes add, and what they cannot.** The gate-4.00 TIFF on disk
still hashes `E400A63A...7112`, which agrees with ORCH's provenance note, with
the digest §34 recorded at the moment it measured, and with fact 1373's
catmull-rom arm from a separate session and a separate exposure code path. The
four arms hash to four distinct values at one byte length. That is a four-way
agreement where the control asked for a two-way one -- but I want to be exact
about its limit: **if the cache had served the same wrong bytes on both
occasions, the hashes would agree just as well.** A repeated digest cannot
tell a correct render from a consistently stale one. Only the warpmap bypass
can, which is why the source read carries this and the hashes merely
corroborate it.

**And the warning is stale, which I would not have known from the row alone.**
Fact 1446 was measured before commit `69f7b4c`, an ancestor of HEAD; at HEAD
`solve_config_key` hashes `reference`, `spans`, `resampler` and every
`SOLVE_ENV` variable into the sidecar path, and a recorded resampler that
disagrees with the wanted one forces a re-solve. Both fields the warning names
as missing are now in the key. ORCH had already published that correction as
fact 1476 -- **the fleet-wide alarm and its own retraction were live in the
corpus at the same time**, which is the ordinary condition of a corpus a dozen
agents write concurrently, and the reason a warning is worth re-deriving even
when it arrives from the coordinator marked highest severity."""


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P144 |" in raw:
        print("P144 already present -- nothing to do")
        return

    bare = ROW.replace("\\|", "")
    assert bare.count("|") == 5, "fact row needs exactly 5 unescaped pipes"
    assert ROW.count("`") % 2 == 0, "fact row backtick count is odd"
    assert PARA.count("`") % 2 == 0, "paragraph backtick count is odd"
    for f in FORBIDDEN:
        if f in ROW or f in PARA:
            sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)
    if "100.00%" in ROW or "100.00%" in PARA:
        sys.exit("NEW PROSE QUOTES 100.00%% -- the exact P143 collision")

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-p144.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P143 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P143 row, found %d" % len(idx))
    lines.insert(idx[0] + 1, ROW)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    for f in FORBIDDEN:
        n = after.count(f)
        if n != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r now occurs %dx" % (f, n))
    if "| P144 |" not in after:
        sys.exit("POST-WRITE CHECK FAILED: P144 missing")
    print("added P144 and the 34.9 paragraph; %d lines" % (after.count("\n") + 1))


if __name__ == "__main__":
    main()

# V-H2H2: is my byte-freeze registration still in HEAD, and can this check FAIL?
#
# WHAT THIS FILE USED TO BE, AND WHY IT WAS NOT EVIDENCE.
#
#     print("STREHL_PYRAMID_SIGNIFICANCE in HEAD:",
#           '"STREHL_PYRAMID_SIGNIFICANCE",' in b)
#
# A bare substring test over the whole file. It has the defect ORCH flagged
# across the fleet: a presence test is satisfied by ANY occurrence of the
# string, including one inside a comment, and it certifies nothing about the
# thing it is supposed to certify -- that the variable is a live entry of the
# `RENDER_ENV` allowlist. `byte-freeze.rs` already contains 2 occurrences of
# `STREHL_SOFT_GATE`, one of which is prose. And I had never once shown the
# check printing False, so I did not know it could.
#
# THE CLAIM EACH CHECK NOW CERTIFIES, stated so it can be pinned:
#   "NAME is a live, uncommented element of the RENDER_ENV array in HEAD."
#
# So the check locates the array by its declaration, slices it at its closing
# `];`, discards comment lines INSIDE that slice, and requires exactly one
# surviving element. An occurrence anywhere else in the file -- prose, a
# different array, a doc comment -- is no longer able to satisfy it.
#
# COMMISSIONING. Five mutants are applied to an in-memory copy of the blob and
# each must land (a mutation that silently fails to apply is a green check about
# nothing, so a miss is a hard error, not a warning). Both the OLD presence test
# and the NEW pinned test are run against every mutant, and the two are printed
# side by side, because the point is not that the new one passes -- it is that
# the old one goes GREEN on a defect, measured rather than asserted.
#
#   NULL             unmodified                        -> expect PRESENT
#   DELETE           entry line removed                -> expect ABSENT
#   COMMENT          entry line commented out          -> expect ABSENT
#   DECOY_IN_ARRAY   entry deleted, re-added as a
#                    COMMENT inside the array          -> expect ABSENT
#   DECOY_OUTSIDE    entry deleted, re-added as text
#                    after the array closes            -> expect ABSENT
#
# The two DECOY mutants are the conclusion-flipping ones: the registration is
# genuinely gone in both, and a presence test cannot tell. They are not required
# to be valid Rust -- this verifier reads text, and what is under test is the
# verifier, not the compiler.

import re
import subprocess

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
PATH = "crates/strehl-cli/tests/byte-freeze.rs"
DECL = "const RENDER_ENV: &[&str] = &["
GUARDED = ["STREHL_PYRAMID_SIGNIFICANCE", "STREHL_SOFT_GATE"]


def head_blob():
    out = subprocess.run(["git", "show", f"HEAD:{PATH}"],
                         capture_output=True, cwd=REPO)
    assert out.returncode == 0, f"git show failed: {out.stderr.decode(errors='replace')}"
    # The blob is what git stores: LF only. Comparing it against a CRLF worktree
    # file byte-for-byte reports a spurious difference on Windows under
    # core.autocrlf=true -- measured today: 4156 bytes of delta, exactly the
    # CRLF count, with the two identical after normalisation.
    return out.stdout.decode("utf-8")


def allowlist(text):
    """The RENDER_ENV elements in `text`, comments discarded."""
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if DECL in l]
    if len(starts) != 1:
        raise AssertionError(
            f"expected exactly 1 `{DECL}`, found {len(starts)} -- the array has "
            "moved or been renamed and every claim in this file is VOID")
    i = starts[0]
    end = next((j for j in range(i + 1, len(lines)) if lines[j].strip() == "];"), None)
    assert end is not None, "RENDER_ENV is not closed by `];` -- claim VOID"
    return [l for l in lines[i + 1:end] if not l.strip().startswith("//")]


def pinned(text, name):
    return sum(1 for l in allowlist(text) if f'"{name}",' in l) == 1


def presence(text, name):
    return f'"{name}",' in text


def entry_line(text, name):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines)
            if f'"{name}",' in l and not l.strip().startswith("//")]
    assert len(hits) == 1, f"{name}: expected 1 live entry line, found {len(hits)}"
    return hits[0]


def mutate(text, name, kind):
    lines = text.split("\n")
    i = entry_line(text, name)
    original = lines[i]
    if kind == "NULL":
        return text
    if kind == "DELETE":
        del lines[i]
    elif kind == "COMMENT":
        lines[i] = "    // " + original.strip()
    elif kind == "DECOY_IN_ARRAY":
        lines[i] = f'    // {name} used to live here: "{name}",'
    elif kind == "DECOY_OUTSIDE":
        del lines[i]
        end = next(j for j in range(i, len(lines)) if lines[j].strip() == "];")
        lines.insert(end + 1, f'// stale mention: "{name}",')
    else:
        raise AssertionError(f"unknown mutant {kind}")
    out = "\n".join(lines)
    if kind != "NULL":
        assert out != text, f"mutant {kind} did not change the text"
        # The registration must actually be gone, or the mutant tests nothing.
        assert not pinned(out, name) or kind == "NULL", (
            f"mutant {kind} left {name} still registered -- mutant is inert")
    return out


blob = head_blob()
print(f"HEAD:{PATH}  {len(blob)} bytes, {len(allowlist(blob))} live RENDER_ENV entries\n")

print("LIVE STATE")
for name in GUARDED:
    print(f"  {name:-<32} registered: {pinned(blob, name)}")
argv_hits = sum(1 for l in blob.split("\n")
                if '"estimator".to_string(),' in l and not l.strip().startswith("//"))
print(f"  {'--merge estimator hardcoded in argv':-<32} live occurrences: {argv_hits}")

MUTANTS = ["NULL", "DELETE", "COMMENT", "DECOY_IN_ARRAY", "DECOY_OUTSIDE"]
EXPECT = {"NULL": True}

print("\nCOMMISSIONING -- old presence test vs new pinned test")
print(f"  {'mutant':<16} {'expect':<8} {'OLD presence':<14} {'NEW pinned':<12} outcome")
old_missed = new_missed = 0
checks = 0
for name in GUARDED:
    for kind in MUTANTS:
        want = EXPECT.get(kind, False)
        text = mutate(blob, name, kind)
        o, n = presence(text, name), pinned(text, name)
        checks += 1
        if o != want:
            old_missed += 1
        if n != want:
            new_missed += 1
        verdict = "ok" if n == want else "NEW FAILED"
        if o != want:
            verdict += "   <- OLD test green on a defect"
        print(f"  {kind:<16} {str(want):<8} {str(o):<14} {str(n):<12} {verdict}")
    print()

print(f"mutants run {checks}   OLD test wrong on {old_missed}   NEW test wrong on {new_missed}")
if new_missed:
    raise SystemExit("NEW check failed commissioning; it may not be quoted.")
print("NEW check commissioned: it has been shown to fail, on defects the old one passed.")

"""Generate the merge_cmd.rs exposure wiring as a PREPARED PATCH -- do not apply.

WHY THIS IS A PATCH AND NOT AN EDIT
===================================
`crates/strehl-cli/src/merge_cmd.rs` is live under BUILD-PLUGIN's gate sweep.
We share one working tree, so two agents editing one file clobber each other
with no merge conflict to warn anyone. ORCH holds the file and will hand it
over; until then this lane produces the change as a patch and applies nothing.

WHY IT IS GENERATED RATHER THAN HAND-WRITTEN
--------------------------------------------
A hand-written unified diff carries hand-written hunk offsets, and those are
wrong the moment the owning lane's commits move a line. This builds a modified
copy in $TEMP, diffs it against the real file with `git diff --no-index`, and
then CHECKS the result with `git apply --check` -- which verifies applicability
without touching the tree. A patch nobody has tried to apply is a guess.

WHAT THE CHANGE IS
------------------
The exposure cancellation is exact because `--srgb`'s tone anchors are linear
in the data: an upstream gain `g` scales both, `s -> s/g`, and normalised `y`
is invariant. The engine fix already committed (9cb7f5d9) puts the gain on the
far side of that normalisation via `Develop::exposure_gain`, applied in
`develop_pixel` after `t.gain()`. Both writer sites in `merge_cmd.rs` build
their `Develop` through `space.develop(...)` and therefore still carry the
default `exposure_gain: 1.0`, so the SHIPPING path (`strehl stack` ->
`merge_cmd::run`, `main.rs:223`) still cancels.

Two call sites need the builder chained on:
  :6962  demosaic branch  -> write_demosaiced
  :7107  binned branch    -> write_binned

plus a guard test. The guard is a SOURCE-level assertion, matching the pattern
already used at `main.rs:1259` (`include_str!("main.rs")` + `contains`). That
is deliberately chosen: the behavioural claim -- that a commanded gain reaches
the pixels -- is already asserted by
`image_out::tests::an_exposure_request_changes_the_pixels_and_not_only_the_banner`,
which regresses the LSQ slope and was commissioned RED on the original defect.
What is NOT asserted anywhere is the *wiring*: that every `Develop` handed to a
writer carries the gain. A behavioural test of that needs RAW frames and cannot
live in a unit test; a source guard can, and it fails exactly when someone adds
a third writer and forgets the builder -- which is precisely how this defect
reached the shipping path in the first place.

The guard counts and PARTITIONS rather than merely searching: it requires the
number of writer-feeding `space.develop(` sites to equal the number chained
with `.with_exposure_gain(`, so a new unchained site fails loudly instead of
being invisible to a `contains` that already found one match elsewhere.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REL = "crates/strehl-cli/src/merge_cmd.rs"
SRC = REPO / REL
OUTDIR = REPO / "experiments" / "BUILD-DEFECT" / "patches"
PATCH = OUTDIR / "merge_cmd-exposure-wiring.patch"

# Each edit is anchored on a FULL unique line. A bare `replace(x, y, 1)` will
# happily land on the first coincidental occurrence; every anchor here is
# checked for uniqueness and the script hard-errors if one does not land.
EDITS = [
    (
        "    let dev = space.develop(matrix.map(|r| r.with_saturation(levels, gains, applied.gain())));\n",
        "    // `.with_exposure_gain` is what carries the commanded exposure past the\n"
        "    // tone normalisation. Without it the gain folded into `norm` below is\n"
        "    // divided straight back out by `--srgb`'s auto-tone, because both tone\n"
        "    // anchors are linear in the data (measured: a commanded 64x span\n"
        "    // delivered 1.0000000, bit-identical across 98,898,048 samples).\n"
        "    // See `Develop::exposure_gain` and docs/research/BUILD-DEFECT.md S14.\n"
        "    let dev = space\n"
        "        .develop(matrix.map(|r| r.with_saturation(levels, gains, applied.gain())))\n"
        "        .with_exposure_gain(applied.gain());\n",
    ),
    (
        "        let dev = space.develop(matrix.map(|r| r.with_saturation(levels, gains, eg)));\n",
        "        // Same reason as the demosaic branch above: the gain in `norm` is\n"
        "        // cancelled by the tone stage, so it must also be applied on the far\n"
        "        // side of that normalisation. This is the identity when no exposure\n"
        "        // was asked for -- `exp2(0)` is exactly 1.0 and `x * 1.0` is `x`\n"
        "        // bit-for-bit -- so the byte-frozen linear renders cannot move.\n"
        "        let dev = space\n"
        "            .develop(matrix.map(|r| r.with_saturation(levels, gains, eg)))\n"
        "            .with_exposure_gain(eg);\n",
    ),
]

GUARD = '''
    /// Every `Develop` handed to a writer must carry the exposure gain.
    ///
    /// This is a WIRING guard, and it exists because the wiring is exactly what
    /// failed. The behavioural claim -- that a commanded exposure reaches the
    /// pixels -- is asserted by
    /// `image_out::tests::an_exposure_request_changes_the_pixels_and_not_only_the_banner`,
    /// which regresses the LSQ slope against the unexposed arm and was
    /// commissioned RED by planting the original defect. That test passes
    /// happily while this file forgets to pass the gain in, because it never
    /// sees this file.
    ///
    /// The defect being guarded: `--exposure` was applied upstream in `norm`
    /// and then divided straight back out by `--srgb`'s auto-tone, whose two
    /// anchors are both linear in the data. MEASURED before the fix: a
    /// commanded 64x span between `--exposure 3` and `--exposure -3` delivered
    /// a regression slope of 1.0000000 with all 98,898,048 samples
    /// bit-identical. The only bytes that moved were the banner inside
    /// `ImageDescription`, which is why a whole-file hash read it as working.
    ///
    /// This COUNTS and PARTITIONS rather than searching. A substring check is
    /// satisfied by any one occurrence, so it would still pass on the day a
    /// third writer is added without the builder -- the same class of blind
    /// spot that let the original defect ship. Requiring the two counts to be
    /// equal makes an unchained site fail loudly.
    #[test]
    fn every_writer_develop_carries_the_exposure_gain() {
        let src = include_str!("merge_cmd.rs");
        // The needles are assembled at runtime so that this test cannot match
        // its OWN source text. Spelled as literals, each needle would occur
        // inside this function and inflate the count it is used to take -- the
        // guard would then pass or fail for reasons having nothing to do with
        // the writers it is watching. A self-counting check is not a check.
        let needle_dev = [".", "develop("].concat();
        let needle_gain = [".", "with_exposure_gain("].concat();
        let developed = src.matches(needle_dev.as_str()).count();
        let carried = src.matches(needle_gain.as_str()).count();
        assert!(
            developed > 0,
            "no develop site was found at all -- this guard has lost its \\
             target and is asserting nothing"
        );
        assert_eq!(
            developed, carried,
            "{developed} writer develop site(s) but only {carried} carry the \\
             exposure gain builder. An unchained writer silently cancels the \\
             commanded exposure -- see docs/research/BUILD-DEFECT.md S14."
        );
    }
}
'''


def main():
    text = SRC.read_text(encoding="utf-8")
    orig = text

    for anchor, replacement in EDITS:
        n = text.count(anchor)
        if n != 1:
            sys.exit(
                f"ANCHOR DID NOT LAND ({n} occurrences), refusing to emit a "
                f"patch built on a guess:\n{anchor!r}"
            )
        text = text.replace(anchor, replacement, 1)

    # The guard goes at the end of the existing `mod tests`, i.e. the final
    # closing brace of the file.
    if not text.endswith("}\n"):
        sys.exit("merge_cmd.rs does not end with a closing brace as expected")
    text = text[: -len("}\n")] + GUARD.lstrip("\n")

    if text == orig:
        sys.exit("the generated text is identical to the source; nothing to patch")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        mod = Path(td) / "merge_cmd.rs"
        mod.write_text(text, encoding="utf-8", newline="")
        r = subprocess.run(
            ["git", "diff", "--no-index", "--", str(SRC), str(mod)],
            cwd=REPO,
            capture_output=True,
        )
        # `git diff --no-index` exits 1 when the files differ. That is success.
        if r.returncode not in (0, 1):
            sys.exit(f"git diff failed: {r.stderr.decode(errors='replace')}")
        diff = r.stdout.decode("utf-8")

    # Rewrite the temp paths to repo-relative ones so the patch applies with
    # `git apply -p1` from the repo root.
    lines = []
    for ln in diff.splitlines(keepends=True):
        if ln.startswith("diff --git "):
            lines.append(f"diff --git a/{REL} b/{REL}\n")
        elif ln.startswith("--- "):
            lines.append(f"--- a/{REL}\n")
        elif ln.startswith("+++ "):
            lines.append(f"+++ b/{REL}\n")
        else:
            lines.append(ln)
    diff = "".join(lines)

    PATCH.write_text(diff, encoding="utf-8", newline="")
    added = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    hunks = sum(1 for l in diff.splitlines() if l.startswith("@@"))
    print(f"wrote {PATCH}")
    print(f"  {hunks} hunk(s), +{added} / -{removed} lines")

    # A patch nobody has tried to apply is a guess. `--check` verifies without
    # writing anything, which is the whole point: the file stays untouched.
    chk = subprocess.run(
        ["git", "apply", "--check", "-p1", str(PATCH)], cwd=REPO, capture_output=True
    )
    if chk.returncode != 0:
        print("APPLIES: NO")
        print(chk.stderr.decode(errors="replace"))
        return 1
    print("APPLIES: YES (verified with `git apply --check`; nothing was written)")

    after = SRC.read_text(encoding="utf-8")
    print(f"source untouched: {'YES' if after == orig else 'NO -- INVESTIGATE'}")
    return 0 if after == orig else 1


if __name__ == "__main__":
    sys.exit(main())

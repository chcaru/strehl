"""Activate M109's highlight ceiling in `strehl stack` (merge_cmd.rs).

DO NOT RUN THIS WITHOUT ORCH'S AUTHORISATION. `merge_cmd.rs` is M97's file and
was DIRTY when this script was written, i.e. M97 had uncommitted work in the
tree. If M97 commits while this edit is applied, M97 carries it in unknowingly.

Why a script instead of a line-numbered patch: the line numbers in the first
version of the routing request (2803 / 2958) were already stale by the time it
was read -- the file had grown to 4125 lines and the sites had moved to 2924 /
3079. Anchors survive that; line numbers do not. Every anchor below is a UNIQUE
FULL LINE and the script hard-errors unless it lands exactly the expected number
of times, so a miss is loud rather than silent.

The two `Develop` sites differ in indentation (4 spaces vs 8), which is what
makes the full-line anchors unique -- a trimmed match would hit both.

WHAT IT DOES, and why each edit is needed:

  1. DELETE the early binding. It sits BEFORE `let applied = match exposure`,
     so it cannot see the exposure gain. Nothing reads it between its binding
     and the demosaic branch (verified: the only readers are the demosaic
     write, the binned write and two `caveat()` calls), so it must be removed
     rather than shadowed -- a shadowed binding with no reader is an unused
     variable, and this workspace builds clippy with `-D warnings`.

  2. INSERT a ceiling-carrying binding immediately before `if demosaic {`,
     where `levels`, `gains` and `applied` are all in scope.

  3. REPLACE the binned branch's own binding in place. It shadows, so edit 2
     does not reach it. `eg` is already bound there.

The byte-frozen measurement path is NOT touched and cannot be: it calls
`write_rgb16` and never constructs a `Develop` at all.

Usage:  python activate_stack_fix.py --check     # verify anchors, write nothing
        python activate_stack_fix.py --apply
        python activate_stack_fix.py --revert     # undo, using the same anchors
"""

import sys
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[3] / "crates" / "strehl-cli" / "src" / "merge_cmd.rs"
)

OLD_EARLY = "\n    let dev = image_out::Develop { matrix, srgb };\n"
OLD_BINNED = "\n        let dev = image_out::Develop { matrix, srgb };\n"
ANCHOR_IF = "\n    if demosaic {\n"

NEW_BEFORE_IF = """    // M109: the matrix must not be handed a triple in which one channel is
    // pinned at the container maximum while white balance has carried the
    // others past it -- that is what renders blown neutral white magenta.
    // See `docs/research/M109-highlights.md`.
    let dev = image_out::Develop {
        matrix: matrix
            .map(|r| r.with_ceiling(color::saturation_ceiling(levels, gains, applied.gain()))),
        srgb,
    };
"""

NEW_BINNED = """        let dev = image_out::Develop {
            matrix: matrix
                .map(|r| r.with_ceiling(color::saturation_ceiling(levels, gains, eg))),
            srgb,
        };
"""


def read():
    with open(TARGET, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write(t):
    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(t)


def require(text, needle, n, label):
    got = text.count(needle)
    if got != n:
        raise SystemExit(
            f"ANCHOR MISS [{label}]: expected {n} occurrence(s), found {got}.\n"
            f"  anchor: {needle!r}\n"
            f"  The file has changed. Re-derive the anchors; do NOT edit by line number."
        )
    print(f"  ok  [{label}] {n} occurrence(s)")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if not TARGET.is_file():
        raise SystemExit(f"not found: {TARGET}")
    t = read()
    print(f"{TARGET}  ({len(t.splitlines())} lines)")

    if mode == "--revert":
        require(t, NEW_BEFORE_IF, 1, "inserted block")
        require(t, NEW_BINNED, 1, "binned block")
        t = t.replace("\n" + NEW_BEFORE_IF + ANCHOR_IF, ANCHOR_IF, 1)
        t = t.replace("\n" + NEW_BINNED, OLD_BINNED, 1)
        t = t.replace(ANCHOR_IF, OLD_EARLY + ANCHOR_IF, 1)
        write(t)
        print("REVERTED (re-run --check to confirm)")
        return 0

    print("verifying anchors:")
    require(t, OLD_EARLY, 1, "early Develop (4-space)")
    require(t, OLD_BINNED, 1, "binned Develop (8-space)")
    require(t, ANCHOR_IF, 1, "if demosaic {")
    if OLD_EARLY not in t.split(ANCHOR_IF)[0]:
        raise SystemExit("ORDER MISS: the early binding is not before `if demosaic {`")
    print("  ok  [order] early binding precedes `if demosaic {`")

    if mode == "--check":
        print("\nCHECK ONLY -- nothing written. Re-run with --apply to patch.")
        return 0
    if mode != "--apply":
        raise SystemExit(f"unknown mode {mode!r}")

    t2 = t.replace(OLD_EARLY, "\n", 1)
    t2 = t2.replace(ANCHOR_IF, "\n" + NEW_BEFORE_IF + ANCHOR_IF, 1)
    t2 = t2.replace(OLD_BINNED, "\n" + NEW_BINNED, 1)
    if t2 == t:
        raise SystemExit("NO-OP: nothing changed, refusing to claim success")
    write(t2)
    print("\nAPPLIED. Now:  cargo build --release  &&  cargo test --release")
    print("Byte-freeze must still pass: STREHL_FREEZE_REQUIRE=1 cargo test --release")
    return 0


if __name__ == "__main__":
    sys.exit(main())

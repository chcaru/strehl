"""Update M100's ledger status and add the M105 / M106 rows.

Rule 41: every dispatched agent gets a row. M105 was stood down rather than
completed and still needs one -- a stem that was dispatched and killed is part
of the record, and the reason it was killed is the useful part.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\AGENTS.md"

M100_OLD = ("`experiments/M100-exposure/`, `C:\\dev\\strehl-out\\M100\\` | dispatched, running |")
M100_NEW = (
    "`experiments/M100-exposure/`, `C:\\dev\\strehl-out\\M100\\` | **complete; patch APPLIED by the orchestrator "
    "at `925d03d`, folded as facts 1348-1349.** M100 built the whole feature in `color.rs`, tested it, and routed "
    "verbatim `main.rs` / `merge_cmd.rs` patches to me **which I then left unapplied for hours while the owner "
    "judged renders 1.5-3.7 stops dark** (fact 1346). Applied at last: nine `merge_cmd.rs` hunks verbatim, two "
    "`main.rs` anchors re-derived because **I had invalidated them myself** applying M95 at `56bd846`. All bars "
    "green at HEAD -- 24 and 59 tests, both refusals, `--srgb --exposure 0` byte-identical to `--srgb`, and the "
    "auto-exposure round trip byte-identical to its own printed flag, at **+1.48 stops**, the same value M100 "
    "recorded before four other milestones landed on the merge. **Its four recorded absolute hashes all failed, "
    "including the byte-freeze** -- proven not to be this patch by a restore-touch-rebuild control, and handed to "
    "M106. Its flagged M95 interaction was ruled **ACCEPTED**. |"
)

NEW_ROWS = [
    ("`M105`",
     "**DISPATCHED ON A FALSE PREMISE AND STOOD DOWN WITHIN 20 MINUTES.** I repurposed an idle agent to build "
     "exposure into the CLI, briefing it that *there is no exposure logic in the CLI at all* and telling it to "
     "write `crates/strehl-cli/src/exposure.rs` from scratch. **The premise was false and the search behind it was "
     "scoped to one crate of two**: M100 had already built, tested and shipped the entire feature in "
     "`crates/strehl-core/src/color.rs`. Caught by reading the ledger row that names the other crate -- a row I had "
     "written by hand an hour earlier. Killed before it built anything.",
     "-- (nothing written)",
     "**stood down (`14f72658`); no code, no report, no cost beyond the dispatch.** Recorded because rule 41 counts "
     "dispatches, not successes, and because the reason is the useful part: fact 1347 and discipline 668 both come "
     "from this stem. It is the fifth instance of the confirm-in-general-never-check-the-instance class, after "
     "facts 1297, 1304, 1324 and 1341."),

    ("`M106`",
     "**THE BYTE-FROZEN MEASUREMENT PATH IS NOT FROZEN, AND NOBODY DECLARED IT.** `merge_cmd.rs` documents the "
     "default no-flag render as *\"The measurement path. **Byte-frozen.**\"* and states that every quality number in "
     "the corpus was measured on the file it writes. M100 recorded that render's SHA-256 as `54A5E20F...` for "
     "**three** binaries spanning a pre-M87 HEAD; at `925d03d` the identical command gives `CF266004...`. I have "
     "already excluded my own exposure patch by restore-touch-rebuild and told M106 not to repeat it. Attribute the "
     "break to a commit and rule on each: `885e9f7` (alignment wired into `strehl stack`), `79dc8b3` (M97's warped "
     "merge, which measured that it *does not improve the image*), `52c6a52` (**M87's halo correction, shipped "
     "\"default OFF\" -- a falsifiable claim that is false if that commit moved this hash**), and M95's three. Then "
     "answer the question that makes it matter: **measure** the max DN delta, RMS and fraction of pixels differing "
     "between M100's baseline and HEAD, because a freeze that broke by 1 DN on 0.01% of pixels is bookkeeping and "
     "one that moved every pixel is a corpus-validity problem. Told to bisect in a **worktree**, since seven agents "
     "are live in the main tree and `align.rs` and `robust.rs` carry uncommitted work that is not its own.",
     "`docs/research/M106-freeze-attribution.md`",
     "dispatched, running (`a7cf3e3e`, `claude-opus-5`)"),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    n = text.count(M100_OLD)
    if n != 1:
        raise SystemExit(f"M100 STATUS ANCHOR FOUND {n} TIMES, need exactly 1")
    text = text.replace(M100_OLD, M100_NEW, 1)

    lines = text.split("\n")
    anchor = [i for i, l in enumerate(lines) if l.startswith("| `M104` / `M104b` |")]
    if len(anchor) != 1:
        raise SystemExit(f"M104 ROW FOUND {len(anchor)} TIMES, need exactly 1")

    rows = []
    for name, brief, files, status in NEW_ROWS:
        row = f"| {name} | {brief} | {files} | {status} |"
        p = row.count("|") - row.count("\\|")
        assert p == 5, f"{name}: {p} unescaped pipes, need 5"
        if re.search(rf"^\| {re.escape(name)} \|", text, re.M):
            raise SystemExit(f"{name} already in the ledger")
        rows.append(row)

    out = lines[:]
    out[anchor[0] + 1:anchor[0] + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"M100 status updated; added {len(rows)} rows after line {anchor[0]}")


if __name__ == "__main__":
    main()

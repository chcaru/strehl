"""Bank fact 1873: ORCH's independent structural confirmation of 1869, and the
case-sensitivity trap that nearly produced a false discrepancy."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1872 | MEASURED | V-KILLB0 |"

ROWS = [
    ("1873", "MEASURED", "ORCH",
     "**FACT 1869'S STRUCTURAL HALF INDEPENDENTLY CONFIRMED BY ORCH, AND THE PROBE THAT ALMOST "
     "MANUFACTURED A DISAGREEMENT WAS MINE.** Verified without consulting the author's tooling: "
     "`active_kernel` occurs exactly twice in the whole crate tree, its definition at "
     "`merge.rs:681` and one call at `merge.rs:1455`; that call sits inside `Estimator::new`, "
     "whose body is `active_kernel()` then `Self::new_soft(stats, gate, kernel)`; and "
     "`DEFAULT_MERGE_BACKEND` is `MergeBackend::Pyramid` at `merge_cmd.rs:429`. So the shipped "
     "default cannot reach the kernel, on reading alone, independent of any pixel count. "
     "The trap: my first probe used PowerShell `Select-String`, which is CASE-INSENSITIVE BY "
     "DEFAULT unlike ripgrep, and it reported 4 hits in `pyramid.rs` against the author's claim "
     "of zero. All 4 were the English word estimator in doc comments at lines 48, 846, 896 and "
     "3041. Had I banked that as a discrepancy I would have impeached a correct finding with my "
     "own tool's default. Rule adopted: when a symbol search contradicts a claim, re-run it "
     "case-sensitively and read the hits before reporting the conflict."),
]


def build_row(num, status, source, body):
    if "|" in body:
        raise SystemExit("REFUSED: raw pipe in fact %s truncates the table row" % num)
    if body.count("*") % 2 != 0:
        raise SystemExit("REFUSED: odd asterisk count in fact %s leaves italics open" % num)
    return "| %s | %s | %s | %s |" % (num, status, source, body)


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR_PREFIX)]
    if len(hits) != 1:
        raise SystemExit("REFUSED: anchor %r matched %d rows, expected 1"
                         % (ANCHOR_PREFIX, len(hits)))
    at = hits[0]
    for num, _s, _src, _b in ROWS:
        if any(ln.startswith("| %s |" % num) for ln in lines):
            raise SystemExit("REFUSED: fact %s already present" % num)

    new_rows = [build_row(*r) for r in ROWS]
    lines[at + 1: at + 1] = new_rows
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(newline.join(lines))
    print("inserted %d row(s) after fact 1872 (line %d)" % (len(new_rows), at + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Final cross-reference and line-count corrections to the M59 report.

A separate script rather than a PowerShell one-liner because PowerShell's
double-quoted here-strings treat the backtick as an escape character, and this
report is full of backticked identifiers. Two earlier one-liners silently
mangled them.
"""
import io
import sys

PATH = "docs/research/M59-corpus-linter.md"

PAIRS = [
    ("`scripts/corpus_lint.py` \u2014 820 lines, standard library only",
     "`scripts/corpus_lint.py` \u2014 870 lines, standard library only"),
    ("reported 13 violations. That was wrong, and \u00a73.3 gives the measurement that",
     "reported 13 violations. That was wrong, and \u00a73.3.1 gives the measurement that"),
    ("`docs/captures-needed.md`, and `crates/**/*.rs` excluding `target/`.\n"
     "78 markdown files and 27 Rust files at the pinned sha "
     "(this report is one of them; see 5.2).",
     "`docs/captures-needed.md`, `docs/research/OWNER-QUESTIONS.md`, and\n"
     "`crates/**/*.rs` excluding `target/`. 78 markdown files and 27 Rust files at\n"
     "the pinned sha \u2014 this report is one of them, and \u00a75.2 records what happened\n"
     "when the linter read it."),
    ("**Pinned:** `7a9b76bd4523d3bdeead32cc0a2c3fef8f39fae9`, working tree clean for\n"
     "`docs/research/SYNTHESIS.md`.",
     "**Pinned:** `7a9b76bd4523d3bdeead32cc0a2c3fef8f39fae9`, working tree clean for\n"
     "`docs/research/SYNTHESIS.md`. **The corpus is under concurrent edit** \u2014 \u00a74 grew\n"
     "from 573 to 639 rows while this milestone ran, across four orchestrator\n"
     "commits. Every total below moves; **the defect set does not.** The same four\n"
     "S1 files, the same three S2 line numbers and the same zero for C1/N1/N2/N4/A1\n"
     "came back on every run in this session."),
]


def main():
    text = io.open(PATH, encoding="utf-8", newline="").read()
    bad = []
    for old, new in PAIRS:
        n = text.count(old)
        if n != 1:
            bad.append((n, old.splitlines()[0][:72]))
            continue
        text = text.replace(old, new)
    if bad:
        for n, s in bad:
            sys.stderr.write("count=%d for %r\n" % (n, s))
        return 1
    text = text.replace("\r\n", "\n").rstrip("\n") + "\n"
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    print("wrote %s (%d bytes)" % (PATH, len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

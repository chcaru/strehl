"""Measure the base rate of raw-asterisk parity on the corpus.

S5 counts `**` pairs and single `*` with a `(?<![\\*])` lookbehind, so a run of
three asterisks reads as one balanced `**` plus an orphan the lookbehind skips,
and a run of four reads as two balanced `**`. Both are invisible to it. This
was demonstrated by negctl_1851.py: planting `***` on a fact row left S5 silent
while the raw-pipe arm of the same control fired correctly.

`***bold-italic***` is legal Markdown, so a run of three is not itself a defect.
The invariant that does hold is PARITY of the total unescaped asterisk count:
`***x***` is 6, `***x**` is 5. If the corpus base rate of odd units is zero,
parity is a shippable strengthening. If it is not zero, it is a check that would
get switched off, exactly as S5's docstring records for `_` at 17 false
positives -- and that is a finding too, not a failure.
"""
import importlib.util
import os
import sys

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
LINT = os.path.join(ROOT, "scripts", "corpus_lint.py")

spec = importlib.util.spec_from_file_location("corpus_lint", LINT)
cl = importlib.util.module_from_spec(spec)
sys.modules["corpus_lint"] = cl
os.chdir(ROOT)
spec.loader.exec_module(cl)


def main():
    # Rebuild the index exactly as corpus_lint.main does (scripts/corpus_lint.py
    # :1584-1591), so the units measured here are the same units S5 checks.
    md_paths, _rs = cl.collect_files(".")
    md_docs = [cl.Doc(".", p) for p in md_paths]
    syn = next(d for d in md_docs if d.rel == cl.SYNTHESIS)
    agents = next((d for d in md_docs if d.rel == cl.AGENTS), None) or cl.Doc(".", cl.SYNTHESIS)
    index = cl.Index(syn, agents)

    units = [("discipline %d" % num, line, text)
             for sec, num, line, label, text in cl.numbered_item_units(index, (5, 10))]
    units += [("fact %d" % num, line, index.syn.lines[line - 1])
              for num, line in index.fact_rows_all]

    odd = []
    for who, line, text in units:
        stripped = cl.strip_code_spans(text)
        # Escaped asterisks are literal and must not count, exactly as S5's
        # single-`*` arm already excludes them.
        n = stripped.replace("\\*", "").count("*")
        if n % 2:
            odd.append((who, line, n, stripped.strip().split("\n")[0][:110]))

    print("units examined      : %d" % len(units))
    print("odd raw-asterisk    : %d" % len(odd))
    print()
    for who, line, n, snip in odd[:25]:
        print("  L%-6d %-16s count=%-4d %s" % (line, who, n, snip))
    if len(odd) > 25:
        print("  ... and %d more" % (len(odd) - 25))
    print()
    if not odd:
        print("VERDICT: base rate 0 -- raw-asterisk parity is SHIPPABLE and would "
              "have caught the planted `***` that S5 missed.")
        return 0
    print("VERDICT: base rate %d -- parity would fire on existing clean text, so "
          "it is NOT shippable as-is. Report the false-positive shapes." % len(odd))
    return 0


if __name__ == "__main__":
    sys.exit(main())

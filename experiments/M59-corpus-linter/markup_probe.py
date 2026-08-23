"""M59 pass 5: measure paired-inline-markup parity before extending S5.

The orchestrator asked for `~~` balance, and asked me to consider whether the
same generalisation applies to `_`, `*` and `` ` `` -- with the explicit
instruction to measure before deciding. This measures all four, per ITEM, with
code spans stripped, exactly as S5 does for `**`.

Backticks are the interesting case: they cannot be measured after stripping code
spans, because the stripper is what is under test. An odd backtick makes the
stripper unreliable in every other check, so this measures the residue LEFT
BEHIND by the stripper instead.

Read-only. Run: python experiments/M59-corpus-linter/markup_probe.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import corpus_lint as cl                                    # noqa: E402


def units(index):
    """Every unit S5 already checks: §5/§10 items, their continuation
    paragraphs, and §4 fact rows."""
    for sec, num, line, label, text in cl.numbered_item_units(index, (5, 10)):
        yield ("§%d %s %d" % (sec, label, num), line, text)
    for num, line in index.fact_rows_all:
        yield ("fact row %d" % num, line, index.syn.lines[line - 1])


def main():
    syn = cl.Doc(ROOT, cl.SYNTHESIS)
    agents = cl.Doc(ROOT, cl.AGENTS)
    index = cl.Index(syn, agents)
    all_units = list(units(index))
    print("units examined: %d  (§5/§10 items + continuation paragraphs + fact rows)"
          % len(all_units))
    print("")

    # ---- token parity, code spans stripped first --------------------------
    print("A  paired-token parity, per item, code spans stripped first")
    print("   %-6s %-8s %s" % ("token", "odd", "first few"))
    for token in ("**", "~~", "__"):
        bad = []
        for name, line, text in all_units:
            if cl.strip_code_spans(text).count(token) % 2:
                bad.append("%s L%d" % (name, line))
        print("   %-6s %-8d %s" % ("`%s`" % token, len(bad), ", ".join(bad[:4])))

    # single-char emphasis: count occurrences NOT part of a doubled run
    for token in ("*", "_"):
        pat = re.compile(r"(?<!%s)\%s(?!%s)" % (re.escape(token),
                                                token, re.escape(token)))
        bad = []
        for name, line, text in all_units:
            if len(pat.findall(cl.strip_code_spans(text))) % 2:
                bad.append("%s L%d" % (name, line))
        print("   %-6s %-8d %s" % ("`%s`" % token, len(bad), ", ".join(bad[:4])))

    # ---- backticks: the residue the stripper leaves behind ----------------
    print("")
    print("B  backticks -- measured as residue, because the stripper is the instrument")
    residue = []
    raw_odd = []
    for name, line, text in all_units:
        left = cl.strip_code_spans(text).count("`")
        if left:
            residue.append((name, line, left, text.strip().split("\n")[0][:90]))
        if text.count("`") % 2:
            raw_odd.append((name, line))
    print("   units with backticks left after stripping : %d" % len(residue))
    print("   units with an odd RAW backtick count      : %d" % len(raw_odd))
    for name, line, left, snip in residue[:12]:
        print("     %-28s L%-6d residue=%-3d %s" % (name, line, left, snip))

    # ---- whole-file backtick residue, outside fences ----------------------
    file_res = 0
    for i, line in enumerate(syn.lines):
        if syn.fenced[i]:
            continue
        file_res += cl.strip_code_spans(line).count("`")
    print("   whole SYNTHESIS, non-fenced lines, residue: %d" % file_res)

    # ---- `~~` usage volume, to show it is not a rare construct -----------
    n_units = sum(1 for _, _, t in all_units if "~~" in t)
    n_spans = sum(len(re.findall(r"~~.*?~~", t, re.S)) for _, _, t in all_units)
    print("")
    print("C  how heavily `~~` is used")
    print("   units containing `~~`      : %d" % n_units)
    print("   closed `~~...~~` spans     : %d" % n_spans)


if __name__ == "__main__":
    main()

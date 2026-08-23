"""How many sites does A2 actually examine? A check's honesty is its denominator.

A2 only looks at a §4 fact row when the row BOTH states `N of M <corpus-noun>`
AND enumerates corpus numbers. This counts how many rows reach each stage, so
the report can state A2's coverage rather than implying it is general.

Read-only. Run: python experiments/M59-corpus-linter/a2_coverage.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def main():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import corpus_lint as CL

    md_paths, rs_paths = CL.collect_files(ROOT)
    md = [CL.Doc(ROOT, p) for p in md_paths]
    syn = next(d for d in md if d.rel == CL.SYNTHESIS)
    agents = next(d for d in md if d.rel == CL.AGENTS)
    index = CL.Index(syn, agents)

    rows = len(index.fact_rows_all)
    has_enum = has_nofm = both = 0
    both_rows = []
    for num, line_no in index.fact_rows_all:
        row = index.syn.lines[line_no - 1]
        lengths = set()
        for m in CL.ENUMERATION.finditer(row):
            items = re.findall(r"\d+", m.group(0))
            if all(index.resolves("fact", int(x)) or index.resolves("question", int(x))
                   for x in items):
                lengths.add(len(items))
        n = list(CL.N_OF_M.finditer(row))
        if lengths:
            has_enum += 1
        if n:
            has_nofm += 1
        if lengths and n:
            both += 1
            both_rows.append((num, line_no, [m.group(0) for m in n], sorted(lengths)))

    print("§4 fact rows                                     : %d" % rows)
    print("rows with >=1 corpus enumeration                 : %d (%.1f%%)"
          % (has_enum, 100.0 * has_enum / rows))
    print("rows with an `N of M <corpus-noun>` claim        : %d (%.1f%%)"
          % (has_nofm, 100.0 * has_nofm / rows))
    print("rows A2 can say ANYTHING about (needs both)      : %d (%.1f%%)"
          % (both, 100.0 * both / rows))
    print("")
    print("the rows A2 examined at HEAD, and its verdict on each:")
    for num, line_no, claims, lengths in both_rows:
        agree = any((int(c.split()[0]) if c.split()[0].isdigit()
                     else CL.NUM_WORD.get(c.split()[0].lower(), -1)) in lengths
                    for c in claims)
        print("   fact %-4d L%-6d %-34s enum lengths %-10s -> %s"
              % (num, line_no, " ; ".join(claims)[:34], lengths,
                 "agrees" if agree else "DISAGREES"))


if __name__ == "__main__":
    main()

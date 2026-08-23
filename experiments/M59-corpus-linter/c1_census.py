"""Count what C1 actually examined, so the report can state a denominator.

Reports, per class, how many citation tokens the linter resolved at HEAD.
Read-only. Run: python experiments/M59-corpus-linter/c1_census.py
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def main():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import corpus_lint as CL

    md_paths, rs_paths = CL.collect_files(ROOT)
    md = [CL.Doc(ROOT, p) for p in md_paths]
    rs = [CL.Doc(ROOT, p) for p in rs_paths]

    by_class = Counter()
    by_kind = Counter()
    by_area = Counter()
    for doc in md + rs:
        area = ("SYNTHESIS" if doc.rel == CL.SYNTHESIS
                else "rust" if doc.rel.endswith(".rs")
                else "reports/other md")
        for kind, num, off, raw, klass in CL.iter_citations(doc):
            by_class[klass] += 1
            by_kind[kind] += 1
            by_area[area] += 1

    print("files scanned: %d markdown, %d rust" % (len(md), len(rs)))
    print("")
    print("citation tokens by class:")
    for k, v in sorted(by_class.items(), key=lambda kv: -kv[1]):
        print("   %-12s %d" % (k, v))
    print("total tokens: %d" % sum(by_class.values()))
    print("")
    print("by kind:")
    for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print("   %-12s %d" % (k, v))
    print("")
    print("by area:")
    for k, v in sorted(by_area.items(), key=lambda kv: -kv[1]):
        print("   %-18s %d" % (k, v))
    print("")
    checked = by_class["ref"]
    print("class 'ref' is what C1 requires to resolve: %d" % checked)
    print("classes 'sub'/'qualified'/'block' are the documented exclusions: %d"
          % (sum(by_class.values()) - checked))


if __name__ == "__main__":
    main()

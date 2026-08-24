"""Correct fact 1298's ratio prose in place.

1298 said the merge's halo is "three orders of magnitude above anything any
input frame contains". That is the ratio to the MEAN single frame (2597x).
Against the WORST single frame -- which is what "anything any input frame
contains" means -- it is 79.02x. The claim survives; the phrasing conflated
two different comparisons. Corrected against fact 1310's operands.
"""
import io

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

OLD = ("The merged image's halo is **three orders of magnitude** above anything any input frame contains, and the "
       "interval does not approach the single-frame level.")

NEW = ("**CORRECTED against fact 1310's operands:** the merge is **79.02x the worst single frame** "
       "(max `8.6107e-04`) and 2597x the mean, at **9299 SE**. This row originally read \"three orders of magnitude "
       "above anything any input frame contains\", which is the ratio to the *mean* wearing the language of the "
       "*maximum*; **79x against the worst frame is the conservative and correct statement**, and 94.31% of frames "
       "score exactly zero.")


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    assert text.count(OLD) == 1, f"expected 1 occurrence of the old prose, found {text.count(OLD)}"
    assert NEW not in text, "already corrected"

    text = text.replace(OLD, NEW, 1)

    rows = [l for l in text.split("\n") if l.startswith("| 1298 |")]
    assert len(rows) == 1, f"expected exactly one 1298 row, got {len(rows)}"
    n = rows[0].count("|") - rows[0].count("\\|")
    assert n == 5, f"corrected 1298: {n} unescaped pipes, need 5"
    assert "79.02x the worst single frame" in rows[0], "correction did not land in row 1298"

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("corrected fact 1298's ratio prose")


if __name__ == "__main__":
    main()

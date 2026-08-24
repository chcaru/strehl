"""Repair fact 1461: name fact 1459, whose figures it deliberately reuses."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

OLD = (
    "**THE RESCALE IS A SUFFICIENT BUT REDUNDANT CAUSE OF THE SHARPNESS LOSS, WHICH IS WHY REMOVING IT "
    "RECOVERS NOTHING.** In isolation"
)
NEW = (
    "**THE RESCALE IS A SUFFICIENT BUT REDUNDANT CAUSE OF THE SHARPNESS LOSS, WHICH IS WHY REMOVING IT "
    "RECOVERS NOTHING.** This row deliberately reuses fact 1459's figures because it is the explanation "
    "of them, not a second measurement of them. In isolation"
)


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    n = text.count(OLD)
    assert n == 1, f"anchor matched {n} times, expected 1"
    text = text.replace(OLD, NEW)

    row = [l for l in text.split("\n") if l.startswith("| 1461 |")]
    assert len(row) == 1
    k = row[0].count("|") - row[0].count("\\|")
    assert k == 5, f"fact 1461: {k} unescaped pipes"
    assert "fact 1459" in row[0], "must name the earlier fact -- that is the disclosure"

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("repaired fact 1461: fact 1459 named as the source of the reused figures")


if __name__ == "__main__":
    main()

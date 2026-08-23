"""One-off: shift M61 report fact numbers 6..28 up by one after inserting a
new fact 5, and fix every cross-reference. Run once, from the submodule root.
"""

import re
import sys

PATH = "docs/research/M61-ptc-high-iso-measured.md"
OLD_MAX = 28


def main() -> int:
    with open(PATH, encoding="utf-8") as fh:
        t = fh.read()

    # Headers: **Fact N (LABEL).**  -- only 6..28, walk downward.
    for n in range(OLD_MAX, 5, -1):
        t = t.replace(f"**Fact {n} (", f"**Fact \x00{n + 1}\x00 (")
    # Cross-references: "fact N" / "facts N" lowercase, and "(fact N)".
    def ref(m):
        n = int(m.group(2))
        if 6 <= n <= OLD_MAX:
            return f"{m.group(1)}\x00{n + 1}\x00"
        return m.group(0)

    t = re.sub(r"\b(facts? )(\d+)\b", ref, t)
    t = t.replace("\x00", "")

    with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)

    heads = re.findall(r"\*\*Fact (\d+) \(", t)
    print("fact headers in order:", ", ".join(heads))
    print("duplicates:", [h for h in set(heads) if heads.count(h) > 1])
    print("refs:", sorted(set(re.findall(r"\bfacts? (\d+)\b", t)), key=int))
    return 0


if __name__ == "__main__":
    sys.exit(main())

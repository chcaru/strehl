"""Print the true occurrence count of every figure verify_s33 counts, inside
its scope, so the expected counts are set from evidence rather than guessed.
Also lists the surrounding context of each hit so a duplicated typo cannot be
mistaken for a legitimate second mention."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
MINUS = "\u2212"

NEEDLES = ["55.3\u00d7", "0.8833", "0.13480", "0.11906", "11.7%", "88.3%",
           "4296", "55.321", "38.77%", "197 797 874",
           "E400A63AA9F6AB1F1957940D7BD9D496",
           "3.664e" + MINUS + "15", "2.1400%", "0.000000%",
           "0.079502", "0.093960", "0.590", "2.451e" + MINUS + "07",
           "6.69e+07", "16 777 216", "1.795e+09", "63 001",
           "30.7%", "23.4%", "0.1569", "0.0186", "56 rings", "0.1167",
           "0.8717", "0.9843", "0.9076", "27 settings",
           "473.2", "148.4", "221.1", "0.671", "0.9958", "4189", "96%"]


def main():
    raw = DOC.read_bytes().decode("utf-8")
    sec = re.sub(r"\s+", " ", raw[raw.index("## 33."):])
    rows = "\n".join(l for l in raw.splitlines()
                     if re.match(r"^\| P1(2[789]|3[012]) \|", l))
    scope = sec + " " + re.sub(r"\s+", " ", rows)
    show = "--show" in sys.argv
    print(f"scope: {len(scope)} chars (section 33 + 6 fact rows)")
    for n in NEEDLES:
        c = scope.count(n)
        print(f'  ("{n}", {c}),')
        if show:
            for mt in re.finditer(re.escape(n), scope):
                a, b = max(0, mt.start() - 55), min(len(scope), mt.end() + 55)
                print(f"        ...{scope[a:b]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

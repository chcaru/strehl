"""MEASURED: how many of SYNTHESIS §4's fact rows actually render as table rows?

Two independent renderers. Control: remove ONLY the blank lines that sit
between two pipe-rows, and re-render.
"""
import io
import re


def load():
    lines = io.open("docs/research/SYNTHESIS.md", encoding="utf-8", newline="").read().split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("## 4. "))
    end = next(i for i, l in enumerate(lines) if i > start and l.startswith("## 5. "))
    return lines, start, end


def render(src):
    from markdown_it import MarkdownIt
    import markdown as pymd
    a = MarkdownIt("gfm-like").disable("linkify").render(src)
    b = pymd.markdown(src, extensions=["tables"])
    return a, b


def report(tag, src):
    a, b = render(src)
    for name, h in (("markdown-it-py", a), ("python-markdown", b)):
        tables = h.count("<table>")
        trs = h.count("<tr>")
        tds = h.count("<td>")
        print("  %-14s %-16s tables=%d  tr=%d  td=%d  data_rows=%d" %
              (tag, name, tables, trs, tds, trs - tables))


def main():
    lines, start, end = load()
    sec = lines[start:end]
    src = "\n".join(sec)
    rows = [i for i, l in enumerate(sec) if re.match(r"^\|\s*\d+\s*\|", l)]
    print("§4 numbered pipe-rows in SOURCE: %d" % len(rows))

    # blank lines sandwiched between two pipe-rows
    bad = []
    for i in range(1, len(sec) - 1):
        if sec[i].strip() == "" and sec[i - 1].startswith("|") and sec[i + 1].startswith("|"):
            bad.append(start + i + 1)  # 1-based file line number
    print("blank lines between two pipe-rows (1-based file lines): %s" % bad)

    print("\nAT HEAD:")
    report("head", src)

    fixed = [l for i, l in enumerate(sec)
             if not (l.strip() == "" and 0 < i < len(sec) - 1
                     and sec[i - 1].startswith("|") and sec[i + 1].startswith("|"))]
    print("\nCONTROL (only those %d blank lines deleted):" % len(bad))
    report("control", "\n".join(fixed))

    # And: does the header's column count clip wide rows? plant one.
    planted = list(sec)
    for i, l in enumerate(planted):
        if l.startswith("| 1 |"):
            planted[i] = l + " EXTRA | CELL |"
            break
    print("\nPLANT (one row given 2 extra cells):")
    report("plant", "\n".join(planted))


if __name__ == "__main__":
    main()

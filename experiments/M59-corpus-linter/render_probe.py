"""MEASURED: what does a GFM renderer actually do with SYNTHESIS §4?

Uses markdown-it-py (gfm-like preset, tables enabled) and python-markdown's
`tables` extension as a second, independent renderer. Read-only.
"""
import io
import re


def slice_section4(path):
    lines = io.open(path, encoding="utf-8", newline="").read().split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("## 4. "))
    end = next(i for i, l in enumerate(lines) if i > start and l.startswith("## 5. "))
    return lines[start:end]


def main():
    sec = slice_section4("docs/research/SYNTHESIS.md")
    src = "\n".join(sec)
    n_rows = sum(1 for l in sec if re.match(r"^\|\s*\d+\s*\|", l))
    print("§4 source: %d lines, %d numbered pipe-rows" % (len(sec), n_rows))

    from markdown_it import MarkdownIt
    md = MarkdownIt("gfm-like").disable("linkify")
    html = md.render(src)
    print("[markdown-it-py gfm-like] <table> = %d   <tr> = %d   <td> = %d" %
          (html.count("<table>"), html.count("<tr>"), html.count("<td>")))

    import markdown as pymd
    html2 = pymd.markdown(src, extensions=["tables"])
    print("[python-markdown tables ] <table> = %d   <tr> = %d   <td> = %d" %
          (html2.count("<table>"), html2.count("<tr>"), html2.count("<td>")))

    # Where does the first table end, and what happens to fact 320?
    for name, h in (("markdown-it", html), ("python-markdown", html2)):
        idx = h.find("320")
        ctx = h[max(0, idx - 200):idx + 200].replace("\n", " ")
        print("\n--- %s: context around the string '320' ---\n%s" % (name, ctx))

    # Control: does the same renderer produce one table if the blanks are removed?
    fixed = re.sub(r"\n\n(?=\|)", "\n", src)
    h3 = md.render(fixed)
    print("\n[control, blank lines between rows removed] <table> = %d  <tr> = %d" %
          (h3.count("<table>"), h3.count("<tr>")))


if __name__ == "__main__":
    main()

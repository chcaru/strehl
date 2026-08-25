"""M87 -- re-wrap section 34's prose to the document's hard-wrap convention.

append_s34.py emitted each paragraph as one long line (max 554 chars) where the
rest of the report wraps at ~78.  This rewraps section 34 only, leaving tables,
code fences, headings and fact rows byte-identical.

Safe by construction for the checkers: verify_s34 normalises whitespace before
matching, so wrapping cannot change any check's outcome, and this script asserts
that the whitespace-collapsed text of section 34 is unchanged by the rewrap.
"""
import pathlib
import re
import textwrap

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"
WIDTH = 78


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def cmp_norm(s):
    """Compare text ignoring line breaks AND blockquote markers.

    Re-wrapping a blockquote legitimately introduces one `> ` prefix per new
    line, so a raw collapsed comparison reports a difference of exactly two
    characters per added line when nothing has actually changed.  Both sides
    are normalised identically here so the invariant still catches real edits.
    """
    return collapse(re.sub(r"(?m)^[ \t]*>[ \t]?", "", s))


def rewrap(lines):
    out = []
    buf = []
    kind = None
    in_code = False

    def flush():
        nonlocal buf, kind
        if not buf:
            return
        text = " ".join(x.strip() for x in buf)
        if kind == "quote":
            text = re.sub(r"^>\s*", "", " ".join(
                re.sub(r"^>\s?", "", x).strip() for x in buf))
            out.extend(textwrap.wrap(text, WIDTH - 2, break_long_words=False,
                                     break_on_hyphens=False,
                                     initial_indent="> ",
                                     subsequent_indent="> ") or ["> "])
        elif kind == "item":
            m = re.match(r"^(\s*(?:\d+\.|[-*])\s+)", buf[0])
            marker = m.group(1)
            body = " ".join(x.strip() for x in buf)[len(marker.strip()) + 1:]
            body = body.strip()
            out.extend(textwrap.wrap(
                body, WIDTH, break_long_words=False, break_on_hyphens=False,
                initial_indent=marker,
                subsequent_indent=" " * len(marker)))
        else:
            out.extend(textwrap.wrap(text, WIDTH, break_long_words=False,
                                     break_on_hyphens=False))
        buf = []
        kind = None

    for ln in lines:
        if ln.strip().startswith("```"):
            flush()
            in_code = not in_code
            out.append(ln)
            continue
        if in_code or ln.startswith("|") or ln.startswith("#") or not ln.strip():
            flush()
            out.append(ln)
            continue
        k = ("quote" if ln.lstrip().startswith(">") else
             "item" if re.match(r"^\s*(?:\d+\.|[-*])\s+", ln) else "prose")
        if kind is not None and k != kind:
            flush()
        if k == "item" and kind == "item":
            flush()
        kind = k
        buf.append(ln)
    flush()
    return out


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    i = raw.index("## 34.")
    head, tail = raw[:i], raw[i:]
    lines = tail.split("\r\n")
    new = rewrap(lines)
    before, after = cmp_norm(tail), cmp_norm("\r\n".join(new))
    assert before == after, "rewrap changed the text, not just the line breaks"
    text = head + "\r\n".join(new)
    assert text.count("\n") == text.count("\r\n"), "CRLF broken by rewrap"
    DOC.write_bytes(text.encode("utf-8"))
    longest = max((len(x) for x in new if not x.startswith("|")), default=0)
    print(f"rewrapped section 34: {len(lines)} -> {len(new)} lines, "
          f"longest non-table line {longest}")
    print("whitespace-collapsed text identical: OK")


if __name__ == "__main__":
    raise SystemExit(main())

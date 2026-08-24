#!/usr/bin/env python3
"""corpus_lint.py — structural, namespace and citation checks for the strehl
research corpus.

Run from the submodule root:

    python scripts/corpus_lint.py

Exits non-zero if any check reports a violation. Every violation is printed as
``path:line: [ID] message`` followed by the offending text.

Why this exists
---------------
SYNTHESIS fact 766: "There is no automated check in the repository that verifies
a fold against its source, that a row is internally consistent after amendment,
or that a cited fact number supports the sentence citing it." Open question 178
asks for the cheapest check that would have caught facts 694, 725, 759 and 763.
This is that check. It is deliberately narrower than the question, and
``docs/research/M59-corpus-linter.md`` records exactly what it cannot see.

What it explicitly does NOT do
------------------------------
* It does not rank sources. A citation that resolves, is true, and is the
  *weaker* available source passes (fact 729).
* It does not read semantics. A sentence in which every number is correct and
  the sentence is still false passes (fact 772), as does a number that is right
  in one configuration and quoted into another (fact 768).
* It does not verify a fold against its source report (facts 758, 762, 765).

A linter that claimed any of those would create false confidence in the one
document that records what the project believes.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import unicodedata

# --------------------------------------------------------------------------
# namespaces are defined BY SECTION, never by number. Facts, disciplines and
# questions share one integer space and are not contiguously numbered, so
# "N is a discipline, therefore N is not a question" is false and is not done
# here. See SYNTHESIS §4's numbering note and AGENTS rules 25 and 37.
# --------------------------------------------------------------------------
SYNTHESIS = "docs/research/SYNTHESIS.md"
AGENTS = "AGENTS.md"

NAMESPACE_SECTION = {"fact": 4, "risk": 7, "discipline": 5, "question": 10}

AMENDMENT_MARKERS = (
    "AMENDED", "REFUTED", "PARTLY REFUTED", "SCOPED", "RESCOPED", "MOOT",
    "WITHDRAWN", "SUPERSEDED", "NOT ADMISSIBLE", "RETRACTED",
)

# Sections of SYNTHESIS.md that declare no numbering namespace and, measured at
# 4c02816, contain zero numbered list items. See check_n5_item_placement.
SECTIONS_WITHOUT_NUMBERED_ITEMS = (2, 4, 6, 9)

# Status words a sentence may assert about a question or discipline. Used by
# advisory A4 only -- see the docstring there for why this is not a check.
STATUS_MARKERS = (
    "MOOT", "ANSWERED", "CLOSED", "RESOLVED", "REOPENED", "WITHDRAWN",
    "SUPERSEDED", "REFUTED",
)

CODE_SPAN = re.compile(r"`+[^`]*`+")
STRIKETHROUGH = re.compile(r"~~.*?~~", re.S)

# nouns whose counts A2 is willing to compare against an enumeration. Anything
# else ("cells", "frames", "stacks") produced false positives at design time.
CORPUS_NOUNS = r"(?:fact|facts|row|rows|fact rows|question|questions|discipline|disciplines|site|sites)"


class Violation(object):
    __slots__ = ("path", "line", "check", "message", "text")

    def __init__(self, path, line, check, message, text=""):
        self.path = path
        self.line = line
        self.check = check
        self.message = message
        self.text = text

    def render(self):
        head = "%s:%d: [%s] %s" % (self.path, self.line, self.check, self.message)
        if self.text:
            snippet = self.text.strip()
            if len(snippet) > 240:
                snippet = snippet[:237] + "..."
            return head + "\n      " + snippet
        return head


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

class Doc(object):
    """A text file, its lines, and a mask of which lines sit inside a fence."""

    def __init__(self, root, relpath):
        self.rel = relpath.replace("\\", "/")
        self.abs = os.path.join(root, relpath)
        with io.open(self.abs, encoding="utf-8", newline="") as fh:
            self.raw = fh.read()
        self.crlf = self.raw.count("\r\n")
        self.bare_lf = self.raw.count("\n") - self.crlf
        self.bare_cr = self.raw.count("\r") - self.crlf
        self.text = self.raw.replace("\r\n", "\n").replace("\r", "\n")
        self.lines = self.text.split("\n")
        self.fenced = self._fence_mask()

    def _fence_mask(self):
        mask = [False] * len(self.lines)
        fence = None
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            m = re.match(r"^(`{3,}|~{3,})", stripped)
            if fence is None:
                if m:
                    fence = m.group(1)[0]
                    mask[i] = True
                    continue
            else:
                mask[i] = True
                if m and m.group(1)[0] == fence:
                    fence = None
                continue
            mask[i] = False
        return mask

    def line_of(self, offset):
        return self.text.count("\n", 0, offset) + 1


def unescaped_pipe_count(line):
    """Count `|` delimiters, treating `\\|` as an escaped literal (rule 37)."""
    count = 0
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            i += 2
            continue
        if ch == "|":
            count += 1
        i += 1
    return count


def split_cells(line):
    """Split a table row on unescaped pipes; drop the outer empties."""
    cells = []
    buf = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append("".join(buf))
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return cells


def is_delimiter_row(line):
    return bool(re.match(r"^\s*\|[\s:|\-]+\|\s*$", line)) and "-" in line


def table_blocks(doc):
    """Yield (start_idx, end_idx) of runs of consecutive pipe-lines outside fences."""
    i = 0
    n = len(doc.lines)
    while i < n:
        if not doc.fenced[i] and doc.lines[i].lstrip().startswith("|"):
            j = i
            while j < n and not doc.fenced[j] and doc.lines[j].lstrip().startswith("|"):
                j += 1
            yield i, j
            i = j
        else:
            i += 1


# --------------------------------------------------------------------------
# SYNTHESIS index
# --------------------------------------------------------------------------

class Index(object):
    def __init__(self, syn, agents):
        self.syn = syn
        self.spans = self._sections(syn.lines)
        self.items = {}
        self.items["fact"] = self._fact_rows()
        for kind in ("discipline", "question", "risk"):
            self.items[kind] = self._list_items(NAMESPACE_SECTION[kind])
        self.items["rule"] = {
            int(m.group(1)): i + 1
            for i, l in enumerate(agents.lines)
            for m in [re.match(r"^(\d+)\. \*\*", l)] if m
        }
        # every declaration site, for duplicate detection (dict collapses dupes)
        self.fact_rows_all = self._fact_rows(collapse=False)
        self.list_items_all = {
            k: self._list_items(NAMESPACE_SECTION[k], collapse=False)
            for k in ("discipline", "question", "risk")
        }

    @staticmethod
    def _sections(lines):
        marks = [(int(m.group(1)), i) for i, l in enumerate(lines)
                 for m in [re.match(r"^## (\d+)\. ", l)] if m]
        out = {}
        for k, (num, start) in enumerate(marks):
            end = marks[k + 1][1] if k + 1 < len(marks) else len(lines)
            out[num] = (start, end)
        return out

    def _fact_rows(self, collapse=True):
        start, end = self.spans[4]
        pairs = []
        for i in range(start, end):
            if self.syn.fenced[i]:
                continue
            m = re.match(r"^\|\s*(\d+)\s*\|", self.syn.lines[i])
            if m:
                pairs.append((int(m.group(1)), i + 1))
        return dict(pairs) if collapse else pairs

    def _list_items(self, section, collapse=True):
        if section not in self.spans:
            return {} if collapse else []
        start, end = self.spans[section]
        pairs = []
        for i in range(start, end):
            if self.syn.fenced[i]:
                continue
            m = re.match(r"^(\d+)\. ", self.syn.lines[i])
            if m:
                pairs.append((int(m.group(1)), i + 1))
        return dict(pairs) if collapse else pairs

    def item_body(self, section, number):
        """Full text of a numbered list item, through to the next item."""
        start, end = self.spans[section]
        i = start
        while i < end:
            m = re.match(r"^(\d+)\. ", self.syn.lines[i])
            if m and int(m.group(1)) == number:
                j = i + 1
                buf = [self.syn.lines[i]]
                while j < end and not re.match(r"^\d+\. ", self.syn.lines[j]) \
                        and not self.syn.lines[j].startswith("#"):
                    buf.append(self.syn.lines[j])
                    j += 1
                return "\n".join(buf)
            i += 1
        return ""

    def resolves(self, kind, number):
        return number in self.items.get(kind, {})

    def other_namespaces(self, number, exclude):
        return [k for k in ("fact", "discipline", "question", "risk", "rule")
                if k != exclude and number in self.items.get(k, {})]


# --------------------------------------------------------------------------
# S — structural
# --------------------------------------------------------------------------

def check_s1_cell_count(docs):
    """Every table row carries its header's cell count. Fact 694's mechanism:
    an unescaped `|` inside `|H|` opens a new cell, and **markdown discards every
    cell beyond the header's column count**, so the row loses a column silently.

    GFM pads a short row with empty cells and truncates a long one, so only an
    over-count destroys data. A short row is reported only when it is also short
    against its own table's modal width — a table that is uniformly narrower
    than its header (AGENTS.md's corpus index) is sloppy, not lossy, and making
    it a violation would fire on ~70 rows and get the linter switched off.
    """
    out = []
    for doc in docs:
        for start, end in table_blocks(doc):
            if end - start < 2 or not is_delimiter_row(doc.lines[start + 1]):
                continue
            want = unescaped_pipe_count(doc.lines[start])
            delim = unescaped_pipe_count(doc.lines[start + 1])
            if want != delim:
                out.append(Violation(
                    doc.rel, start + 1, "S1",
                    "table HEADER has %d unescaped pipes but its delimiter row "
                    "(line %d) declares %d: the delimiter is GFM's ground truth, so "
                    "the header is the corrupted row. A corrupted header is adopted "
                    "as this check's own standard and silences the whole table — "
                    "escape absolute-value bars as \\|."
                    % (want, start + 2, delim), doc.lines[start]))
                want = delim
            body = [unescaped_pipe_count(doc.lines[i]) for i in range(start + 2, end)]
            modal = max(set(body), key=body.count) if body else want
            for i in range(start, end):
                got = unescaped_pipe_count(doc.lines[i])
                if got > want:
                    out.append(Violation(
                        doc.rel, i + 1, "S1",
                        "table row has %d unescaped pipes, header (line %d) has %d: "
                        "%d cell(s) past the header's column count are DISCARDED by "
                        "the renderer. Escape absolute-value bars as \\|."
                        % (got, start + 1, want, got - want),
                        doc.lines[i]))
                elif got < want and got < modal:
                    out.append(Violation(
                        doc.rel, i + 1, "S1",
                        "table row has %d unescaped pipes; its table's rows are "
                        "modally %d and the header (line %d) has %d, so this row is "
                        "missing a cell its siblings carry"
                        % (got, modal, start + 1, want),
                        doc.lines[i]))
    return out


def check_s6_pipe_in_code_span(docs):
    """No table row may carry an unescaped `|` inside a code span.

    Discipline 524: S1 compares a row's pipe count to its header's, so it is
    blind to a row that is malformed **and** coincidentally lands on the header
    width — one span leaking a cell while another cell is missing nets to zero.
    This check tests fact 694's *mechanism* instead of its arithmetic, so the
    coincidence cannot hide it.

    In GFM a table row is split on `|` **before** inline code is parsed, so a
    backtick span never protects a bar: `\\|H\\|` is the only correct spelling
    inside a table. Any unescaped bar between backticks on a table row is
    therefore a defect regardless of how the counts come out.
    """
    span = re.compile(r"`+[^`]*`+")
    out = []
    for doc in docs:
        for start, end in table_blocks(doc):
            if end - start < 2 or not is_delimiter_row(doc.lines[start + 1]):
                continue
            for i in range(start, end):
                line = doc.lines[i]
                if is_delimiter_row(line):
                    continue
                for m in span.finditer(line):
                    if re.search(r"(?<!\\)\|", m.group(0)):
                        out.append(Violation(
                            doc.rel, i + 1, "S6",
                            "code span %s on a table row contains an unescaped "
                            "`|`: the renderer splits the row on it BEFORE parsing "
                            "the span, so this opens a cell. Write \\| inside tables."
                            % m.group(0)[:40], line))
                        break
    return out


def check_s2_table_continuity(docs):
    """A blank line terminates a GFM table. The rows after it have no header and
    no delimiter row of their own, so they render as paragraph text while the
    source looks complete -- fact 694's failure mode at table scale."""
    out = []
    for doc in docs:
        for i in range(1, len(doc.lines) - 1):
            if doc.fenced[i] or doc.lines[i].strip():
                continue
            prev, nxt = doc.lines[i - 1], doc.lines[i + 1]
            if doc.fenced[i - 1] or doc.fenced[i + 1]:
                continue
            if not (prev.lstrip().startswith("|") and nxt.lstrip().startswith("|")):
                continue
            # how many rows are stranded after this break?
            j = i + 1
            while j < len(doc.lines) and not doc.fenced[j] \
                    and doc.lines[j].lstrip().startswith("|"):
                j += 1
            stranded = j - (i + 1)
            has_header = is_delimiter_row(doc.lines[i + 2]) if i + 2 < len(doc.lines) else False
            if has_header:
                continue  # a genuinely new table, with its own header
            out.append(Violation(
                doc.rel, i + 1, "S2",
                "blank line inside a table: the %d row(s) below it have no header "
                "or delimiter row and will render as paragraph text, not as table "
                "rows. Delete the blank line." % stranded,
                "(blank) next row: " + nxt))
    return out


def git_index_eol(root):
    """Line endings **as committed**, from `git ls-files --eol`, or None.

    This exists because the obvious version of S4 -- count CRLF and LF on disk
    -- measures the developer's checkout, not the repository. With
    `core.autocrlf=true` (the Windows default) git rewrites LF to CRLF on
    checkout, so a corpus that is uniformly LF in the object database appears
    to be 13 files of mixed garbage in the working tree. MEASURED at
    82f13b0: 1351 tracked text files, `i/lf` for every one of them, zero
    `i/crlf` and zero `i/mixed` -- while the same tree on disk showed 13 mixed
    files. The disk version of this check is red on every Windows machine and
    green on every Linux one, which is the definition of a check that gets
    turned off. Ask git instead.

    Returns {relpath: eol} where eol is one of lf/crlf/mixed/none/-text, or
    None when git is unavailable, so the caller can skip and say so.
    """
    try:
        p = subprocess.run(["git", "ls-files", "--eol"], cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except (OSError, ValueError):
        return None
    if p.returncode != 0:
        return None
    out = {}
    for raw in p.stdout.decode("utf-8", "replace").splitlines():
        # "i/lf    w/crlf  attr/                 \tpath"
        if "\t" not in raw:
            continue
        fields, path = raw.split("\t", 1)
        m = re.match(r"i/(\S+)", fields.strip())
        if m:
            out[path.strip().replace("\\", "/")] = m.group(1)
    return out


def check_s3_hygiene(docs, index_eol):
    """Rule 37: assert the file still ends in exactly one newline after every
    fold -- `\\Z` in an item-end lookahead silently eats it."""
    out = []
    for doc in docs:
        n = len(doc.lines)
        if not doc.raw.endswith("\n"):
            out.append(Violation(doc.rel, n, "S3", "file does not end in a newline",
                                 doc.lines[-1] if doc.lines else ""))
        elif doc.raw.endswith("\n\n"):
            trailing = len(doc.raw) - len(doc.raw.rstrip("\n"))
            out.append(Violation(doc.rel, n, "S3",
                                 "file ends in %d newlines, expected exactly one"
                                 % trailing))
        # CR is judged on the committed blob, never on disk -- see git_index_eol.
        if doc.rel == SYNTHESIS and index_eol is not None:
            eol = index_eol.get(doc.rel)
            if eol in ("crlf", "mixed"):
                out.append(Violation(doc.rel, 1, "S3",
                                     "SYNTHESIS.md is committed with %s line "
                                     "endings; it is LF-only" % eol.upper()))
    return out


def check_s4_line_endings(docs, index_eol):
    """Mixed endings inside one file mean two tools wrote it. Harmless to a
    renderer, but it inflates a diff and so hides rule 29's deletion count,
    which is the only tell a string-anchored edit ate its own anchor.

    Judged on the committed blob. See git_index_eol for why the on-disk version
    of this check is worthless."""
    if index_eol is None:
        return []
    out = []
    for doc in docs:
        eol = index_eol.get(doc.rel)
        if eol == "mixed":
            out.append(Violation(doc.rel, 1, "S4",
                                 "committed with MIXED line endings"))
        elif eol == "crlf":
            out.append(Violation(doc.rel, 1, "S4",
                                 "committed with CRLF line endings; the corpus is LF"))
    return out


# --------------------------------------------------------------------------
# N — namespace
# --------------------------------------------------------------------------

def strip_code_spans(text):
    """Backtick spans are not markup. The corpus legitimately contains a literal
    `**` inside backticks; counting it as emphasis is a false positive. Measured:
    stripping is worth exactly 2 false positives on SYNTHESIS at 4c02816 --
    small, but the whole check is worthless if it fires on legitimate text."""
    return CODE_SPAN.sub("", text)


def numbered_item_units(index, sections):
    """Yield (section, number, first_line, label, text) for every numbered item
    in `sections`, grouped with its continuation lines.

    Grouping rule (M58c): continuation runs until a blank line, the next
    `^\\d+\\. ` item, or a heading. A numbered item may then continue in a
    further indented paragraph after a blank line -- 8 such paragraphs exist at
    4c02816 -- so those are yielded as their own units rather than dropped.
    """
    syn = index.syn
    for sec in sections:
        if sec not in index.spans:
            continue
        start, end = index.spans[sec]
        i = start
        current = None
        while i < end:
            if syn.fenced[i]:
                i += 1
                continue
            m = re.match(r"^(\d+)\. ", syn.lines[i])
            if m:
                num = int(m.group(1))
                j = i + 1
                while j < end and syn.lines[j].strip() \
                        and not re.match(r"^\d+\. ", syn.lines[j]) \
                        and not syn.lines[j].startswith("#"):
                    j += 1
                current = num
                yield (sec, num, i + 1, "item", "\n".join(syn.lines[i:j]))
                i = j
                continue
            line = syn.lines[i]
            if line.strip() and line.startswith((" ", "\t")) and current is not None:
                j = i
                while j < end and syn.lines[j].strip():
                    j += 1
                yield (sec, current, i + 1, "continuation paragraph",
                       "\n".join(syn.lines[i:j]))
                i = j
                continue
            if line.strip() and not line.startswith((" ", "\t")):
                current = None
            i += 1


MARKUP_TOKENS = (
    # (delimiter, regex matching one delimiter, what an odd count means)
    ("**", re.compile(r"\*\*"), "bold span never closes"),
    ("~~", re.compile(r"~~"), "strikethrough never closes, so text nobody "
                              "meant to retract reads as retracted"),
    ("__", re.compile(r"(?<!_)__(?!_)"), "bold span never closes"),
    ("*", re.compile(r"(?<![\\*])\*(?!\*)"), "italic span never closes"),
)


def check_s5_emphasis_balance(index):
    """Invariant B, generalised to every paired inline delimiter with a measured
    base rate of zero on this corpus.

    M58c/82f13b0: prepending a clause to a `N. **Headline**` item consumes its
    opening `**`, and the item silently mis-renders from there. Four §5 items
    had never closed their final span (disciplines 170, 181, 211, 221 -- the
    last over-closing with `****`).

    `~~` was added after the same defect recurred under a different delimiter:
    question 165 was amended with a strikethrough that opened `~~` and never
    closed it, and ~200 characters read as retracted. `**` parity passed
    throughout. In this corpus `~~` is how a retracted claim is marked -- 20
    closed spans at 10a03df -- so an unclosed one silently retracts text nobody
    meant to retract. That is worse than a mis-rendered heading: it inverts
    meaning rather than losing formatting.

    The method is the whole check. Measured on SYNTHESIS §5+§10 at 4c02816:

        naive, per LINE                     320 flags
        per ITEM, any line odd              114 flags   (74 in §5 alone)
        per ITEM, joined, code spans kept     2 flags
        per ITEM, joined, code spans stripped 0 flags   <- shipped

    Numbered items wrap across continuation lines and a span legitimately opens
    on one line and closes on another, so per-line counting is worse than
    useless. Both the join and the strip are load-bearing.

    Which delimiters ship, measured over 1060 units at 10a03df:

        `**`  0 odd      `~~`  0 odd      `__`  0 odd
        `*`   0 odd, once an escaped `\\*` is excluded (1 without: fact 82)
        `_`  17 odd -- NOT SHIPPED. `N_eff`, `sigma_beta`, `f_sig` and
             `phi_nonorm` are identifiers written outside code spans, and no
             counter can tell those from italics. Seventeen false positives is
             a check that gets switched off, so `_` is left alone.
    """
    out = []
    units = [("§%d %s" % (sec, label),
              ("discipline %d" % num) if sec == 5 else ("question %d" % num),
              line, text)
             for sec, num, line, label, text in numbered_item_units(index, (5, 10))]
    units += [("§4 fact row", "fact %d" % num, line, index.syn.lines[line - 1])
              for num, line in index.fact_rows_all]

    for label, who, line, text in units:
        stripped = strip_code_spans(text)
        for token, pat, meaning in MARKUP_TOKENS:
            n = len(pat.findall(stripped))
            if n % 2:
                out.append(Violation(
                    SYNTHESIS, line, "S5",
                    "%s (%s): odd number of `%s` (%d) after code spans are "
                    "stripped, so a %s"
                    % (who, label, token, n, meaning),
                    text.strip().split("\n")[0]))
        # The stripper is this linter's instrument: S5 above, A2's matching and
        # A4's all depend on it. A backtick it cannot pair leaves residue, and
        # from that point the strip is silently wrong. CODE_SPAN's `[^`]*`
        # matches newlines, so a code span that legitimately spans a line break
        # inside one unit leaves NO residue -- two such spans exist in §8/§9 and
        # were verified against this. Residue therefore means genuinely unpaired.
        residue = stripped.count("`")
        if residue:
            out.append(Violation(
                SYNTHESIS, line, "S5",
                "%s (%s): %d backtick(s) unpaired after code-span stripping, so "
                "every stripped-then-counted check in this linter is unreliable "
                "on this unit" % (who, label, residue),
                text.strip().split("\n")[0]))
    return out


def check_n1_duplicates(index):
    out = []
    seen = {}
    for num, line in index.fact_rows_all:
        if num in seen:
            out.append(Violation(SYNTHESIS, line, "N1",
                                 "fact %d is already declared at line %d (§4 fact rows)"
                                 % (num, seen[num]),
                                 index.syn.lines[line - 1]))
        else:
            seen[num] = line
    for kind, pairs in index.list_items_all.items():
        seen = {}
        for num, line in pairs:
            if num in seen:
                out.append(Violation(SYNTHESIS, line, "N1",
                                     "%s %d is already declared at line %d (§%d)"
                                     % (kind, num, seen[num], NAMESPACE_SECTION[kind]),
                                     index.syn.lines[line - 1]))
            else:
                seen[num] = line
    return out


def check_n2_placement(index):
    """Facts live in §4's table; disciplines in §5; questions in §10. A number
    is not evidence of which -- placement is (AGENTS rule 37)."""
    out = []
    syn = index.syn
    s4, e4 = index.spans[4]
    # a numbered list item at column 0 inside §4 is a discipline or question
    # that landed in the fact section
    for i in range(s4, e4):
        if syn.fenced[i]:
            continue
        if re.match(r"^\d+\. ", syn.lines[i]):
            out.append(Violation(SYNTHESIS, i + 1, "N2",
                                 "numbered list item inside §4; facts are `| N |` "
                                 "table rows, so this belongs in §5 or §10",
                                 syn.lines[i]))
    # a `| N | ... | ... | ... |` four-column row outside §4
    for i, line in enumerate(syn.lines):
        if syn.fenced[i] or s4 <= i < e4:
            continue
        if re.match(r"^\|\s*\d+\s*\|", line) and unescaped_pipe_count(line) == 5:
            out.append(Violation(SYNTHESIS, i + 1, "N2",
                                 "four-column `| N |` row outside §4; fact rows "
                                 "live in §4 only", line))
    return out


def check_n5_item_placement(index):
    """Invariant A, first half, in the only form that has power here.

    M58c: commit 39b5ca7 wrote question 170's verdict into DISCIPLINE 170.
    Measured rate 1 of 29 numbered items across four audited commits (~3%).
    The rule as first proposed -- "a `N. **...**` item must sit in §5 or §10" --
    was MEASURED against this document and fires 21 times on legitimate content:
    §1 (3 items), §3 (6), §7 (6), §8 (6). §7 is the `risk` namespace, so 15 of
    those 21 are ordinary prose enumerations in narrative sections. A check that
    fires 21 times gets turned off, so it is not shipped in that form.

    What IS shipped: four sections carry a table or plain prose and contain
    ZERO numbered items -- measured at 4c02816, and stable across this
    document's history. A numbered item appearing in one of them is a
    misfiled discipline, question or risk. §4 is the one that matters (facts are
    `| N |` rows, never list items) and is also covered by N2 from the other
    direction.

    If a narrative section legitimately gains a numbered list, this fires once
    and someone edits one tuple. That is the intended failure mode: a check that
    is cheap to re-baseline beats a check tuned until it can never fire.
    """
    out = []
    syn = index.syn
    named = {2: "Name", 4: "Measured facts", 6: "Novelty", 9: "Scope"}
    for sec in SECTIONS_WITHOUT_NUMBERED_ITEMS:
        if sec not in index.spans:
            continue
        start, end = index.spans[sec]
        for i in range(start, end):
            if syn.fenced[i]:
                continue
            m = re.match(r"^(\d+)\. ", syn.lines[i])
            if m:
                out.append(Violation(
                    SYNTHESIS, i + 1, "N5",
                    "numbered item %s in §%d (%s), which holds no numbering "
                    "namespace; disciplines belong in §5, questions in §10, "
                    "risks in §7"
                    % (m.group(1), sec, named.get(sec, "?")),
                    syn.lines[i]))
    return out


def check_n4_unallocated(index):
    """§4's preamble asserts which numbers are unallocated. That is a checkable
    claim about the document's own state."""
    out = []
    s4, e4 = index.spans[4]
    facts = index.items["fact"]
    pat = re.compile(r"(\d+)\s*[-\u2013]\s*(\d+)([^.]{0,60}?)(?:are|is)\s+unallocated", re.I)
    for i in range(s4, e4):
        if index.syn.fenced[i]:
            continue
        for m in pat.finditer(index.syn.lines[i]):
            lo, hi = int(m.group(1)), int(m.group(2))
            if hi < lo or hi - lo > 200:
                continue
            clash = [n for n in range(lo, hi + 1) if n in facts]
            if clash:
                out.append(Violation(
                    SYNTHESIS, i + 1, "N4",
                    "§4 says %d-%d are unallocated, but %s exist as fact row(s) "
                    "(first at line %d)"
                    % (lo, hi, ", ".join(str(c) for c in clash), facts[clash[0]]),
                    m.group(0)))
    return out


def advisory_n3_shape(index):
    """HEURISTIC. A discipline phrased as a question probably belongs in §10.
    Base rate 0 of 212 at the time of writing; it is still a heuristic."""
    out = []
    for num, line in index.list_items_all["discipline"]:
        body = index.item_body(5, num)
        m = re.match(r"^\d+\. \*\*(.+?)\*\*", body, re.S)
        lead = m.group(1) if m else body[:200]
        if "?" in lead:
            out.append(Violation(SYNTHESIS, line, "N3",
                                 "HEURISTIC: §5 discipline %d's lead sentence is "
                                 "phrased as a question; questions live in §10" % num,
                                 lead[:160]))
    return out


# --------------------------------------------------------------------------
# Q1 — quote provenance
# --------------------------------------------------------------------------

_QUOTE_SYM = {
    "\u03c3": "sigma", "\u03bc": "mu", "\u03bb": "lambda", "\u03b1": "alpha",
    "\u03b2": "beta", "\u03c1": "rho", "\u03ba": "kappa", "\u03b4": "delta",
    "\u03b5": "epsilon", "\u03b8": "theta", "\u03c4": "tau", "\u03c6": "phi",
    "\u03c7": "chi", "\u03b3": "gamma", "\u03c9": "omega", "\u0394": "delta",
    "\u03a3": "sum", "\u221a": "sqrt", "\u00d7": "x", "\u2248": "~",
    "\u2264": "<=", "\u2265": ">=", "\u00b2": "2", "\u00b3": "3",
    "\u2192": "->", "\u00b1": "+/-", "\u2260": "!=",
}

_QUOTE_PUNCT = (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                ("\u2014", "--"), ("\u2013", "-"), ("\u2212", "-"), ("\u00a0", " "))

_ATTR_VERB = (r"(?:says?|said|wrote|writes|reads?|states?|stated|reported|"
              r"reports?|calls?|claims?|concluded?)")

ATTRIBUTED_QUOTE = re.compile(
    r"\b(M\d+[a-z]?)\b(?:'s)?[^\"]{0,70}?\b" + _ATTR_VERB + r"\b[^\"]{0,40}?"
    r"\"([^\"]{20,400}?)\"", re.I)


def _quote_norm(s):
    s = unicodedata.normalize("NFKC", s)
    for a, b in _QUOTE_PUNCT:
        s = s.replace(a, b)
    for a, b in _QUOTE_SYM.items():
        s = s.replace(a, b)
    s = re.sub(r"[*`~_]", "", s)
    s = re.sub(r"\s*%", "%", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _quote_resolves(q, texts):
    """An elided quote resolves if every >=4-word fragment appears, in order."""
    frags = [f.strip() for f in re.split(r"\.{3}|\u2026", q)
             if len(f.strip().split()) >= 4]
    if not frags:
        return True
    for t in texts:
        pos = 0
        ok = True
        for fr in frags:
            i = t.find(fr, pos)
            if i < 0:
                ok = False
                break
            pos = i + len(fr)
        if ok:
            return True
    return False


def advisory_q1_quote_provenance(docs):
    """A quote attributed to a milestone must appear in that milestone's report.

    This exists because of a measured defect in the orchestrator, not in any
    agent. Six relay errors were made in a single session and agents caught all
    six by reading sources the orchestrator had summarised. The worst was fact
    986, which put quotation marks around a sentence M62 never wrote, crediting
    it with an independent replication it had explicitly disclaimed four lines
    later. C1 cannot see this: the citation `M62` resolves, because M62 exists.
    Only comparing the QUOTED TEXT against the cited report can see it.

    Written blind and run before its author was told what it should find, it
    recovered fact 986 unprompted, along with facts 996 and 1021 -- all three
    already independently corrected at source. That is the whole argument for
    it: it re-derived known defects it was not told about.

    TWO FALSE-POSITIVE MECHANISMS, both mechanical and both fixed by rule
    rather than by threshold:

      - ELISION. `"the sigma_F effect M66 found... measured on my own plant"`
        is a faithful quote with a clause removed. A substring test fails on it.
        Fragments are therefore matched independently and IN ORDER.
      - SYMBOL SPELLING. The corpus writes the same identifier as both `σ_F`
        and `sigma_F`. Greek and mathematical symbols are transliterated on both
        sides before comparison, so the two spellings compare equal.

    HONEST LIMITS, and they are why this ships as an advisory:

      - Both exclusions were derived from the corpus they are measured on, so
        the 0-false-positive residual is IN-SAMPLE, exactly as A4's was.
      - A quote can fail here for a reason that is nobody's fault: the cited
        report was CORRECTED AT SOURCE after the quote was folded. Fact 1021
        flags for precisely this reason. That is still worth surfacing -- a
        record quoting text that no longer exists is a record that cannot be
        checked -- but it is not a misquotation and must not be reported as one.
      - It cannot see the error class that actually caused three of the six:
        an over-broad claim in the orchestrator's OWN words, with no quotation
        marks to check. Fact 996's "any per-plane statistic" was a gain null
        only, and M73 found "surface of revolution" where the invariant needs a
        cylinder. **No lexical check can catch those**; the two candidate
        matchers tried before this one fired on 28% and 65% of all fact rows
        and were abandoned as unusable. Discipline 493 stands: a negative or
        universal claim cites nothing, and the machine is blind to it.

    THE RESIDUAL IS NOW FULLY ADJUDICATED: 8 at first run, 5 after repair.

    Two further false-positive mechanisms were found by hand-checking all eight
    against their sources, and both are recorded rather than coded around:

      - NEAREST-MILESTONE MISATTRIBUTION. Fact 775 names M48 and M54 in one
        row; the regex bound the quote to M48 because M48 appears first, but
        the prose attributes it to M54. A row naming two milestones can bind a
        quote to the wrong one.
      - QUOTING A RETRACTION. All five survivors quote a claim that the SAME
        fact retracts -- facts 986, 994, 996 and 1021 (twice). That is
        quotation used as evidence of an error, which is the opposite of
        misattribution, and A4 already carries the same exclusion for reported
        speech.

    Three rows were genuine and were repaired at source (775, 856, 887): all
    three put the orchestrator's OWN summary inside quotation marks and
    attributed it to a milestone. Fact 856 was the worst of them and is the
    reason this advisory earned its keep -- it attributed the phrase "every
    frame in the corpus" to M53, when M53 wrote "for the whole corpus" and had
    already marked its own claim REFUTED. `M54-clip-mask-measured.md:589`
    records who actually said it: the orchestrator, in a broadcast M54 names as
    "that universal quantifier". See fact 1053.

    Promotion to blocking therefore needs the retraction exclusion stated as a
    RULE. It is NOT coded here, because the only obvious implementation is a
    lexical retraction-marker matcher, and lexical matchers on this corpus were
    measured firing on 28% and 65% of all rows. Widening an exclusion until the
    number reaches zero is the failure A4's docstring warns about; a documented,
    adjudicated residual of 5 is the honest state. Until that rule exists, a RED
    gate here would block five agents for a defect that is the orchestrator's
    alone.
    """
    reports = {}
    for d in docs:
        m = re.match(r"^docs/research/(M\d+[a-z]?)-", d.rel)
        if m:
            reports.setdefault(m.group(1), []).append(_quote_norm(d.text))
    syn = [d for d in docs if d.rel == SYNTHESIS]
    if not syn:
        return []
    out = []
    for i, line in enumerate(syn[0].lines):
        if not re.match(r"^\| \d+ \|", line):
            continue
        parts = re.split(r"(?<!\\)\|", line)
        if len(parts) != 6:
            continue
        for milestone, quote in ATTRIBUTED_QUOTE.findall(parts[2] + " " + parts[3]):
            qn = _quote_norm(quote)
            if len(qn.split()) < 5:
                continue
            if _quote_resolves(qn, reports.get(milestone, [])):
                continue
            out.append(Violation(
                SYNTHESIS, i + 1, "Q1",
                "fact %s attributes a quote to %s that does not appear in %s's "
                "report (misquotation, or the source was corrected after the "
                "fold)" % (parts[1].strip(), milestone, milestone),
                qn[:160]))
    return out


# --------------------------------------------------------------------------
# C1 — citation resolution
# --------------------------------------------------------------------------

# The gap between the kind word and the number may wrap ONE line -- the corpus is
# hard-wrapped and 172 real citations sit across a line break -- but it may NOT
# cross a blank line. Measured 2026-08-24 (experiments/ORCH-drift-check/
# c1_gap_survey.py): 12832 citations on one line, 172 across one newline, and 20
# across a blank line of which **20/20 were false positives** -- a `## Facts`
# heading followed by a list item `1. **MEASURED...`, or M87-occlusion.md:3736's
# heading ending in the word "question" followed by a paragraph opening "49 986".
# 19 of the 20 had been passing SILENTLY because a phantom `Facts 1` resolves
# against fact 1, which exists; only the 20th pointed at a number that did not.
# Known residual hole, unmeasured and therefore not coded around: a heading
# followed by a digit-leading line with NO blank line between them would still
# match. No instance exists in the corpus today.
KIND_TOKEN = re.compile(
    r"(?<![-\w])(facts?|disciplines?|questions?|risks?|rules?)"
    r"(?![^\S\n]*\n[^\S\n]*\n)\s+(?=\d)", re.I)
CONNECTOR = re.compile(r"\A(\s*(?:,\s*and|,|;|/|&|and|through|to|\u2013|\u2014|-)\s*)(?=\d)")
MILESTONE_QUALIFIER = re.compile(
    r"\bM\d+[A-Za-z]*(?:-V)?\b(?:\s*\u00a7[\d.]+[a-z]?)?[\s,]*$")
PROPOSAL = re.compile(r"\b(propos\w+|reserv\w+|renumber\w+|unallocated)\b", re.I)

LOCAL_DECL = [
    re.compile(r"^\*\*(\d+)\.\s"),
    re.compile(r"^\|\s*(\d+)\s*\|"),
    re.compile(r"\*\*(?:Discipline|Question|Fact|Risk)\s+(\d+)\.?\*\*", re.I),
    # A declaration may carry a parenthetical label before the closing bold:
    # `**Fact 12 (MEASURED).**` is the corpus convention and was invisible to the
    # pattern above, which requires the number to abut the closing `**`. Measured
    # 2026-08-xx: 57 declarations across 6 reports were invisible, 29 in M48c alone.
    # Their local citations then resolved against SYNTHESIS's global numbering and
    # passed against an unrelated fact. See SYNTHESIS fact for the measurement.
    re.compile(r"\*\*(?:Discipline|Question|Fact|Risk)\s+(\d+)\s*\([^)\n]*\)\.?\*\*", re.I),
    re.compile(r"^#+\s*(?:Discipline|Question|Fact)\s+(\d+)\b", re.I),
]


def local_declarations(doc):
    out = set()
    for line in doc.lines:
        for pat in LOCAL_DECL:
            m = pat.search(line)
            if m:
                out.add(int(m.group(1)))
    return out


def iter_citations(doc):
    """Yield (kind, number, offset, raw, klass).

    klass is 'ref' for a corpus reference, 'sub' for a report-local sub-item
    label (`fact 198c`), 'qualified' for another document's numbering
    (`M25 §7 fact 190`), or 'block' for reservation notation (`facts 250+`).

    The number is a MAXIMAL digit run: `fact 200` never matches `fact 200a`.
    Fact 763 exists because a substring match could not tell those apart.
    """
    text = doc.text
    for m in KIND_TOKEN.finditer(text):
        kind = m.group(1).lower()
        if kind.endswith("s"):
            kind = kind[:-1]
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.start())
        line_end = len(text) if line_end < 0 else line_end
        before = text[line_start:m.start()]
        qualified = bool(MILESTONE_QUALIFIER.search(before))
        # `reserved` / `proposed` / `renumbered` may sit on either side of the
        # numbers: "*(facts 520-539 reserved for M45)*" puts it after.
        window = text[max(line_start, m.start() - 90):min(line_end, m.start() + 120)]
        proposal = bool(PROPOSAL.search(window))
        pos = m.end()
        while True:
            nm = re.compile(r"\d+").match(text, pos)
            if not nm:
                break
            num = int(nm.group(0))
            after = text[nm.end():nm.end() + 1]
            raw = text[m.start():nm.end() + (1 if after.isalpha() else 0)]
            if after.isalpha():
                yield (kind, num, nm.start(), raw, "sub")
                break
            if after == "+":
                yield (kind, num, nm.start(), raw, "block")
                break
            if after == "." and text[nm.end() + 1:nm.end() + 2].isdigit():
                break                                   # a decimal, e.g. 1.253
            if after in ("%", "\u00d7") or text[nm.end():nm.end() + 2] == "x ":
                break                                   # a quantity, e.g. 10x
            klass = "qualified" if (qualified or proposal) else "ref"
            yield (kind, num, nm.start(), raw, klass)
            pos = nm.end()
            cm = CONNECTOR.match(text[pos:pos + 14])
            if not cm:
                break
            pos += len(cm.group(1))


def check_c1_citations(docs, index):
    out = []
    syn_rel = SYNTHESIS
    for doc in docs:
        is_report = doc.rel.endswith(".md") and doc.rel != syn_rel
        local = local_declarations(doc) if is_report else set()
        for kind, num, off, raw, klass in iter_citations(doc):
            if klass != "ref":
                continue
            if index.resolves(kind, num):
                continue
            if num in local:
                continue                                # the report's own numbering
            line = doc.line_of(off)
            elsewhere = index.other_namespaces(num, kind)
            extra = (" — %d exists as %s" % (num, "/".join(elsewhere))) if elsewhere else \
                    (" — no item of any kind carries %d" % num)
            where = "AGENTS.md" if kind == "rule" else \
                    "SYNTHESIS §%d" % NAMESPACE_SECTION[kind]
            out.append(Violation(
                doc.rel, line, "C1",
                "`%s` does not resolve: %s has no %s %d%s"
                % (raw, where, kind, num, extra),
                doc.lines[line - 1]))
    return out


# --------------------------------------------------------------------------
# A — semantic
# --------------------------------------------------------------------------

CLOSES = re.compile(r"\b(closes?|closed|closing|answers?|answered)\s+question\s+(\d+)\b", re.I)


def paragraph_at(doc, i):
    """The scope an amendment has to live in to count as adjacent to its claim.

    For a table row that is the row itself: table rows are contiguous, so a
    paragraph walk would span the whole of §4 and every row would inherit every
    other row's "REOPENED". That bug made A1 silent on its own plant and was
    caught only because the power probe demanded to see the check fail
    (rule 36, discipline 351). For prose it is the paragraph.
    """
    if doc.lines[i].lstrip().startswith("|"):
        return doc.lines[i]
    a = i
    while a > 0 and doc.lines[a - 1].strip():
        a -= 1
    b = i
    while b + 1 < len(doc.lines) and doc.lines[b + 1].strip():
        b += 1
    return "\n".join(doc.lines[a:b + 1])


def check_a1_question_status(docs, index):
    """Fact 622 asserted "closes question 119" beside a headline recording that
    119 is REOPENED (fact 761's first instance). A row that claims to close a
    reopened question, and does not itself acknowledge the reopening, is a
    contradiction the document can detect on its own."""
    out = []
    reopened = set()
    for num, _line in index.list_items_all["question"]:
        if re.search(r"\bREOPENED\b", index.item_body(10, num)):
            reopened.add(num)
    if not reopened:
        return out
    for doc in docs:
        for i, line in enumerate(doc.lines):
            if doc.fenced[i]:
                continue
            hits = [m for m in CLOSES.finditer(line) if int(m.group(2)) in reopened]
            if not hits:
                continue
            para = paragraph_at(doc, i)
            if re.search(r"REOPEN", para, re.I) or "~~" in para:
                continue                            # the passage acknowledges it
            for m in hits:
                q = int(m.group(2))
                out.append(Violation(
                    doc.rel, i + 1, "A1",
                    "`%s`, but SYNTHESIS §10 marks question %d REOPENED (line %d) "
                    "and nothing in this passage says so"
                    % (m.group(0), q, index.items["question"][q]),
                    line))
    return out


NUM_WORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
INT_TOKEN = r"\d{1,4}(?![\d.,]?\d)(?![%\u00d7]|x\b|\s?(?:px|ms|DN|e-|s\b))"
ENUMERATION = re.compile(r"(?<![\d.\-])" + INT_TOKEN +
                         r"(?:\s*(?:,|;|/|,?\s*and|&)\s*" + INT_TOKEN + r")+")
N_OF_M = re.compile(r"\b(\d{1,4}|" + "|".join(NUM_WORD) + r")\s+of\s+\d{1,5}\s+(" +
                    CORPUS_NOUNS + r")\b", re.I)


def check_a2_count_vs_enumeration(index):
    """Fact 725 claimed "7 of 515 rows" and its very next sentence enumerated
    eight. Restricted to counts of CORPUS items in a row that also enumerates
    corpus numbers: the unrestricted form scored 4 flags and 0 true positives."""
    out = []
    for num, line_no in index.fact_rows_all:
        row = index.syn.lines[line_no - 1]
        lengths = set()
        spans = []
        for m in ENUMERATION.finditer(row):
            items = re.findall(r"\d+", m.group(0))
            if not all(index.resolves("fact", int(x)) or index.resolves("question", int(x))
                       for x in items):
                continue                     # a data list, not a corpus enumeration
            lengths.add(len(items))
            spans.append(m.group(0))
        if not lengths:
            continue
        for m in N_OF_M.finditer(row):
            tok = m.group(1).lower()
            n = int(tok) if tok.isdigit() else NUM_WORD[tok]
            if n in lengths:
                continue
            out.append(Violation(
                SYNTHESIS, line_no, "A2",
                "fact %d states `%s` but the row's corpus enumerations have "
                "length(s) %s; the count and the list disagree"
                % (num, m.group(0), sorted(lengths)),
                " || ".join(s[:90] for s in spans)))
    return out


# A settled question may be marked with any of these; the words are synonyms in
# practice, and A4 must not fire merely because a report said "answered" where
# §10 said "closed". Found out of sample -- see check_a4_status_coherence.
SETTLED_MARKERS = frozenset((
    "MOOT", "ANSWERED", "CLOSED", "RESOLVED", "REFUTED", "WITHDRAWN",
    "SUPERSEDED",
))

QUOTED_SPAN = re.compile(r"\"[^\"]*\"|\u201c[^\u201d]*\u201d")

# Hoisted to module level so heldout_probe.py measures the SHIPPED matcher
# rather than a copy of it that can drift out of step with this one.
A4_CLAIM = re.compile(
    r"\b(question|discipline)\s+(\d{1,4})\b(?![\w.])"
    r"(?P<mid>(?:(?!--)[^.;|)\u2014]){0,60}?)"
    r"\b(?P<mk>%s)\b" % "|".join(STATUS_MARKERS), re.I)
A4_NEGATION = re.compile(r"\b(cannot|can't|not|never|no longer|still|un)\b", re.I)


def a4_corroborated(body, marker):
    """True if `body` records a settled verdict compatible with `marker`."""
    wanted = SETTLED_MARKERS if marker in SETTLED_MARKERS else {marker}
    return any(re.search(r"\b%s\b" % re.escape(w), body, re.I) for w in wanted)


def check_a4_status_coherence(index):
    """If a fact says a question is answered, closed or moot, the question must
    say so itself.

    M58c: fact 771 asserted "Question 170 is MOOT" while §10's question 170
    carried no MOOT marker, because the verdict had been written into DISCIPLINE
    170 instead. C1 is silent -- question 170 exists, so the citation resolves.
    Only comparing the ASSERTED STATUS against the referenced item's own text
    can see it.

    This shipped first as an advisory, on a measured 32% residual that I called
    "prose, not a defect rate". That call was wrong, and the way it was wrong is
    worth recording: I measured the rate and did not read the six. Reading them
    against their §10 items gives four REAL inconsistencies (questions 101, 80,
    120 and 161 -- each asserted settled by a fact row while §10 still reads
    open, question 161's item still claiming a systematic that fact 804
    resolved) and two false positives. A rate is not an adjudication.

    The two false positives have grammatical signatures, not statistical ones,
    so they are excluded by rule rather than by threshold:

      - POSSESSIVE. "Question 132's leading hypothesis is closed" does not
        assert that question 132 is closed; the subject is the hypothesis, and
        §10's question 132 is correctly still UNVERIFIED.
      - REPORTED SPEECH. Fact 761 QUOTES `"Question 119 is answered negatively"`
        as an example of the defect it is reporting. Quoting a false sentence is
        not asserting it -- the same principle as the existing ~~strikethrough~~
        exclusion, where retracted text is not assertion either.

    HONEST LIMIT, and the reason this docstring is long: both exclusions were
    derived from the only two false positives in the corpus, so the measured
    0-false-positive rate is IN-SAMPLE. The rules are grammatical and should
    generalise, but that is ARGUED, not measured. If this check starts firing on
    prose, the exclusion list is where to look first -- and demoting it back to
    an advisory is the correct response, not widening the exclusions until the
    number goes away.

    OUT-OF-SAMPLE TEST. Running this matcher over every source EXCEPT
    SYNTHESIS.md -- 402 report files, commit messages, rust and OWNER-QUESTIONS,
    none of which informed the rules -- gave 67 candidates, and exposed two
    false-positive mechanisms the in-sample set structurally could not contain:

      1. MARKER VOCABULARY. M46 says "Question 120 is answered"; §10's question
         120 says `CLOSED`. The question IS settled; only the word differs. In
         §4 the words happened to align, so this was invisible. Corroboration is
         therefore tested against SETTLED_MARKERS as an equivalence class, not
         against the exact word. This preserves all four real detections at
         eceecb5, whose items carried NO status word at all -- verified by
         re-running against that blob.
      2. WINDOW BRIDGING. `discipline 316) -- **the brief's expectation is
         refuted` matched across a bracket and a dash into an unrelated clause.
         The 60-character window now stops at `)`, `--` and an em dash as well
         as at `.`, `;` and `|`.

    What the equivalence class costs: a claim of "answered" is now corroborated
    by an item reading `CLOSED, REOPENED` -- question 119's shape. A4 sees that
    §10 has an opinion, not that the opinion has since moved on. Ordering
    verdicts is beyond a regex, and a check that guesses at it would fire on
    every legitimately contested item.
    """
    out = []
    pat = A4_CLAIM
    negation = A4_NEGATION
    kind_section = {"question": 10, "discipline": 5}
    for i, line in enumerate(index.syn.lines):
        if index.syn.fenced[i]:
            continue
        bare = strip_code_spans(line)
        visible = STRIKETHROUGH.sub("", bare)
        quoted = [(m.start(), m.end()) for m in QUOTED_SPAN.finditer(bare)]
        for m in pat.finditer(bare):
            kind = m.group(1).lower()
            num = int(m.group(2))
            marker = m.group("mk").upper()
            body = index.item_body(kind_section[kind], num)
            if not body:
                continue                                  # C1 owns non-existence
            if a4_corroborated(body, marker):
                continue
            if m.group(0) not in visible:
                continue                                  # struck through
            if bare[m.end(2):m.end(2) + 2] in ("'s", "\u2019s"):
                continue                                  # possessive subject
            if any(a <= m.start() < b for a, b in quoted):
                continue                                  # reported speech
            if negation.search(m.group("mid")) or \
                    negation.search(bare[max(0, m.start() - 40):m.start()]):
                continue
            out.append(Violation(
                SYNTHESIS, i + 1, "A4",
                "this says %s %d is %s, but §%d's %s %d records no settled "
                "verdict at all. Either it was written into the wrong namespace "
                "(M58c, commit 39b5ca7) or §%d was never updated."
                % (kind, num, marker, kind_section[kind], kind, num,
                   kind_section[kind]),
                m.group(0)))
    return out


def advisory_a3_amendment(index):
    """HEURISTIC. Fact 761: "An amendment that leaves the headline intact is
    worse than no amendment." A marker in the Consequence or Source cell but not
    in the Fact cell is that shape -- but most instances are legitimate, so this
    is a review list, never a failure."""
    out = []
    pat = re.compile(r"\b(%s)\b" % "|".join(AMENDMENT_MARKERS))
    for num, line_no in index.fact_rows_all:
        cells = split_cells(index.syn.lines[line_no - 1])
        if len(cells) < 4:
            continue
        if pat.search(cells[2] + " " + cells[3]) and not pat.search(cells[1]):
            out.append(Violation(
                SYNTHESIS, line_no, "A3",
                "HEURISTIC: fact %d carries an amendment marker outside the Fact "
                "cell only; check the headline still says something true" % num,
                cells[1].strip()[:180]))
    return out



def check_c2_report_paths(md_docs, root):
    """C1 resolves fact/discipline/question NUMBERS and never looks at a file
    path, so a citation to a report that does not exist passes silently.

    Measured at 6202c9c: the orchestrator folded M63's milestone and cited
    `docs/research/M60-bimodality.md` three times -- in the very commit whose
    subject was that report's rename -- because M63 had renamed it to
    `M63-bimodality.md` and deliberately kept the *experiment* directory on the
    old stem with a forwarding note. Three dead citations, zero linter output.

    The exemption is grounded in DECLARED data, not inferred intent. Rule 41
    requires a milestone number to be allocated in AGENTS.md's allocation ledger
    *at dispatch*, before the agent writes anything, so the ledger legitimately
    names report paths that do not exist yet. A path appearing in that table is
    a forward reference and is exempt; anything else is a dead citation. This is
    deliberately not the heuristic M59 refused to build -- it reads a table the
    project already maintains rather than guessing from spelling.

    Power, measured against plants: a dead path not in the ledger is caught; a
    dead path present in the ledger is exempt; a live path never flags.
    """
    out = []
    research = os.path.join(root, "docs", "research")
    try:
        existing = set(os.listdir(research))
    except OSError:
        return out
    ledger = ""
    ap = os.path.join(root, AGENTS)
    if os.path.isfile(ap):
        ledger = io.open(ap, encoding="utf-8").read()
    pat = re.compile(r"docs/research/([A-Za-z0-9_.\-]+\.md)")
    for doc in md_docs:
        for i, line in enumerate(doc.lines, 1):
            for m in pat.finditer(line):
                name = m.group(1)
                if name in existing:
                    continue
                if ("docs/research/" + name) in ledger:
                    continue          # declared at dispatch; not yet written
                out.append(Violation(doc.rel, i, "C2",
                                     "cites docs/research/%s, which does not "
                                     "exist and is not allocated in the ledger"
                                     % name, line.strip()[:160]))
    return out

# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def check_c3_experiment_dir_attribution(root):
    """An `experiments/<Mn>-<slug>` directory must not be named for a milestone
    other than the one whose report owns `<slug>`.

    This exists because of fact 1049. `experiments/M60-bimodality/` holds the
    work reported in `M63-bimodality.md`; there is no M60 bimodality report and
    there never was. The orchestrator read the directory's number as the
    report's and briefed M74 to read a file that does not exist. Rule 40 caught
    it, because naming prior reports in a brief forces the agent to open them.

    Neither existing check can see this. C1 validates numbered citations
    against the record, and `M60` is a real milestone. C2 validates
    `docs/research/...` paths, and a directory is not one. **The misattribution
    lives in the filesystem, where nothing was looking.**

    ACCEPTED, NOT FIXED, and the distinction is deliberate. The directory holds
    252 files and is referenced from seventeen files including seven committed
    reports. Those reports are records of what was run at the time, under the
    path it was run at; rewriting them to match a rename would trade one stale
    reference for many falsified ones. The collision is therefore recorded here
    rather than erased, and any NEW one fails.

    Residual is zero once the accepted entry is excluded, so this ships
    blocking rather than advisory.
    """
    accepted = {
        "M60-bimodality": "M63 — reported in M63-bimodality.md; see fact 1049. "
                          "Not renamed: 252 files, 17 referencing files, 7 of "
                          "them committed reports that record this path.",
    }
    exp = os.path.join(root, "experiments")
    if not os.path.isdir(exp):
        return []
    owners = {}
    research = os.path.join(root, "docs", "research")
    if os.path.isdir(research):
        for name in os.listdir(research):
            m = re.match(r"(M\d+[a-z]?)-(.+)\.md$", name)
            if m:
                owners.setdefault(m.group(2).lower(), set()).add(m.group(1))
    out = []
    for name in sorted(os.listdir(exp)):
        if not os.path.isdir(os.path.join(exp, name)):
            continue
        m = re.match(r"(M\d+[a-z]?)-(.+)$", name, re.I)
        if not m:
            continue
        milestone, slug = m.group(1), m.group(2).lower()
        own = [f for f in os.listdir(research)
               if f.lower().startswith(milestone.lower() + "-")] if os.path.isdir(research) else []
        if any(slug in f.lower() for f in own):
            continue
        holders = owners.get(slug)
        if not holders:
            continue
        if milestone.lower() in {h.lower() for h in holders}:
            continue
        if name in accepted:
            continue
        out.append(Violation(
            "experiments/" + name, 0, "C3",
            "experiment directory is named for %s, but the report owning the "
            "subject '%s' is %s — a milestone number encoded in a path that "
            "no citation check validates (fact 1049)"
            % (milestone, slug, "/".join(sorted(holders))),
            "experiments/" + name))
    return out


def check_d1_duplicate_content(index):
    """Two fact numbers for one measurement is worse than none, because a later
    reader counts them as independent corroboration.

    N1 catches a repeated fact *number*. It cannot see the failure that actually
    happened: M82 reported across several turns, its final report restated a
    finding already folded from an earlier turn, and the same measurement was
    folded twice under two numbers (facts 1141 and 1160, discipline 585). A
    final report is *supposed* to be self-contained, so restatement is correct
    behaviour by the agent and a trap for whoever folds it.

    The signature is shared rare numerals. A measurement's distinctive constants
    -- `18.424`, `97.41`, `1.026` -- are effectively a fingerprint; prose is not.
    So: extract numeric tokens that are specific enough to be evidence, keep the
    ones that are globally rare, and flag any pair of facts sharing several.

    Deliberately linked rows are exempt. This corpus amends in place rather than
    deleting, so a refutation or a superseding row is *expected* to restate the
    numbers it is correcting, and saying so in the text is the convention that
    makes it legible.
    """
    out = []
    # a token is evidence-grade if it carries real precision: a decimal with at
    # least two fractional digits, or an integer of four or more digits.
    tok_re = re.compile(r"(?<![\w.])(\d+\.\d{2,}|\d{4,})(?![\w.])")

    claims = {}
    for num, line in index.fact_rows_all:
        row = index.syn.lines[line - 1]
        parts = re.split(r"(?<!\\)\|", row)
        if len(parts) < 4:
            continue
        toks = set(tok_re.findall(parts[2]))
        if toks:
            claims[num] = (line, toks, set(int(m) for m in
                                           re.findall(r"\b(\d{1,4})\b", row)))

    freq = {}
    for _num, (_line, toks, _refs) in claims.items():
        for t in toks:
            freq[t] = freq.get(t, 0) + 1
    # a token shared by many facts is a unit or a bar, not a fingerprint
    RARE = 3
    SHARED = 3
    for num, (line, toks, refs) in claims.items():
        rare = {t for t in toks if freq[t] <= RARE}
        if len(rare) < SHARED:
            continue
        for other, (oline, otoks, _orefs) in claims.items():
            if other >= num:
                continue
            # disclosure is pair-scoped: the later row must name the earlier
            # fact's number. A blanket keyword is not enough, and an exempt row
            # stays visible as a *target* -- the first version of this check
            # dropped exempt rows from the comparison set entirely and a planted
            # duplicate of the already-amended fact 1141 sailed straight through.
            if other in refs:
                continue
            common = rare & {t for t in otoks if freq[t] <= RARE}
            if len(common) >= SHARED:
                out.append(Violation(
                    SYNTHESIS, line, "D1",
                    "fact %d shares %d rare numerals with fact %d (line %d): %s. "
                    "If these are one measurement folded twice, mark the later row "
                    "as a duplicate and move any new material into the earlier one "
                    "(discipline 585). If the restatement is deliberate, name the "
                    "earlier fact's number in the row -- that is the disclosure."
                    % (num, len(common), other, oline,
                       ", ".join(sorted(common)[:6])),
                    index.syn.lines[line - 1]))
    return out


CHECKS = ["S1", "S2", "S3", "S4", "S5", "S6", "N1", "N2", "N4", "N5", "C1", "C2",
          "C3", "D1", "A1", "A2", "A4"]
ADVISORIES = ["N3", "A3", "Q1"]


def collect_files(root):
    md = [SYNTHESIS]
    research = os.path.join(root, "docs", "research")
    if os.path.isdir(research):
        for name in sorted(os.listdir(research)):
            rel = "docs/research/" + name
            if name.endswith(".md") and rel != SYNTHESIS:
                md.append(rel)
    for extra in (AGENTS, "README.md", "OWNER-QUESTIONS.md", "docs/captures-needed.md"):
        if os.path.isfile(os.path.join(root, extra)):
            md.append(extra)
    rs = []
    crates = os.path.join(root, "crates")
    for dirpath, dirnames, filenames in os.walk(crates):
        dirnames[:] = [d for d in dirnames if d != "target"]
        for name in sorted(filenames):
            if name.endswith(".rs"):
                rs.append(os.path.relpath(os.path.join(dirpath, name), root).replace("\\", "/"))
    return [p for p in md if os.path.isfile(os.path.join(root, p))], sorted(rs)


def main(argv=None):
    # The corpus is full of Greek, arrows and dashes, and this script's own
    # contract is that "every violation is printed". On Windows the default
    # console encoding is cp1252, which cannot encode U+0394 and friends, so
    # `print(v.render())` raised UnicodeEncodeError *mid-loop*: the header had
    # already printed, the violation list was truncated to nothing, the FAIL
    # summary never printed, and the traceback read like a broken tool rather
    # than a failing corpus. The exit code was 1 either way, so no caller could
    # tell the two apart. Never let the reporter's encoding decide which
    # violations exist. (SYNTHESIS discipline 702.)
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="repository root (default: .)")
    ap.add_argument("--advisory", action="store_true",
                    help="also print heuristic advisories (never affects exit code)")
    ap.add_argument("--only", action="append", metavar="ID",
                    help="run only these checks (repeatable); for power probes")
    ap.add_argument("--list", action="store_true", help="list check ids and exit")
    args = ap.parse_args(argv)

    if args.list:
        print("checks (failing):   " + " ".join(CHECKS))
        print("advisories (never fail): " + " ".join(ADVISORIES))
        return 0

    root = args.root
    syn_path = os.path.join(root, SYNTHESIS)
    if not os.path.isfile(syn_path):
        sys.stderr.write("corpus_lint: %s not found; run from the submodule root "
                         "or pass --root\n" % SYNTHESIS)
        return 2

    md_paths, rs_paths = collect_files(root)
    md_docs = [Doc(root, p) for p in md_paths]
    rs_docs = [Doc(root, p) for p in rs_paths]
    syn = next(d for d in md_docs if d.rel == SYNTHESIS)
    agents = next((d for d in md_docs if d.rel == AGENTS), None)
    if agents is None:
        agents = Doc(root, SYNTHESIS)  # degrade rather than crash
    index = Index(syn, agents)

    wanted = set()
    for spec in (args.only or CHECKS):
        for name in str(spec).replace(";", ",").split(","):
            name = name.strip().upper()
            if name:
                wanted.add(name)
    unknown = sorted(wanted - set(CHECKS) - set(ADVISORIES))
    if unknown:
        sys.stderr.write(
            "corpus_lint: unknown check id(s) %s. Known: %s. Refusing to run: an "
            "unrecognised --only silently selects NO checks and exits 0, which "
            "reads as a green gate.\n" % (", ".join(unknown),
                                          " ".join(CHECKS + ADVISORIES)))
        return 2
    index_eol = git_index_eol(root)
    violations = []
    if "S1" in wanted:
        violations += check_s1_cell_count(md_docs)
    if "S2" in wanted:
        violations += check_s2_table_continuity(md_docs)
    if "S3" in wanted:
        violations += check_s3_hygiene(md_docs + rs_docs, index_eol)
    if "S4" in wanted:
        violations += check_s4_line_endings(md_docs + rs_docs, index_eol)
    if "S5" in wanted:
        violations += check_s5_emphasis_balance(index)
    if "S6" in wanted:
        violations += check_s6_pipe_in_code_span(md_docs)
    if "N1" in wanted:
        violations += check_n1_duplicates(index)
    if "N2" in wanted:
        violations += check_n2_placement(index)
    if "N4" in wanted:
        violations += check_n4_unallocated(index)
    if "N5" in wanted:
        violations += check_n5_item_placement(index)
    if "C1" in wanted:
        violations += check_c1_citations(md_docs + rs_docs, index)
    if "C2" in wanted:
        violations += check_c2_report_paths(md_docs, root)
    if "C3" in wanted:
        violations += check_c3_experiment_dir_attribution(root)
    if "D1" in wanted:
        violations += check_d1_duplicate_content(index)
    if "A1" in wanted:
        violations += check_a1_question_status(md_docs + rs_docs, index)
    if "A2" in wanted:
        violations += check_a2_count_vs_enumeration(index)
    if "A4" in wanted:
        violations += check_a4_status_coherence(index)

    violations.sort(key=lambda v: (v.check, v.path, v.line))

    print("corpus_lint: %d markdown file(s), %d rust file(s); "
          "%d facts, %d disciplines, %d questions, %d risks, %d rules"
          % (len(md_docs), len(rs_docs), len(index.items["fact"]),
             len(index.items["discipline"]), len(index.items["question"]),
             len(index.items["risk"]), len(index.items["rule"])))
    print("corpus_lint: checks run: %s" % " ".join(sorted(wanted)))
    if index_eol is None and ({"S3", "S4"} & wanted):
        print("corpus_lint: NOTE — `git ls-files --eol` unavailable, so the "
              "line-ending half of S3 and all of S4 were SKIPPED. They are "
              "judged on the committed blob, never on the working tree.")
    print("")

    if violations:
        for v in violations:
            print(v.render())
        print("")
        by_check = {}
        for v in violations:
            by_check[v.check] = by_check.get(v.check, 0) + 1
        print("corpus_lint: FAIL — %d violation(s): %s"
              % (len(violations),
                 ", ".join("%s=%d" % kv for kv in sorted(by_check.items()))))
    else:
        print("corpus_lint: OK — no violations")

    if args.advisory:
        adv = (advisory_n3_shape(index) + advisory_a3_amendment(index)
               + advisory_q1_quote_provenance(md_docs))
        print("")
        print("--- ADVISORY (heuristics; these do NOT affect the exit code) ---")
        for v in adv:
            print(v.render())
        print("corpus_lint: %d advisory item(s)" % len(adv))

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

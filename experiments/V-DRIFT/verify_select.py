#!/usr/bin/env python3
"""Numeric verifier for docs/research/V-SELECT.md.

Every check is pinned to ONE canonical cell: a named section, a row prefix within
it, and a column index. That is not decoration. Section 4.1 and section 4.2 hold
tables with the SAME row labels (`s12`, `s4`, `s2`) and different values, so a
document-wide search for a row starting `| s12 |` matches two rows and a checker
that takes the first one silently verifies the wrong subject. The same trap cost
a full rewrite of V-DRIFT's verifier, where 22 checks failed purely because
values legitimately appear more than once in prose.

Run with --commission to plant defects and confirm the checker goes RED. A
verifier that has never been shown to fail is a green light of unknown meaning.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "research" / "V-SELECT.md"
NUM = re.compile(r"-?\d+\.?\d*")
GLYPH = {"\u00d7": "x", "\u2192": "->", "\u2014": "--", "\u2013": "-",
         "\u2212": "-", "\u2019": "'"}


def norm(s: str) -> str:
    """Fold the typographic glyphs the prose uses onto their ASCII spellings.

    The document is written with real en/em dashes, multiplication signs and
    arrows; the checks are easier to read and to keep correct in ASCII. Folding
    both sides means a check can never fail merely because the writer typed a
    nicer glyph than the checker did.
    """
    for k, v in GLYPH.items():
        s = s.replace(k, v)
    return s


def label(s: str) -> str:
    return norm(s).replace("**", "").replace("`", "").strip()


def sections(text: str) -> dict[str, list[str]]:
    """Split on '## ' and '### ' headings; key is the leading token, e.g. '4.1'.

    Both levels must be tracked. Section 4 opens with prose and then splits into
    4.1 (flower) and 4.2 (bee), whose tables carry IDENTICAL row labels. Parsing
    only '## ' collapses both subjects into one section and every row anchor in
    it becomes ambiguous.
    """
    out: dict[str, list[str]] = {}
    key = "0"
    for line in text.splitlines():
        m = re.match(r"^(#{2,3}) (.+)$", line)
        if m:
            head = m.group(2).strip()
            key = head.split()[0].rstrip(".") if head[0].isdigit() else head
            out.setdefault(key, [])
        else:
            out.setdefault(key, []).append(line)
    return out


def cell(s: str) -> float | None:
    m = NUM.search(s.replace("**", "").replace("`", "").replace(",", ""))
    return float(m.group()) if m else None


class Checker:
    def __init__(self, text: str) -> None:
        self.sec = sections(text)
        self.text = text
        self.ok = 0
        self.fail: list[str] = []

    def row(self, sec: str, prefix: str, col: int, want: float, what: str,
            ncells: int | None = None, rel: float = 6e-3) -> None:
        if sec not in self.sec:
            self.fail.append(f"{what}: section {sec} not found")
            return
        hits = []
        for line in self.sec[sec]:
            t = line.strip()
            if not t.startswith("|"):
                continue
            cells = [c.strip() for c in t.strip("|").split("|")]
            if not label(cells[0]).startswith(label(prefix)):
                continue
            if ncells is not None and len(cells) != ncells:
                continue
            hits.append(cells)
        if len(hits) != 1:
            self.fail.append(
                f"{what}: row '{prefix}' in section {sec} matched {len(hits)} rows, want 1")
            return
        got = cell(hits[0][col])
        if got is None:
            self.fail.append(f"{what}: cell {col} of '{prefix}' has no number")
            return
        if abs(got - want) > rel * max(abs(want), 1e-9):
            self.fail.append(f"{what}: section {sec} row '{prefix}' col {col} "
                             f"= {got}, want {want}")
            return
        self.ok += 1

    def has(self, needle: str, what: str) -> None:
        if re.search(r"\s+".join(map(re.escape, norm(needle).split())), norm(self.text)):
            self.ok += 1
        else:
            self.fail.append(f"{what}: text not found: {needle!r}")


def build(text: str) -> Checker:
    c = Checker(text)

    # 2.1 -- the failed first commissioning design (5 columns)
    c.row("2.1", "shift 1 px", 2, 0.8670, "2.1 shift1 reg", ncells=5)
    c.row("2.1", "shift 1 px", 3, 0.9024, "2.1 shift1 sel", ncells=5)
    c.row("2.1", "shift 4 px", 3, 3.0031, "2.1 shift4 sel", ncells=5)

    # 2.2 -- the commissioned instrument (6 columns)
    for pre, tot, reg, sel, ratio, fit in [
            ("null", 0.0, 0.0, 0.0, None, 0.0),
            ("shift 0.05 px", 0.07146, 0.04519, 0.03260, 0.721, 0.0560),
            ("shift 0.20 px", 0.28700, 0.18061, 0.13205, 0.731, 0.2241),
            ("shift 0.80 px", 1.21924, 0.70783, 0.64444, 0.910, 0.9093),
            ("blob-blur 0.1", 0.47797, 0.00187, 0.47777, 255.616, 0.0021),
            ("blob-blur 0.6", 1.10738, 0.00876, 1.10680, 126.384, 0.0062),
            ("interp only", 0.0, 0.0, 0.0, 0.0, None),
            ("scale 0.2%", 0.13378, 0.07962, 0.10466, 1.315, None),
            ("scale 0.8%", 0.56473, 0.31811, 0.40865, 1.285, None)]:
        c.row("2.2", pre, 1, tot, f"2.2 {pre} total", ncells=6, rel=2e-2)
        c.row("2.2", pre, 2, reg, f"2.2 {pre} reg", ncells=6, rel=2e-2)
        c.row("2.2", pre, 3, sel, f"2.2 {pre} sel", ncells=6, rel=2e-2)
        if ratio is not None:
            c.row("2.2", pre, 4, ratio, f"2.2 {pre} sel/reg", ncells=6, rel=2e-2)
        if fit is not None:
            c.row("2.2", pre, 5, fit, f"2.2 {pre} fit shift", ncells=6, rel=2e-2)

    c.row("2.2", "fitted translation recovers", 1, 13.7, "2.2 dose recovery", ncells=2)
    c.row("2.2", "separation", 1, 129.7, "2.2 separation", ncells=2)
    c.has("worst ratio over **both** families is **1.28**", "2.3 leak ratio")

    # 3 -- the confounded interleaved ladder on flower (10 columns)
    for pre, n, sep, shift, reg, seln, sela, hs, ab in [
            ("n34", 35, 6, 0.180, 0.3875, 1.5260, 98.9, 64.8, 1.18),
            ("n102", 103, 2, 0.229, 0.1967, 1.4951, 123.6, 82.6, 1.08),
            ("n204", 205, 1, 0.167, 0.1304, 1.3168, 133.5, 101.4, 0.98)]:
        c.row("3", pre, 1, n, f"3 {pre} N", ncells=10)
        c.row("3", pre, 3, sep, f"3 {pre} sep", ncells=10)
        c.row("3", pre, 4, shift, f"3 {pre} shift", ncells=10)
        c.row("3", pre, 5, reg, f"3 {pre} reg", ncells=10)
        c.row("3", pre, 6, seln, f"3 {pre} sel_net", ncells=10)
        c.row("3", pre, 7, sela, f"3 {pre} sel_abs", ncells=10)
        c.row("3", pre, 8, hs, f"3 {pre} high_S", ncells=10)
        c.row("3", pre, 9, ab, f"3 {pre} A/B", ncells=10)
    c.has("169.1 vs 100.5 -- a ratio of 1.68", "3 bee contamination")

    # 4.1 flower and 4.2 bee -- SAME row labels, different sections (12 columns)
    for sec, rows in [
            ("4.1", [("s12", 35, 0.9973, 0.9970, 0.259, 0.2177, 1.5294, 112.1, 73.3, 1.15),
                     ("s4", 103, 0.9973, 0.9972, 0.173, 0.1443, 1.4357, 128.0, 89.1, 1.02),
                     ("s2", 205, 0.9972, 0.9973, 0.167, 0.1304, 1.3168, 133.5, 101.4, 0.98)]),
            ("4.2", [("s12", 50, 0.9217, 0.9241, 0.356, 0.3176, 1.3816, 168.6, 122.0, 1.14),
                     ("s4", 150, 0.9277, 0.9340, 0.444, 0.4579, 1.2149, 193.0, 158.9, 1.10),
                     ("s2", 299, 0.9228, 0.9359, 0.618, 0.6044, 0.9519, 172.2, 180.9, 1.01)])]:
        for pre, n, ka, kb, shift, reg, seln, sela, hs, ab in rows:
            c.row(sec, pre, 1, n, f"{sec} {pre} N", ncells=12)
            c.row(sec, pre, 4, ka, f"{sec} {pre} kA", ncells=12)
            c.row(sec, pre, 5, kb, f"{sec} {pre} kB", ncells=12)
            c.row(sec, pre, 6, shift, f"{sec} {pre} shift", ncells=12)
            c.row(sec, pre, 7, reg, f"{sec} {pre} reg", ncells=12)
            c.row(sec, pre, 8, seln, f"{sec} {pre} sel_net", ncells=12)
            c.row(sec, pre, 9, sela, f"{sec} {pre} sel_abs", ncells=12)
            c.row(sec, pre, 10, hs, f"{sec} {pre} high_S", ncells=12)
            c.row(sec, pre, 11, ab, f"{sec} {pre} A/B", ncells=12)

    # 5 -- confidence depth ladders (6 columns), flower and bee rows are disjoint
    for pre, k, mean, med, p90, frac in [
            ("18", 0.9973, 761.8, 889.0, 1000.0, 81.14),
            ("52", 0.9973, 746.2, 923.0, 1000.0, 80.05),
            ("103", 0.9972, 737.3, 893.0, 990.0, 80.32),
            ("205", 0.9971, 728.4, 878.0, 976.0, 80.01),
            ("25", 0.9217, 458.2, 400.0, 960.0, 42.81),
            ("75", 0.9277, 425.6, 347.0, 933.0, 42.40),
            ("150", 0.9228, 417.7, 347.0, 933.0, 41.48),
            ("299", 0.9321, 418.5, 355.0, 930.0, 41.85)]:
        c.row("5", pre, 1, k, f"5 N={pre} k", ncells=6)
        c.row("5", pre, 2, mean, f"5 N={pre} mean", ncells=6)
        c.row("5", pre, 3, med, f"5 N={pre} median", ncells=6)
        c.row("5", pre, 4, p90, f"5 N={pre} p90", ncells=6)
        c.row("5", pre, 5, frac, f"5 N={pre} frac", ncells=6)

    # 6 -- confidence map commissioning (4 columns)
    for pre, mean, med, frac in [
            ("`--pyramid-select hard-max`", 691.3, 885.0, 74.46),
            ("`--pyramid-exponent 4.0`", 722.9, 885.0, 77.68),
            ("**shipped default**", 746.2, 923.0, 80.05),
            ("`--pyramid-exponent 0.5`", 811.6, 923.0, 86.77)]:
        c.row("6", pre, 1, mean, f"6 {pre[:24]} mean", ncells=4)
        c.row("6", pre, 2, med, f"6 {pre[:24]} median", ncells=4)
        c.row("6", pre, 3, frac, f"6 {pre[:24]} frac", ncells=4)
    c.has("span here is 691.3 -> 811.6, or 120.3 units", "6 knob span")

    # 7 -- headroom, the cloud-width-controlled reading (7 columns)
    for pre, n, dflt, hard, head, fd, fh in [
            ("flower", 18, 761.8, 710.8, 50.9, 81.14, 76.06),
            ("flower", 205, 728.4, 670.9, 57.5, 80.01, 74.22),
            ("bee", 25, 458.2, 402.7, 55.5, 42.81, 37.19),
            ("bee", 299, 418.5, 352.0, 66.5, 41.85, 35.53)]:
        # Row label alone is ambiguous (two flower rows, two bee rows), so each
        # check is pinned by matching the N cell first and then reading across.
        sec = c.sec.get("7", [])
        hits = [[x.strip() for x in l.strip().strip("|").split("|")]
                for l in sec if l.strip().startswith("|")
                and label(l.strip().strip("|").split("|")[0]).startswith(pre)
                and len([x for x in l.strip().strip("|").split("|")]) == 7
                and cell(l.strip().strip("|").split("|")[1]) == n]
        if len(hits) != 1:
            c.fail.append(f"7 {pre} N={n}: matched {len(hits)} rows, want 1")
            continue
        for col, want, what in ((2, dflt, "default"), (3, hard, "hard-max"),
                                (4, head, "headroom"), (5, fd, "frac default"),
                                (6, fh, "frac hard-max")):
            got = cell(hits[0][col])
            if got is None or abs(got - want) > 6e-3 * max(abs(want), 1e-9):
                c.fail.append(f"7 {pre} N={n} {what} = {got}, want {want}")
            else:
                c.ok += 1
    c.has("1.13x on flower, 1.20x on bee", "7 headroom growth")

    # 8 -- what rises with depth (3 columns)
    c.row("8", "`flower-bud-alone-cpl`", 2, 0.60, "8 flower reg ratio", ncells=3)
    c.row("8", "`bee-3-cpl`", 2, 1.90, "8 bee reg ratio", ncells=3)
    c.has("0.9228/0.9359", "8 bee k divergence")

    # Verdict-level claims that must track the tables
    c.has("0.86x on flower across N=35->205", "verdict flower fraction")
    c.has("0.69x on bee across N=50->299", "verdict bee fraction")
    c.has("1.19x and 1.02x respectively", "verdict absolute")
    c.has("headroom grows **1.13x on flower** (50.9 -> 57.5", "verdict flower headroom")
    c.has("**1.20x on bee** (55.5 -> 66.5", "verdict bee headroom")
    c.has("6.6 units on flower and 11.0 on bee", "verdict effect size")
    c.has("5.5% to 9.2% of that span", "verdict span fraction")
    c.has("761.8->728.4 on flower", "verdict flower confidence level")
    c.has("458.2->418.5 on bee", "verdict bee confidence level")
    return c


def commission(text: str) -> int:
    """Plant defects and require RED. Each anchor must be unique or we hard-error."""
    plants = [
        ("| s12 | 50 | 25 | 1 | 0.9217 | 0.9241 | 0.356 | 0.3176 |",
         "| s12 | 50 | 25 | 1 | 0.9217 | 0.9241 | 0.356 | 0.9176 |",
         "4.2 bee s12 reg"),
        ("| 299 | 0.9321 | 418.5 |", "| 299 | 0.9321 | 918.5 |",
         "5 bee N=299 mean confidence"),
        ("| `--pyramid-select hard-max` (argmax, one frame wins) | 691.3 |",
         "| `--pyramid-select hard-max` (argmax, one frame wins) | 991.3 |",
         "6 hard-max mean"),
        ("| bee | 299 | 418.5 | 352.0 | **+66.5** |",
         "| bee | 299 | 418.5 | 352.0 | **+36.5** |",
         "7 bee deep headroom"),
    ]
    bad = 0
    for old, new, what in plants:
        if text.count(old) != 1:
            raise SystemExit(f"MUTATION TARGET NOT FOUND OR AMBIGUOUS "
                             f"({text.count(old)} hits): {what}")
        c = build(text.replace(old, new, 1))
        caught = any(what.split()[0] in f or what[:12] in f for f in c.fail) or c.fail
        print(f"  [{'RED  ' if caught else 'GREEN'}] planted defect in {what}: "
              f"{len(c.fail)} check(s) failed")
        bad += not caught
    print(f"\n{'VERIFIER COMMISSIONED' if bad == 0 else f'{bad} PLANT(S) MISSED'}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()
    text = DOC.read_text(encoding="utf-8")
    if a.commission:
        return commission(text)
    c = build(text)
    for f in c.fail:
        print(f"  FAIL {f}")
    print(f"\n{c.ok} checks passed, {len(c.fail)} failed -- "
          f"{'GREEN' if not c.fail else 'RED'}")
    return 1 if c.fail else 0


if __name__ == "__main__":
    sys.exit(main())

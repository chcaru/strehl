"""Verify the generated gallery instead of trusting the generator's own log.

The generator prints "missing 1:1: 0" from the same variables it used to build
the page. That is a self-report, and this project has spent a night learning
what self-reports are worth. This re-reads the written HTML, extracts every
`src` and every local `href`, and checks each one against the filesystem --
which is the only claim that matters to someone opening the page.

It also checks the two things a broken gallery gets wrong while still passing a
link check: that every master has a card, and that the 1:1 crops are actually
large enough to be 1:1 rather than reduced images with a confident caption.
"""
import html.parser
import pathlib
import re
import sys
import urllib.parse

OUT = pathlib.Path(r"C:\dev\strehl-out\VIEW")
SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")
IDX = OUT / "index.html"

# These three were module constants pinned to ONE gallery. Passing an index path
# on the command line overrode only `idx`, so asset existence and master coverage
# were still resolved against C:\dev\strehl-out\VIEW and SHIP-V1 -- a different
# gallery and a superseded master set. The tool therefore printed GALLERY VERIFIED
# for a page nobody was looking at, which is the exact failure this file's own
# docstring is about. Paths are now derived from the index actually being checked.
def resolve(idx_path: pathlib.Path, ship_arg: str | None):
    """Derive the asset root and master set from the index under test."""
    out = idx_path.parent
    if ship_arg:
        return out, pathlib.Path(ship_arg)
    # Gallery asset names are '<master-stem>--<full|1to1>.<ext>'; recover the
    # master directory from the stems rather than assuming a version.
    stems = {p.name.split("--")[1] for p in (out / "assets").glob("*--*--*.*")
             if len(p.name.split("--")) >= 3}
    for s in sorted(stems):
        cand = pathlib.Path(r"C:\dev\strehl-out") / s
        if cand.is_dir():
            return out, cand
    return out, SHIP

# A "true 1:1" crop that is smaller than this on its long edge is either a
# reduced image or a crop so small it cannot support a print verdict.
MIN_1TO1_EDGE = 700

# Subjects the page explicitly claims are print-worthy where examined AND
# capture-limited elsewhere in frame. The page makes this claim in prose; this
# checks the rendered tags actually bear it out. Written down here rather than
# scraped from the page, so that deleting the tags cannot also delete the test.
CONFLICT = [
    "tweezers-cpl",
    "leaf-2-cpl",
    "flower-bud-with-background-fern-cpl",
]

VOID = {"br", "img", "hr", "meta", "link", "input"}


class Balance(html.parser.HTMLParser):
    """Track div/section nesting.

    Added after an edit to the generator silently truncated a <div class="note">
    and left its remaining prose dangling outside any element. The page still
    rendered, every link still resolved, and the verifier still printed
    GALLERY VERIFIED -- because nothing was checking structure. A malformed page
    that passes a link check is exactly the failure this file exists to catch.
    """

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        if tag in ("div", "section"):
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag not in ("div", "section"):
            return
        if not self.stack:
            self.errors.append(f"</{tag}> at line {self.getpos()[0]} closes nothing")
            return
        open_tag, line = self.stack.pop()
        if open_tag != tag:
            self.errors.append(
                f"</{tag}> at line {self.getpos()[0]} closes <{open_tag}> from line {line}")


def main() -> int:
    idx = IDX
    if len(sys.argv) > 1:
        idx = pathlib.Path(sys.argv[1])
    if not idx.exists():
        print(f"REFUSE: {idx} does not exist")
        return 1
    out, ship = resolve(idx, sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"index   : {idx}")
    print(f"assets  : {out}")
    print(f"masters : {ship}")
    if not ship.is_dir():
        print(f"REFUSE: master directory {ship} does not exist")
        return 1
    doc = idx.read_text(encoding="utf-8")

    srcs = re.findall(r'<img[^>]*\bsrc="([^"]+)"', doc)
    hrefs = re.findall(r'href="file:///([^"]+)"', doc)
    # Headings gained an inline badge span -- '<h2>name <span class="badge">...' --
    # so the original `<h2>([^<]+)</h2>` matched nothing and reported 0 cards while
    # 26 sections were present. Capture the whole heading and strip inline tags.
    raw_heads = re.findall(r'<section class="card">.*?<h2>(.*?)</h2>', doc, re.S)
    # Drop the badge span and its TEXT, not just its tags -- stripping tags alone
    # leaves 'bee-1-cpl--SHIP-V2 showcase' and every card reads as an orphan.
    cards = [re.sub(r"<[^>]+>", "",
                    re.sub(r"<span\b[^>]*>.*?</span>", "", h, flags=re.S)).strip()
             for h in raw_heads]
    if len(raw_heads) != doc.count('<section class="card">'):
        print(f"REFUSE: {doc.count('<section class=\"card\">')} card sections but "
              f"{len(raw_heads)} headings matched -- the heading pattern is stale")
        return 1

    print(f"cards: {len(cards)}   img src: {len(srcs)}   master links: {len(hrefs)}")

    bad_src = [s for s in srcs if not (out / urllib.parse.unquote(s)).exists()]
    bad_href = [h for h in hrefs
                if not pathlib.Path(urllib.parse.unquote(h)).exists()]

    masters = sorted(p.stem for p in ship.glob("*.tiff"))
    missing_cards = [m for m in masters if m not in cards]
    extra_cards = [c for c in cards if c not in masters]

    # Every card must carry a tag, or a subject silently reads as endorsed.
    #
    # Counted PER CARD, not globally. The first version of this counted every
    # tag span in the document and subtracted the card count, which meant a
    # decorative tag anywhere in the prose could offset a card that had lost
    # its tag and the total would still read 0. It was caught only because a
    # tag added to a note made the count go negative -- had the same edit also
    # dropped a card's tag, it would have read clean.
    #
    # NOTE the [^>]* before the closing quote: the capture tags carry a title=
    # attribute, and the original pattern required '">' immediately after the
    # class, so it could not see them at all.
    # PAGE FORMAT. Two generators have produced this page: a legacy one using a
    # 't-*/g-*' tag taxonomy, and build_view.py using 'badge b-*' verdicts. The
    # tag/prose checks below are written for the former. Run against the latter
    # they reported '26 cards missing a quality tag' -- which is not a failure of
    # the page, it is a check that does not apply. Report those as N/A explicitly:
    # a skipped check must never be counted alongside a passing one.
    fmt_tags = 'class="tag t-' in doc or 'class="tag g-' in doc
    fmt_badges = 'class="badge b-' in doc
    fmt = "legacy tag taxonomy" if fmt_tags else (
        "build_view badges" if fmt_badges else "UNRECOGNISED")
    print(f"format  : {fmt}")

    card_blocks = re.findall(
        r'<section class="card">(.*?)</section>', doc, re.S)
    untagged, uncaptioned, multitagged = 0, 0, []
    for blk in card_blocks:
        head = blk.split("</div>", 1)[0]
        q = re.findall(r'<span class="tag (t-[a-z-]+)"[^>]*>', head)
        c = re.findall(r'<span class="tag (g-[a-z-]+)"[^>]*>', head)
        name = re.search(r"<h2>([^<]+)</h2>", head)
        name = name.group(1) if name else "?"
        if fmt_tags:
            if len(q) == 0:
                untagged += 1
            if len(c) == 0:
                uncaptioned += 1
        if len(q) > 1 or len(c) > 1:
            multitagged.append(f"{name}: {len(q)} quality, {len(c)} capture")
    if len(card_blocks) != len(cards):
        multitagged.append(
            f"card section count {len(card_blocks)} != heading count {len(cards)}")

    # Structure: a truncated container renders fine and links fine.
    bal = Balance()
    bal.feed(doc)
    if bal.stack:
        bal.errors.extend(
            f"<{t}> opened at line {ln} never closed" for t, ln in bal.stack)

    # The page claims three subjects are print-worthy where examined and
    # capture-limited elsewhere. Check the tags actually say both.
    conflict_bad = []
    if fmt_tags:
        for stem in CONFLICT:
            # Card headings may carry a render-set suffix ('leaf-2-cpl--SHIP-V2')
            # and an inline badge span, so anchor on the stem as a prefix.
            m = re.search(
                r'<h2>' + re.escape(stem) + r'(?:--[^<\s]+)?[^<]*(?:<span.*?</span>)?'
                r'</h2>(.*?)</div>', doc, re.S)
            if not m:
                conflict_bad.append(f"{stem}: no card head found")
                continue
            head = m.group(1)
            has_print = 't-print' in head or 't-flagship' in head
            has_reshoot = 'g-gap' in head or 'g-move' in head
            if not (has_print and has_reshoot):
                conflict_bad.append(
                    f"{stem}: print={has_print} reshoot={has_reshoot}")

    small = []
    try:
        from PIL import Image
        for s in srcs:
            if "--1to1" not in s:
                continue
            p = out / urllib.parse.unquote(s)
            with Image.open(p) as im:
                if max(im.size) < MIN_1TO1_EDGE:
                    small.append((p.name, im.size))
        pil = True
    except ImportError:
        pil = False

    # A stated count must match the list printed beside it.
    #
    # This exists because the prose in this gallery has twice carried a number
    # that no longer matched the subjects listed next to it -- "four subjects",
    # then "eight" -- and nothing checked. A count in prose is a claim about
    # data that sits three inches away; it should not be possible to change one
    # without the other. Both sentences below must agree with the list AND with
    # each other, so a partial edit fails rather than half-passing.
    WORDS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
        "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
        "twenty": 20, "twenty-one": 21, "twenty-two": 22, "twenty-three": 23,
        "twenty-four": 24, "twenty-five": 25, "twenty-six": 26,
    }
    count_bad = []
    # The narrative summary sentences ("N subjects have been judged print-worthy",
    # "All N subjects have now been opened at 1:1") exist only on the legacy page.
    # Their absence there is a real regression and must fail; their absence on the
    # badge-format page means the check does not apply. Do not conflate the two.
    prose_na = not fmt_tags

    m_list = re.search(
        r"(\w[\w-]*) subjects have been judged print-worthy.*?"
        r"examined:(.*?)Compound-eye",
        doc, re.S | re.I)
    if not m_list:
        if not prose_na:
            count_bad.append("could not find the print-worthy sentence at all")
        listed = None
        stated = None
    else:
        stated = WORDS.get(m_list.group(1).lower())
        listed = len(re.findall(r"<code>([^<]+)</code>", m_list.group(2)))
        uniq = len(set(re.findall(r"<code>([^<]+)</code>", m_list.group(2))))
        if stated is None:
            count_bad.append(f"unparseable number word {m_list.group(1)!r}")
        elif stated != listed:
            count_bad.append(
                f"says {m_list.group(1)} ({stated}) print-worthy but lists {listed}")
        if uniq != listed:
            count_bad.append(
                f"print-worthy list repeats a subject ({listed} entries, {uniq} unique)")

    # The page used to claim every examined subject passed, so "opened" and
    # "print-worthy" were the same number and checking them equal was right.
    # That is no longer true: 26 opened, 24 print-worthy. The weak fix would be
    # to stop comparing them. The rule that replaces it is STRONGER -- the
    # difference must be discharged by NAMING every subject that was opened and
    # did not pass. That makes it impossible to quietly drop a subject from the
    # pass list, which is the failure the original check existed to prevent.
    m_open = re.search(
        r"(?:All\s+)?([\w-]+) subjects have now been opened at 1:1", doc, re.I)
    opened = None
    if not m_open:
        if not prose_na:
            count_bad.append("could not find the 'opened at 1:1' sentence at all")
    else:
        tok = m_open.group(1).lower()
        opened = WORDS.get(tok, int(tok) if tok.isdigit() else None)
        if opened is None:
            count_bad.append(f"unparseable 'opened at 1:1' number {tok!r}")

    if opened is not None and opened != len(cards):
        count_bad.append(
            f"'opened at 1:1' says {opened} but the page renders {len(cards)} cards")

    if opened is not None and listed is not None:
        shortfall = opened - listed
        if shortfall < 0:
            count_bad.append(
                f"more print-worthy ({listed}) than opened ({opened})")
        else:
            m_exc = re.search(
                r"not called print-worthy are not merge failures either:(.*?)"
                r"implied pass", doc, re.S | re.I)
            if not m_exc:
                if shortfall:
                    count_bad.append(
                        f"{shortfall} opened subject(s) are not print-worthy and "
                        f"no sentence names them")
            else:
                named = set(re.findall(r"<code>([^<]+)</code>", m_exc.group(1)))
                if len(named) != shortfall:
                    count_bad.append(
                        f"{shortfall} opened subject(s) did not pass but "
                        f"{len(named)} are named ({sorted(named)})")
                overlap = named & set(
                    re.findall(r"<code>([^<]+)</code>", m_list.group(2)))
                if overlap:
                    count_bad.append(
                        f"subject named as NOT print-worthy also appears in the "
                        f"print-worthy list: {sorted(overlap)}")

    print()
    print(f"broken image src              : {len(bad_src)}")
    print(f"broken master links           : {len(bad_href)}")
    print(f"masters with no card          : {len(missing_cards)}")
    print(f"cards with no master          : {len(extra_cards)}")
    na = "n/a (badge-format page; check belongs to the legacy tag taxonomy)"
    print(f"cards missing a quality tag   : {untagged if fmt_tags else na}")
    print(f"cards missing a capture tag   : {uncaptioned if fmt_tags else na}")
    print(f"cards with duplicate tags     : {len(multitagged)}")
    print(f"malformed div/section nesting : {len(bal.errors)}")
    print(f"stated retouch/reshoot splits not borne out by tags : "
          f"{len(conflict_bad) if fmt_tags else na}")
    print(f"stated counts disagreeing with the list beside them : "
          f"{len(count_bad) if not prose_na else na}")
    if pil:
        print(f"1:1 crops under {MIN_1TO1_EDGE}px long edge : {len(small)}")
    else:
        print("1:1 crop size check           : SKIPPED (Pillow not available)")

    for label, items in (
        ("broken src", bad_src),
        ("broken href", bad_href),
        ("no card", missing_cards),
        ("orphan card", extra_cards),
        ("too small", small),
        ("structure", bal.errors),
        ("duplicate tags", multitagged),
        ("split not borne out", conflict_bad),
        ("count mismatch", count_bad),
    ):
        for it in items[:8]:
            print(f"  {label}: {it}")

    ok = (not bad_src and not bad_href and not missing_cards
          and not extra_cards and untagged == 0 and (not pil or not small)
          and uncaptioned == 0 and not bal.errors and not conflict_bad
          and not multitagged and not count_bad)
    print()
    print("GALLERY VERIFIED" if ok else "GALLERY NOT VERIFIED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

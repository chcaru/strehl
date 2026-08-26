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
    doc = idx.read_text(encoding="utf-8")

    srcs = re.findall(r'<img[^>]*\bsrc="([^"]+)"', doc)
    hrefs = re.findall(r'href="file:///([^"]+)"', doc)
    cards = re.findall(r'<section class="card">.*?<h2>([^<]+)</h2>', doc, re.S)

    print(f"cards: {len(cards)}   img src: {len(srcs)}   master links: {len(hrefs)}")

    bad_src = [s for s in srcs if not (OUT / urllib.parse.unquote(s)).exists()]
    bad_href = [h for h in hrefs
                if not pathlib.Path(urllib.parse.unquote(h)).exists()]

    masters = sorted(p.stem for p in SHIP.glob("*.tiff"))
    missing_cards = [m for m in masters if m not in cards]
    extra_cards = [c for c in cards if c not in masters]

    # Every card must carry a tag, or a subject silently reads as endorsed.
    # NOTE the [^>]* before the closing quote: the capture tags carry a title=
    # attribute, and the original pattern required '">' immediately after the
    # class, so it could not see them at all.
    tags = re.findall(r'<span class="tag (t-[a-z-]+)"[^>]*>', doc)
    untagged = len(cards) - len(tags)

    # The capture/reshoot verdict is a second, independent tag per card.
    cap_tags = re.findall(r'<span class="tag (g-[a-z-]+)"[^>]*>', doc)
    uncaptioned = len(cards) - len(cap_tags)

    # Structure: a truncated container renders fine and links fine.
    bal = Balance()
    bal.feed(doc)
    if bal.stack:
        bal.errors.extend(
            f"<{t}> opened at line {ln} never closed" for t, ln in bal.stack)

    # The page claims three subjects are print-worthy where examined and
    # capture-limited elsewhere. Check the tags actually say both.
    conflict_bad = []
    for stem in CONFLICT:
        m = re.search(
            r'<h2>' + re.escape(stem) + r'</h2>(.*?)</div>', doc, re.S)
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
            p = OUT / urllib.parse.unquote(s)
            with Image.open(p) as im:
                if max(im.size) < MIN_1TO1_EDGE:
                    small.append((p.name, im.size))
        pil = True
    except ImportError:
        pil = False

    print()
    print(f"broken image src              : {len(bad_src)}")
    print(f"broken master links           : {len(bad_href)}")
    print(f"masters with no card          : {len(missing_cards)}")
    print(f"cards with no master          : {len(extra_cards)}")
    print(f"cards missing a quality tag   : {untagged}")
    print(f"cards missing a capture tag   : {uncaptioned}")
    print(f"malformed div/section nesting : {len(bal.errors)}")
    print(f"stated retouch/reshoot splits not borne out by tags : "
          f"{len(conflict_bad)}")
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
        ("split not borne out", conflict_bad),
    ):
        for it in items[:8]:
            print(f"  {label}: {it}")

    ok = (not bad_src and not bad_href and not missing_cards
          and not extra_cards and untagged == 0 and (not pil or not small)
          and uncaptioned == 0 and not bal.errors and not conflict_bad)
    print()
    print("GALLERY VERIFIED" if ok else "GALLERY NOT VERIFIED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

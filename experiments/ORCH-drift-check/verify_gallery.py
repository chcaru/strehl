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


def main() -> int:
    if not IDX.exists():
        print(f"REFUSE: {IDX} does not exist")
        return 1
    doc = IDX.read_text(encoding="utf-8")

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
    tags = re.findall(r'<span class="tag ([a-z-]+)">', doc)
    untagged = len(cards) - len(tags)

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
    ):
        for it in items[:8]:
            print(f"  {label}: {it}")

    ok = (not bad_src and not bad_href and not missing_cards
          and not extra_cards and untagged == 0 and (not pil or not small))
    print()
    print("GALLERY VERIFIED" if ok else "GALLERY NOT VERIFIED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

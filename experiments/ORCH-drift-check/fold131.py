"""Fold the gear-dispatch gap -- the blocker to defaulting the CA correction ON.

Facts 1592-1594, discipline 820.

The measured CA win (facts 1587-1589) cannot be defaulted on, because the product
has no way to know a capture came from the gear the profile describes.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1591 |")
disc_line = full_line(raw, "819. ")

NEW_FACTS = [
    (
        1592,
        "MEASURED",
        "ORCH",
        "**STREHL PARSES NO CAMERA IDENTITY WHATSOEVER. There is no make, model, lens, "
        "focal-length or aperture tag read anywhere in the product.** `git grep` over "
        "every production `.rs` for `0x010f`, `0x0110`, `\"Make\"`, `\"Model\"`, "
        "`LensSpec` and `maker_note` returns **nothing**, and `strehl-raw`'s public "
        "surface exposes no such field. `OpticalProfile` (`optics.rs:123`) carries a "
        "`key` and is selected **only** by a hand-typed `STREHL_FIX_CA` value. **The "
        "optical-profile plugin has its data and no dispatch.**",
    ),
    (
        1593,
        "MEASURED",
        "ORCH",
        "**THAT GAP IS WHAT BLOCKS THE PROJECT'S ONE READY-TO-SHIP QUALITY WIN.** The CA "
        "correction is measured to cut edge-localised chroma excess by **61.0 %** and "
        "**58.7 %** and to be visibly cleaner by eye (facts 1587-1589), and it is "
        "default-OFF (fact 1579). **It cannot simply be switched on**, because the shipped "
        "profile describes one specific optical path -- A7C2 + FE100GM + 2x TC + X4 CPL "
        "-- and the product cannot tell whether the frames in front of it came from that "
        "path. Defaulting it on would apply one photographer's measured aberration to "
        "everybody's glass. **The correct default is 'on when the capture matches a known "
        "profile, off otherwise', and the matching half does not exist.**",
    ),
    (
        1594,
        "ARGUED",
        "ORCH",
        "**AND THE FAILURE IS SILENT IN THE DANGEROUS DIRECTION.** M109's `d142783` "
        "preflight validates that a named profile **exists**, which catches a typo in "
        "0.235 s. It cannot catch a **mismatch** -- a correctly-spelled key naming real "
        "glass that is not the glass in the capture. That path applies a wrong optical "
        "model at full strength, completes successfully, and produces fringes that a user "
        "would read as the lens's own. **Key-existence validation and gear-match "
        "validation are different checks and only the first is built.** Marked ARGUED: no "
        "mismatched render has been measured, and the size of the resulting error is "
        "unknown.",
    ),
]

NEW_DISCS = [
    (
        820,
        "**A plugin system needs the data AND the dispatch that selects it; shipping the "
        "data alone leaves the capability un-defaultable and silently misapplicable.** "
        "strehl has a measured optical profile and no way to recognise the gear it "
        "describes (facts 1592-1593), so its best-measured correction must stay off and "
        "can be pointed at the wrong glass by hand. **When a profile is keyed to physical "
        "hardware, the identification of that hardware is part of the plugin, not a "
        "convenience on top of it** -- and until it exists, every claim of the form 'the "
        "tool corrects X' is really 'the tool corrects X if the operator knows to ask'.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))

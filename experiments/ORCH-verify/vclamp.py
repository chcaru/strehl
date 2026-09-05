"""Check the verbatim quotes in ORCH-clamp-default-decision.md against their sources.

Quotes are compared on whitespace-collapsed text because both the quoting and the
quoted documents are hard-wrapped, so a phrase legitimately spans line breaks.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
KERNEL = ROOT / "docs" / "research" / "ORCH-kernel-decision.md"
PASSABILITY = ROOT / "docs" / "research" / "M136-m8-passability.md"
DECISION = ROOT / "docs" / "research" / "ORCH-clamp-default-decision.md"


def collapse(text):
    return re.sub(r"\s+", " ", text)


# (label, source path, exact phrase as it must appear in the source)
QUOTES = [
    ("known-defeat clipping", SCORECARD,
     "destructive clipping can force a zero rate"),
    ("known-defeat clamping", SCORECARD,
     "Final clamping can erase M8-O evidence"),
    ("M1 is the control", SCORECARD,
     "A future M1 and the retained M4 flat-power-plus-transfer component are the "
     "owner-gate controls against buying the hull result through sharpening, "
     "attenuation, or clamping."),
    ("SOTA limit", SCORECARD,
     "While M1 is absent, M8 may prove only this internal invariant, not SOTA."),
    ("M8-R figure", PASSABILITY,
     "63,191,176 / 6,131,678,976 = 1.030569%"),
    ("N1 outranks any metric", KERNEL,
     "This is fact 1374's real concern and it outranks any metric."),
    ("discipline 890 gate", KERNEL,
     "The gate that should have failed was never written"),
    ("metric gaming ruling", PASSABILITY,
     "metric gaming and an unearned product pass"),
    ("in-hull bit-identical", PASSABILITY,
     "leaves already\nin-hull Catmull-Rom values bit-identical"),
    ("M4 co-control not dropped", DECISION,
     "silently drops M4"),
]

failures = []
checked = 0
for label, path, phrase in QUOTES:
    checked += 1
    if not path.exists():
        failures.append(f"{label}: SOURCE MISSING {path}")
        continue
    hay = collapse(path.read_text(encoding="utf-8"))
    needle = collapse(phrase)
    n = hay.count(needle)
    if n != 1:
        failures.append(f"{label}: matched {n} times in {path.name}, expected exactly 1")

# Each corrected anchor must be pinned to ITS OWN site, not merely present
# somewhere in the document. A bare presence test is satisfied by any duplicate:
# `:1631` also occurs in the citation-correction paragraph, so deleting it from
# the blockquote left a presence test GREEN. Commissioning arm A caught exactly
# that and this is the repair.
dec = collapse(DECISION.read_text(encoding="utf-8"))
SITED_ANCHORS = [
    ("known-defeat blockquote",
     '`docs/proposals/2026-09-sota-scorecard.md:1629-1631` — **"Known defeat.**'),
    ("M1/M4 control blockquote",
     '`docs/proposals/2026-09-sota-scorecard.md:1639-1642` — **"A future M1 and the'),
    ("citation correction names :1642",
     "The correct anchors are `:1631` (known defeat) and `:1639-1642`"),
]
for label, anchor in SITED_ANCHORS:
    checked += 1
    n = dec.count(collapse(anchor))
    if n != 1:
        failures.append(f"sited anchor {label!r}: matched {n} times, expected exactly 1")

# :1573-1582 may appear ONLY inside the citation-correction paragraph that
# explains it is wrong. It must never appear as a live citation.
occurrences = dec.count(":1573-1582")
checked += 1
if occurrences != 1:
    failures.append(
        f"':1573-1582' appears {occurrences} times; expected exactly 1 "
        "(inside the citation correction only)"
    )
elif "are the M8-O v1.5 legitimacy ruling, not" not in dec:
    failures.append("':1573-1582' present but the retraction sentence is missing")

# --- Amendment 1 / N6: the three live code facts, read from the Rust source ---
# These are pinned against crates/ rather than against the prose, so that a
# change to the code that invalidates N6's premise fails here rather than
# silently leaving a stale ruling in force.
_align = (ROOT / "crates" / "strehl-core" / "src" / "align.rs").read_text(
    encoding="utf-8", errors="replace")
_restore = (ROOT / "crates" / "strehl-core" / "src" / "restore.rs").read_text(
    encoding="utf-8", errors="replace")

_code_facts = [
    ("resampler enum still has six variants",
     all(collapse("Resampler::%s" % v) in collapse(_align)
         for v in ("Nearest", "Bilinear", "CatmullRom", "ClampedCatmullRom",
                   "Lanczos2", "Lanczos3"))),
    ("bilinear tap is still non-negative",
     collapse("Resampler::Bilinear => (1.0 - a).max(0.0),") in collapse(_restore)),
    ("restoration still refuses only the clamped kernel",
     collapse("!matches!(r, Resampler::ClampedCatmullRom)") in collapse(_restore)),
]
for _label, _ok in _code_facts:
    checked += 1
    if not _ok:
        failures.append(
            f"{_label}: FALSE. Amendment 1 / N6 rests on this code fact; if the "
            "code changed, the ruling must be re-derived, not left standing.")

# N6 and the coupling claim must both survive in the prose.
# OWNER/decision prose puts rulings in blockquotes, so '> ' markers land
# mid-sentence once whitespace is collapsed. Strip them for these quotes only,
# leaving the checks above reading exactly what they read before.
_dec_bq = collapse(re.sub(r"(?m)^[ \t]*>[ \t]?", "", DECISION.read_text(
    encoding="utf-8", errors="replace")))
for _label, _quote in (
    ("N6 prohibition",
     "No configuration change may be adopted as a route to an M8 pass while "
     "blocker `(a)` is open, if that change buys its out-of-range rate by "
     "altering the resampling kernel."),
    ("M8 coupled to (a)",
     "**M8 cannot be honestly passed before `(a)` closes.**"),
    ("N6 states its own falsifier",
     "it must be **qualified rather than footnoted**"),
):
    checked += 1
    if collapse(_quote) not in _dec_bq:
        failures.append(f"{_label}: missing from the decision document")

print(f"checked   {checked}")
print(f"failures  {len(failures)}")
for f in failures:
    print("  FAIL", f)
print("GREEN" if not failures else "RED")
sys.exit(1 if failures else 0)

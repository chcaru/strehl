"""Amend facts 1483-1487 and discipline 759 in place; fold M109's resolving measurements.

ORCH built a five-fact narrative on three "it does nothing" signals. M109 measured
that two of the three were structurally incapable of seeing the effect, and that the
third disagreed by subject rather than by instrument. Correcting in place per
discipline 746 -- amend by dated addendum, never silently rewrite.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()

AMENDMENTS = [
    # (unique anchor, appended text)
    (
        "belongs to the first path only. |",
        "belongs to the first path only. **AMENDED 2026-08-24 -- THIS FINAL SENTENCE IS "
        "REFUTED (fact 1491).** M109 measured the defect on **both** paths on the same "
        "subject `dry-erase-marker-head-cpl`: `strehl stack` **2.0017 %** of frame with "
        "green offset **-0.1028**, argmax-baseline 0.3378 %. The quoted 2.002 % and ~0.10 "
        "were **`strehl stack` figures all along**, taken from ORCH's own reproduce "
        "command; only the `0.3378 % -> 0.0944 %` pair was argmax, and it was labelled "
        "argmax every time it appeared. The commit archaeology in this row is accurate; "
        "the inference drawn from it was not. |",
    ),
    (
        "so the defect had every opportunity to appear. |",
        "so the defect had every opportunity to appear. **AMENDED 2026-08-24 -- SCOPE "
        "CORRECTED (fact 1494).** These four subjects are genuinely neutral, but this is "
        "**not** a general null for the default path: **none of the four is the affected "
        "subject**. On `dry-erase-marker-head-cpl` the defect is present at 2.0017 %. "
        "M110's selector is **not** blind to it either -- it covers **99.04 %** of that "
        "subject's magenta population. M110 and M109 disagree **by subject, not by "
        "instrument**, and both measurements stand. |",
    ),
    (
        "the ported clip is inert on the default path for every stack so far tested. |",
        "the ported clip is inert on the default path for every stack so far tested. "
        "**AMENDED 2026-08-24 -- THIS ROW IS REFUTED IN FULL (fact 1493). It is the "
        "worst inference of the night and it was ORCH's.** The byte-freeze renders the "
        "**measurement** path -- default, binned, linear, camera-native -- while the clip "
        "is **viewing-path only (`--srgb`)**, because ORCH's own brief required it to be: "
        "*\"the byte-frozen measurement output must not change by a single byte.\"* A HOLD "
        "there is the **designed outcome** and carries **zero information** about "
        "inertness. This was not an independent corroboration; it was a test engineered to "
        "be unable to see the change, read as evidence the change was absent. |",
    ),
    (
        "is an argmax phenomenon, and was never a property of the shipped render. |",
        "is an argmax phenomenon, and was never a property of the shipped render. "
        "**AMENDED 2026-08-24 -- REFUTED (fact 1491).** The dilution argument is "
        "physically reasonable and empirically wrong here: the defect is **larger** on the "
        "merged path (2.0017 %) than on argmax (0.3378 %). Retained as a worked example of "
        "a plausible mechanism invented to explain an artefact of two blind instruments. |",
    ),
    (
        "the fourth instance of this error class in one night, and roughly an hour after "
        "folding discipline 758 against it (facts 1483, 1484).",
        "the fourth instance of this error class in one night, and roughly an hour after "
        "folding discipline 758 against it (facts 1483, 1484). **AMENDED 2026-08-24 -- THE "
        "PRINCIPLE STANDS; THIS INSTANTIATION DOES NOT.** ORCH did **not** commit this "
        "error: the broadcast figures were `strehl stack` figures quoted as `strehl stack` "
        "figures, and argmax-only numbers stayed labelled argmax. The real error was "
        "different and is recorded as discipline **763**. Keep this discipline for the "
        "general rule, which remains sound; strike the example.",
    ),
]

for anchor, replacement in AMENDMENTS:
    n = raw.count(anchor)
    assert n == 1, "AMENDMENT ANCHOR NOT UNIQUE (%d hits): %s" % (n, anchor[:70])
    raw = raw.replace(anchor, replacement, 1)
    print("amended: %s..." % anchor[:62])


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1490 |")
disc_line = full_line(raw, "762. ")

NEW_FACTS = [
    (
        1491,
        "MEASURED",
        "M109",
        "**The magenta defect is real on the default `strehl stack` path.** Same subject "
        "`D:\\personal\\macro\\dry-erase-marker-head-cpl`, same flags "
        "(`--srgb --auto-exposure --gate 4`): `stack` **2.0017 % -> 0.5060 %** of frame, "
        "argmax-baseline **0.3378 % -> 0.0944 %**. Green offset in the magenta region "
        "measures **-0.1028** on the stack render. `e9ad010` is **not inert** there -- "
        "identical argv, one toggle, two different renders: `DB7BAAD2..A1DDDC` vs "
        "`559407FE..AD12E5`.",
    ),
    (
        1492,
        "MEASURED",
        "M109",
        "**The highlight clip cannot overshoot into green, structurally rather than "
        "luckily.** B14 (the registered B1 predicate with channels swapped): green excess "
        "**0.0113 % before and after**, pixels turned green-excess by the clip **0**, mean "
        "green offset -0.1028 -> **-0.0260**, **max green offset after exactly +0.0000**. "
        "Mechanism: `K = min_c ceil_c`, and green's ceiling **is** the minimum because its "
        "white-balance gain is 1.0 by construction; the clip only lowers channels to `K`, "
        "and green already sits at or below `K`, so it lands on neutral and cannot cross "
        "it. B14 was **not** pre-registered, though its predicate is the exact mirror of "
        "one that was.",
    ),
    (
        1493,
        "MEASURED",
        "M109",
        "**A byte-freeze HOLD cannot certify a `--srgb` change, because the freeze never "
        "renders `--srgb`.** The frozen artefact is the *measurement* path -- default, "
        "binned, linear, camera-native -- and the highlight clip is viewing-path only by "
        "ORCH's own requirement that the frozen output not move by a byte. M97's 5/5 HOLD "
        "therefore proves the fix **stayed out of the measurement path**, which is the "
        "designed result, and says nothing whatever about whether it changes a viewed "
        "render.",
    ),
    (
        1494,
        "MEASURED",
        "M109",
        "**M110's four-subject null and M109's 2.0017 % never conflicted: they differ by "
        "subject, not by instrument.** M109 first hypothesised M110's `R,B >= 99 % full "
        "scale` selector was structurally blind here, reasoning from raw DN (R 46.8 % FS, "
        "B 86.2 % FS) -- then measured that it covers **99.04 %** of the magenta "
        "population and **refuted its own hypothesis**. The error was comparing a **raw**"
        "-domain criterion against an **output**-domain population: raw R at 46.8 % FS "
        "becomes output R **0.9944** after x2.687 white balance, exposure, matrix and the "
        "sRGB curve.",
    ),
    (
        1495,
        "MEASURED",
        "M109",
        "The highlight fix remains **PARTIAL**: **0.5060 %** of frame still reads magenta "
        "after the clip on `dry-erase-marker-head-cpl`, **visibly pink at 1:1**, against "
        "LibRaw's **0.0061 %** on the same capture -- roughly **83x** worse than the "
        "reference implementation. The clip removes about three quarters of the defect and "
        "is not a solution to it.",
    ),
]

NEW_DISCS = [
    (
        763,
        "**When several instruments agree there is no effect, verify each one is *able* to "
        "see the effect's domain before treating the agreement as corroboration.** "
        "Concurring nulls feel like independent confirmation and are the most persuasive "
        "evidence available; two blind instruments agreeing is not evidence at all, it is "
        "manufactured confidence, and it is more dangerous than a single wrong number "
        "because it comes with a corroboration story attached. ORCH declared a shipped fix "
        "inert on three signals: a byte-freeze that renders a different pipeline by design "
        "(fact 1493), four subjects none of which exhibited the defect (fact 1494), and a "
        "mechanism invented afterwards to explain both (fact 1487, refuted). For each null, "
        "state the domain it samples and show the effect would have been in range.",
    ),
    (
        764,
        "**A test built to be insensitive to a change cannot later be cited as evidence the "
        "change did nothing.** The byte-freeze was specified to hold across this fix; when "
        "it held, that was the specification being met, not a measurement. Whenever a "
        "guarantee and an observation are the same artefact, the observation has no "
        "evidential content -- record which one you are invoking (fact 1493).",
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
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "fold text contains 0x%02X" % o

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("\nfolded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("amended in place: facts 1483, 1484, 1485, 1487; discipline 759")

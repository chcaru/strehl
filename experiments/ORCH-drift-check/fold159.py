"""ORCH fold 159: M124-resampler-flag.

A build, not a measurement. Notable for three things: it proved byte-inertness
against a COMMITTED freeze fixture rather than its own before/after; it found
that the flag is structurally unfreezable and said so instead of faking a row;
and it reported a cost reading OUTSIDE the prior milestone's range as a bound
it could not isolate rather than smoothing it over.
"""
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1726 | MEASURED | M124 | **`--resampler` IS NOW EXPOSED ON `stack` AND THE DEFAULT DID NOT MOVE, PROVEN AGAINST A COMMITTED FIXTURE RATHER THAN THE AGENT'S OWN BEFORE/AFTER.** Five kernels reachable (`nearest`, `bilinear`, `catmull-rom`, `lanczos2`, `lanczos3`), default `catmull-rom`. On `coffee-bean --limit 20 --gate 2.0`, no `--srgb`, solving path, empty per-arm cache: the default renders `119936E6...D709` **before the change (x3 runs), after the change, and under an explicit `--resampler catmull-rom`** -- and that hash **is the already-recorded `coffee-bean-20-gate2-sidecar` freeze fixture, which still HOLDS at HEAD**. So byte-inertness is anchored to a fixture committed before the work began, not to a self-comparison. All five kernels produce **distinct** hashes; the whole matrix was re-run after the final rebuild and reproduced exactly. Tests: **70 + 5 (byte-freeze, `STREHL_FREEZE_REQUIRE=1`) + 352 = 427 passed, 0 failed**. Commits `711ac32`, `169840c`. |
| 1727 | MEASURED | M124 | **`lanczos2` WAS UNREACHABLE BECAUSE THE NAME -> VARIANT MAPPING EXISTED TWICE.** One `pub(crate)` mapping in `warpmap.rs` and a second private `match` inside `AlignArgs`; the two had drifted, and a kernel present in the enum could not be named on the command line. The fix was to widen the existing mapping to `pub`, add `RESAMPLER_NAMES`, and delete the duplicate -- **one mapping, not two, and not three**. M124 explicitly crossed the crate boundary (`strehl-core`) to achieve that, against the letter of its brief, and said so: copying the mapping CLI-side would have ended with three. A test now asserts every listed name maps to a **distinct** variant, which is the check whose absence allowed the drift. |
| 1728 | MEASURED | M124 | **THE FLAG IS STRUCTURALLY UNFREEZABLE, AND M124 SAID SO RATHER THAN ADDING A ROW THAT WOULD LOOK LIKE COVERAGE.** `byte-freezes.tsv` builds its command from the row and verifies the header verbatim; there is no `resampler` column, the registry is append-only so adding one means editing the header, and **the parser rejects solving rows**. The only two admissible modes are align-off and sidecar-override -- **which are exactly the two modes in which `--resampler` cannot change a single byte**. A freeze row for this flag would therefore be a row that can never fail. This is the correct disposition of an untestable check and the opposite of the pattern in fact 1725. |
| 1729 | ARGUED | M124 | **THE KERNEL COSTS ARE BOUNDS, NOT VALUES, AND ONE OF THEM FELL OUTSIDE THE PRIOR MILESTONE'S RANGE UNRECONCILED.** Two runs on a **shared** machine: lanczos3 **3.4-3.5x**, lanczos2 **2.3-2.4x**, nearest **0.67-0.68x**, bilinear **0.69-0.82x**. That bilinear upper end is **outside M118 Y10's 0.56-0.69x**. M124 attributed it to host load and **explicitly did not isolate it**, reporting the disagreement rather than the convenient half of it. Under the fleet-concurrency discipline this is the right call and the number is unusable as a value: **a timing measured on a machine running eighteen other agents is a bound**. Whoever needs the real cost must pin the tree and idle the host. |
| 1730 | MEASURED | M124 | **KERNELS CANNOT SHARE A CACHE ENTRY, AND A BAD NAME FAILS BEFORE ANY DECODE.** The default's sidecar cache key is unchanged across the work (`coffee-bean-55f8b4c1af1e8037`, content `EF74541395DB1BA6...`) and `lanczos3` resolves to a **different** key -- so a kernel switch cannot silently serve another kernel's cached warp, which is the failure mode a name-keyed cache invites. `strehl stack --resampler bogus` exits 1 with `unknown resampler "bogus"; valid choices are ...` **before any decode**, and `strehl align` emits byte-identical text from the same unified parser (fact 1727). |
"""

NEW_DISCIPLINES = """881. **PROVE BYTE-INERTNESS AGAINST A FIXTURE COMMITTED BEFORE THE WORK, NOT AGAINST YOUR OWN BEFORE/AFTER.** M124's default hash `119936E6...D709` was already in `byte-freezes.tsv` as `coffee-bean-20-gate2-sidecar` (fact 1726). A self-comparison proves only that the agent did not change its mind mid-run; matching a **pre-existing committed hash** proves the output is where the corpus says it should be. When a fixture for your surface already exists, quoting it costs nothing and upgrades the claim's class.
882. **A CHECK THAT CANNOT FAIL IS WORSE THAN A MISSING CHECK, BECAUSE IT REPORTS AS COVERAGE.** Fact 1728 is the model disposition: M124 worked out that every admissible freeze mode was one in which its flag provably could not act, and **declined to add the row**, stating the structural reason. Compare fact 1725, where a script that printed a real disagreement was never folded and created a false record of having checked. **Both failures are about the gap between performing a check and the check meaning something** -- one adds ceremony, the other discards substance.
883. **WHEN THE SAME MAPPING EXISTS TWICE, THE BUG IS NOT IN EITHER COPY.** `lanczos2` was unreachable because a name table lived in two places and drifted (fact 1727). The repair that ends with **one** mapping is worth crossing a crate boundary for; the repair that ends with two or three is not a repair. Add the test that the duplication defeated -- here, that every listed name resolves to a **distinct** variant.
884. **A TIMING TAKEN ON A SHARED HOST IS A BOUND; LABEL IT AS ONE AND REPORT THE READING THAT DOES NOT FIT.** M124's bilinear cost ran outside the prior milestone's range and it published the disagreement unresolved (fact 1729). The temptation is to quote the half that agrees. **An unreconciled out-of-range reading is information; a silently dropped one is a defect that will be rediscovered later at higher cost.**
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    eol = txt.index("\n", i)
    return txt[: eol + 1] + block + txt[eol + 1 :]


text = insert_after_fact_row(1725, NEW_FACTS, text)

m = re.search(r"^880\. .*?(?=\n\d+\. |\n## )", text, re.S | re.M)
assert m, "discipline 880 not found"
text = text[: m.end()] + "\n" + NEW_DISCIPLINES.rstrip() + text[m.end() :]

# ---------------------------------------------------------------- assertions

assert text != orig, "no change"
for n in (1726, 1727, 1728, 1730):
    assert text.count(f"| {n} | MEASURED | M124 |") == 1, f"fact {n}"
assert text.count("| 1729 | ARGUED | M124 |") == 1, "fact 1729 must be ARGUED"
for n in (881, 882, 883, 884):
    assert re.search(rf"^{n}\. \*\*", text, re.M), f"discipline {n}"

for line in NEW_FACTS.strip().split("\n"):
    assert line.count("|") == 5, f"pipe count {line.count('|')}: {line[:80]}"
    stripped = re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, f"bold imbalance: {line[:80]}"

# The cost fact must not read as a value.
i1729 = text.index("| 1729 |")
row1729 = text[i1729 : text.index("\n", i1729)]
assert "BOUNDS, NOT VALUES" in row1729, "1729 must state bounds"
assert "did not isolate" in row1729, "1729 must record the unreconciled reading"

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold159 OK: facts 1726-1730, disciplines 881-884")
